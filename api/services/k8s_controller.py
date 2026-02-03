"""
Kubernetes controller for direct K8s API operations.

Replaces subprocess calls to trader-ctl.sh with native Kubernetes Python client.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from jinja2 import Environment, FileSystemLoader
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from api.config import get_settings
from api.models import Trader

logger = logging.getLogger(__name__)


class KubernetesControllerError(Exception):
    """Base exception for K8s controller errors."""

    pass


class KubernetesTraderController:
    """Direct Kubernetes API controller for trader management."""

    @classmethod
    def is_available(cls) -> bool:
        """
        Check if Kubernetes integration is enabled.

        Returns:
            bool: True if K8s is enabled, False otherwise
        """
        settings = get_settings()
        return settings.k8s_enabled

    def __init__(self):
        """
        Initialize Kubernetes client and Jinja2 templates.

        Tries in-cluster config first (for running in K8s),
        falls back to kubeconfig (for local development).

        Raises:
            RuntimeError: If Kubernetes is disabled
        """
        settings = get_settings()
        
        if not settings.k8s_enabled:
            raise RuntimeError(
                "Kubernetes is disabled. Set K8S_ENABLED=true to use K8s features."
            )
        
        # Load K8s config (in-cluster first, then kubeconfig)
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster K8s config")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Loaded kubeconfig")

        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()

        self.namespace = settings.k8s_namespace
        self.github_repo = settings.github_repo

        # Load Jinja2 templates
        templates_path = Path(settings.templates_dir)
        self.jinja_env = Environment(
            loader=FileSystemLoader(templates_path),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def deploy_trader(self, trader: Trader, private_key: str) -> Dict[str, Any]:
        """
        Deploy trader to Kubernetes using replace strategy.

        Args:
            trader: Trader model with configuration
            private_key: Raw (unencrypted) private key for K8s Secret

        Returns:
            Dict with deployment status and k8s_name

        Raises:
            KubernetesControllerError: If deployment fails
        """
        try:
            # 1. Remove existing resources (ignore 404)
            self._delete_resources_if_exist(trader)

            # 2. Create Secret
            self._create_secret(trader, private_key)

            # 3. Create ConfigMap
            self._create_configmap(trader)

            # 4. Create StatefulSet
            self._create_statefulset(trader)

            logger.info(f"Successfully deployed trader {trader.k8s_name}")
            return {"status": "deployed", "k8s_name": trader.k8s_name}

        except ApiException as e:
            logger.error(f"K8s API error deploying trader: {e}")
            raise KubernetesControllerError(f"Deployment failed: {e.reason}")

    def remove_trader(self, trader: Trader) -> None:
        """
        Remove all Kubernetes resources for a trader.

        Args:
            trader: Trader model

        Raises:
            KubernetesControllerError: If deletion fails (except 404)
        """
        try:
            self._delete_resources_if_exist(trader)
            logger.info(f"Successfully removed trader {trader.k8s_name}")
        except ApiException as e:
            if e.status != 404:
                raise KubernetesControllerError(f"Removal failed: {e.reason}")

    def update_trader_config(self, trader: Trader) -> None:
        """
        Update ConfigMap and restart pod to pick up new configuration.

        Args:
            trader: Trader model with updated configuration

        Raises:
            KubernetesControllerError: If update fails
        """
        try:
            # Delete and recreate ConfigMap
            self._delete_configmap(trader)
            self._create_configmap(trader)

            # Restart by deleting pod (StatefulSet will recreate it)
            self.restart_trader(trader)

            logger.info(f"Successfully updated config for trader {trader.k8s_name}")

        except ApiException as e:
            raise KubernetesControllerError(f"Config update failed: {e.reason}")

    def restart_trader(self, trader: Trader) -> None:
        """
        Restart trader by deleting pod (StatefulSet recreates it).

        Args:
            trader: Trader model

        Raises:
            KubernetesControllerError: If restart fails
        """
        try:
            pods = self.core_api.list_namespaced_pod(
                namespace=self.namespace, label_selector=f"trader-address={trader.wallet_address}"
            )
            for pod in pods.items:
                self.core_api.delete_namespaced_pod(
                    name=pod.metadata.name,
                    namespace=self.namespace,
                )
                logger.info(f"Deleted pod {pod.metadata.name} for restart")
        except ApiException as e:
            if e.status != 404:
                raise KubernetesControllerError(f"Restart failed: {e.reason}")

    def get_trader_status(self, trader: Trader) -> Dict[str, Any]:
        """
        Get real-time Kubernetes status for a trader.

        Args:
            trader: Trader model

        Returns:
            Dict with K8s status information:
            - exists: Whether StatefulSet exists
            - pod_phase: Pod phase (Pending, Running, Failed, etc.)
            - ready: Whether pod is ready
            - restarts: Number of container restarts
            - pod_ip: Pod IP address
            - node: Node name
            - started_at: Pod start time

        Raises:
            KubernetesControllerError: If status check fails (except 404)
        """
        result = {
            "exists": False,
            "pod_phase": None,
            "ready": False,
            "restarts": 0,
            "ready_replicas": 0,
            "pod_ip": None,
            "node": None,
            "started_at": None,
        }

        try:
            # Check StatefulSet exists
            sts = self.apps_api.read_namespaced_stateful_set(
                name=trader.k8s_name,
                namespace=self.namespace,
            )
            result["exists"] = True
            result["ready_replicas"] = sts.status.ready_replicas or 0

            # Get pod details
            pods = self.core_api.list_namespaced_pod(
                namespace=self.namespace, label_selector=f"trader-address={trader.wallet_address}"
            )

            if pods.items:
                pod = pods.items[0]
                result["pod_phase"] = pod.status.phase
                result["pod_ip"] = pod.status.pod_ip
                result["node"] = pod.spec.node_name
                result["started_at"] = (
                    pod.status.start_time.isoformat() if pod.status.start_time else None
                )

                if pod.status.container_statuses:
                    cs = pod.status.container_statuses[0]
                    result["ready"] = cs.ready
                    result["restarts"] = cs.restart_count

        except ApiException as e:
            if e.status == 404:
                result["exists"] = False
            else:
                raise KubernetesControllerError(f"Status check failed: {e.reason}")

        return result

    def get_trader_logs(self, trader: Trader, tail_lines: int = 100) -> Optional[str]:
        """
        Get pod logs for a trader.

        Args:
            trader: Trader model
            tail_lines: Number of log lines to return (default 100)

        Returns:
            Log output as string, or None if no pod found

        Raises:
            KubernetesControllerError: If log retrieval fails (except 404)
        """
        try:
            pods = self.core_api.list_namespaced_pod(
                namespace=self.namespace, label_selector=f"trader-address={trader.wallet_address}"
            )

            if not pods.items:
                return None

            pod_name = pods.items[0].metadata.name

            return self.core_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=self.namespace,
                tail_lines=tail_lines,
            )

        except ApiException as e:
            if e.status == 404:
                return None
            raise KubernetesControllerError(f"Log retrieval failed: {e.reason}")

    # Private methods

    def _delete_resources_if_exist(self, trader: Trader) -> None:
        """
        Delete all K8s resources for trader, ignoring 404 errors.

        Deletes in order: StatefulSet (with foreground propagation),
        ConfigMap, Secret.
        """
        # Delete StatefulSet first (with foreground propagation to wait for pods)
        try:
            self.apps_api.delete_namespaced_stateful_set(
                name=trader.k8s_name,
                namespace=self.namespace,
                body=client.V1DeleteOptions(propagation_policy="Foreground"),
            )
            logger.info(f"Deleted StatefulSet {trader.k8s_name}")
        except ApiException as e:
            if e.status != 404:
                raise

        # Delete ConfigMap
        self._delete_configmap(trader)

        # Delete Secret
        try:
            self.core_api.delete_namespaced_secret(
                name=f"{trader.k8s_name}-secret",
                namespace=self.namespace,
            )
            logger.info(f"Deleted Secret {trader.k8s_name}-secret")
        except ApiException as e:
            if e.status != 404:
                raise

    def _delete_configmap(self, trader: Trader) -> None:
        """Delete ConfigMap for trader, ignoring 404."""
        try:
            self.core_api.delete_namespaced_config_map(
                name=f"{trader.k8s_name}-config",
                namespace=self.namespace,
            )
            logger.info(f"Deleted ConfigMap {trader.k8s_name}-config")
        except ApiException as e:
            if e.status != 404:
                raise

    def _create_secret(self, trader: Trader, private_key: str) -> None:
        """
        Create Kubernetes Secret for trader.

        Args:
            trader: Trader model
            private_key: Raw private key to store
        """
        template = self.jinja_env.get_template("secret.yaml.j2")
        manifest = template.render(
            trader_name=trader.k8s_name,
            namespace=self.namespace,
            wallet_address=trader.wallet_address,
            private_key=private_key,
        )

        secret_dict = yaml.safe_load(manifest)
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=secret_dict["metadata"]["name"],
                namespace=secret_dict["metadata"]["namespace"],
                labels=secret_dict["metadata"]["labels"],
            ),
            string_data=secret_dict["stringData"],
        )

        self.core_api.create_namespaced_secret(
            namespace=self.namespace,
            body=secret,
        )
        logger.info(f"Created Secret {trader.k8s_name}-secret")

    def _create_configmap(self, trader: Trader) -> None:
        """
        Create Kubernetes ConfigMap for trader.

        Args:
            trader: Trader model with configuration

        Raises:
            KubernetesControllerError: If trader has no configuration
        """
        # Get latest config from trader
        latest_config = trader.latest_config
        if not latest_config:
            raise KubernetesControllerError("Trader has no configuration")

        config_json = json.dumps(latest_config.config_json, indent=2)

        template = self.jinja_env.get_template("configmap.yaml.j2")
        manifest = template.render(
            trader_name=trader.k8s_name,
            namespace=self.namespace,
            wallet_address=trader.wallet_address,
            config_json=config_json,
        )

        cm_dict = yaml.safe_load(manifest)
        configmap = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=cm_dict["metadata"]["name"],
                namespace=cm_dict["metadata"]["namespace"],
                labels=cm_dict["metadata"]["labels"],
            ),
            data=cm_dict["data"],
        )

        self.core_api.create_namespaced_config_map(
            namespace=self.namespace,
            body=configmap,
        )
        logger.info(f"Created ConfigMap {trader.k8s_name}-config")

    def _create_statefulset(self, trader: Trader) -> None:
        """
        Create Kubernetes StatefulSet for trader.

        Args:
            trader: Trader model with image_tag
        """
        template = self.jinja_env.get_template("statefulset.yaml.j2")
        manifest = template.render(
            trader_name=trader.k8s_name,
            namespace=self.namespace,
            wallet_address=trader.wallet_address,
            github_repo=self.github_repo,
            image_tag=trader.image_tag,
        )

        sts_dict = yaml.safe_load(manifest)

        # Use ApiClient to deserialize properly
        statefulset = client.ApiClient().deserialize(
            type("Response", (), {"data": json.dumps(sts_dict)})(), "V1StatefulSet"
        )

        self.apps_api.create_namespaced_stateful_set(
            namespace=self.namespace,
            body=statefulset,
        )
        logger.info(f"Created StatefulSet {trader.k8s_name}")
