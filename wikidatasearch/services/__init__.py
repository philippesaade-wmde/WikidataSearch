# ruff: noqa: D100,D101,D102,D103,D104,D200,D205,D417
from .search import HybridSearch

__all__ = ["HybridSearch", "Logger", "Feedback", "build_analytics_app"]


def __getattr__(name: str):
    if name in {"Logger", "Feedback"}:
        from .logger import Feedback, Logger

        return {"Logger": Logger, "Feedback": Feedback}[name]
    if name == "build_analytics_app":
        from .analytics import build_analytics_app

        return build_analytics_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
