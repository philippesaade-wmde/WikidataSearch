# ruff: noqa: D100,D101,D102,D103,D104,D200,D205,D417
__all__ = ["app"]


def __getattr__(name: str):
    if name == "app":
        from .main import app

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
