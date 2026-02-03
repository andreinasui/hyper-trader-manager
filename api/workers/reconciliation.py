"""
Background reconciliation worker.

Periodically syncs Kubernetes state to PostgreSQL database.
Ensures trader.status reflects actual K8s pod state.
"""

import asyncio
import logging
from typing import Optional

from api.config import get_settings
from api.database import SessionLocal
from api.models import Trader
from api.services.k8s_controller import (
    KubernetesControllerError,
    KubernetesTraderController,
)

logger = logging.getLogger(__name__)

# Global task reference for cancellation
_reconciliation_task: Optional[asyncio.Task] = None


def _determine_status(k8s_status: dict) -> str:
    """
    Map Kubernetes state to trader status string.

    Args:
        k8s_status: Dict from KubernetesTraderController.get_trader_status()

    Returns:
        Status string: running, pending, starting, failed, or missing
    """
    if not k8s_status.get("exists"):
        return "missing"

    pod_phase = k8s_status.get("pod_phase")
    ready = k8s_status.get("ready", False)
    ready_replicas = k8s_status.get("ready_replicas", 0)

    if pod_phase == "Failed":
        return "failed"
    elif ready and ready_replicas > 0:
        return "running"
    elif pod_phase in ("Pending", "ContainerCreating"):
        return "pending"
    elif pod_phase == "Running" and not ready:
        return "starting"
    else:
        return "pending"


async def reconciliation_loop(interval_seconds: Optional[int] = None):
    """
    Background task to sync Kubernetes state to PostgreSQL.

    Runs continuously, checking all traders every interval_seconds.
    Updates trader.status based on actual K8s pod state.

    Args:
        interval_seconds: Override default reconciliation interval
    """
    settings = get_settings()
    
    # Exit early if Kubernetes is disabled
    if not settings.k8s_enabled:
        logger.info("Kubernetes disabled - reconciliation worker exiting")
        return
    
    interval = interval_seconds or settings.reconciliation_interval

    logger.info(f"Starting reconciliation loop (interval: {interval}s)")

    while True:
        try:
            db = SessionLocal()
            k8s = KubernetesTraderController()

            try:
                traders = db.query(Trader).all()
                updated_count = 0

                for trader in traders:
                    try:
                        k8s_status = k8s.get_trader_status(trader)
                        new_status = _determine_status(k8s_status)

                        if trader.status != new_status:
                            old_status = trader.status
                            trader.status = new_status
                            updated_count += 1
                            logger.info(
                                f"Trader {trader.k8s_name} status: {old_status} -> {new_status}"
                            )

                    except KubernetesControllerError as e:
                        logger.warning(f"Failed to get status for {trader.k8s_name}: {e}")

                if updated_count > 0:
                    db.commit()
                    logger.debug(f"Reconciliation updated {updated_count} traders")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Reconciliation loop error: {e}", exc_info=True)

        await asyncio.sleep(interval)


def start_reconciliation() -> asyncio.Task:
    """
    Start the reconciliation background task.

    Returns:
        asyncio.Task: The running reconciliation task
    """
    global _reconciliation_task
    _reconciliation_task = asyncio.create_task(reconciliation_loop())
    logger.info("Reconciliation worker started")
    return _reconciliation_task


def stop_reconciliation():
    """Stop the reconciliation background task."""
    global _reconciliation_task
    if _reconciliation_task:
        _reconciliation_task.cancel()
        _reconciliation_task = None
        logger.info("Reconciliation loop stopped")
