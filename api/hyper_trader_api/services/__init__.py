"""
Service layer for HyperTrader API.

This package exports all business logic services.
"""

# Try to import kubernetes-dependent services, but don't fail if not available
__all__ = []

try:
    from hyper_trader_api.services.k8s_controller import (  # noqa: F401
        KubernetesControllerError,
        KubernetesTraderController,
    )

    __all__.extend(["KubernetesControllerError", "KubernetesTraderController"])
except ImportError:
    pass

try:
    from hyper_trader_api.services.privy_service import (  # noqa: F401
        PrivyError,
        PrivyService,
        get_privy_service,
    )

    __all__.extend(["PrivyService", "PrivyError", "get_privy_service"])
except ImportError:
    pass

try:
    from hyper_trader_api.services.trader_service import (  # noqa: F401
        TraderNotFoundError,
        TraderOwnershipError,
        TraderService,
        TraderServiceError,
    )

    __all__.extend(
        [
            "TraderService",
            "TraderServiceError",
            "TraderNotFoundError",
            "TraderOwnershipError",
        ]
    )
except ImportError:
    pass
