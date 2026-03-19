import asyncio
import importlib
import sys
import types
from pathlib import Path
from urllib.parse import urlencode

import pytest
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class DummyLogger:
    calls = []

    @staticmethod
    def add_request(*args, **kwargs):
        DummyLogger.calls.append({"args": args, "kwargs": kwargs})


class DummyFeedback:
    calls = []

    @staticmethod
    def add_feedback(*args, **kwargs):
        DummyFeedback.calls.append({"args": args, "kwargs": kwargs})


class DummySearch:
    def __init__(self):
        self.calls = []
        self.vectordb_langs = ["en", "fr"]
        self.translator = types.SimpleNamespace(mint_langs=["en", "fr", "de", "ar"])

    def search(self, query, **kwargs):
        self.calls.append({"name": "search", "query": query, "kwargs": kwargs})
        filt = kwargs.get("filter") or {}
        if filt.get("metadata.IsProperty"):
            return [
                {
                    "PID": "P31",
                    "similarity_score": 0.91,
                    "rrf_score": 0.04,
                    "source": "Vector Search",
                }
            ]
        return [
            {
                "QID": "Q42",
                "similarity_score": 0.95,
                "rrf_score": 0.05,
                "source": "Vector Search",
            }
        ]

    def get_similarity_scores(self, query, qids, **kwargs):
        self.calls.append(
            {
                "name": "get_similarity_scores",
                "query": query,
                "qids": list(qids),
                "kwargs": kwargs,
            }
        )
        out = []
        for idx, qid in enumerate(qids):
            score = max(0.0, 1.0 - idx * 0.1)
            if qid.startswith("Q"):
                out.append({"QID": qid, "similarity_score": score})
            elif qid.startswith("P"):
                out.append({"PID": qid, "similarity_score": score})
        return out


class DummyLimiter:
    def limit(self, *_args, **_kwargs):
        def _deco(fn):
            return fn

        return _deco


def _identity_cache(*_args, **_kwargs):
    def _deco(fn):
        return fn

    return _deco


@pytest.fixture(scope="session")
def test_ctx():
    # Ensure a clean import path for this isolated unit-test setup.
    for mod in list(sys.modules):
        if mod.startswith("wikidatasearch"):
            sys.modules.pop(mod, None)

    dummy_search = DummySearch()

    fake_config = types.ModuleType("wikidatasearch.config")
    fake_settings = types.SimpleNamespace(
        CACHE_TTL=60,
        RATE_LIMIT="1000/minute",
        MAX_VECTORDB_K=50,
        FRONTEND_STATIC_DIR="frontend/dist",
        ANALYTICS_API_SECRET="",
    )
    fake_config.settings = fake_settings
    fake_config.SEARCH = dummy_search
    sys.modules["wikidatasearch.config"] = fake_config

    fake_logger = types.ModuleType("wikidatasearch.services.logger")
    fake_logger.Logger = DummyLogger
    fake_logger.Feedback = DummyFeedback
    sys.modules["wikidatasearch.services.logger"] = fake_logger

    fake_analytics = types.ModuleType("wikidatasearch.services.analytics")
    fake_analytics.build_analytics_app = lambda: None
    sys.modules["wikidatasearch.services.analytics"] = fake_analytics

    fake_dependencies = types.ModuleType("wikidatasearch.dependencies")
    fake_dependencies.limiter = DummyLimiter()
    fake_dependencies.register_rate_limit = lambda _app: None
    fake_dependencies.require_descriptive_user_agent = lambda _request: None
    sys.modules["wikidatasearch.dependencies"] = fake_dependencies

    fake_cache_module = types.ModuleType("fastapi_cache.decorator")
    fake_cache_module.cache = _identity_cache
    sys.modules["fastapi_cache.decorator"] = fake_cache_module

    # Avoid importing the real app module via wikidatasearch/__init__.py side effects.
    fake_main = types.ModuleType("wikidatasearch.main")
    fake_main.app = object()
    sys.modules["wikidatasearch.main"] = fake_main

    ctx = {
        "search": dummy_search,
        "logger": DummyLogger,
        "feedback": DummyFeedback,
        "item": importlib.import_module("wikidatasearch.routes.item"),
        "property": importlib.import_module("wikidatasearch.routes.property"),
        "similarity": importlib.import_module("wikidatasearch.routes.similarity"),
        "frontend": importlib.import_module("wikidatasearch.routes.frontend"),
    }
    return ctx


@pytest.fixture
def run_async():
    def _run(coro):
        return asyncio.run(coro)

    return _run


@pytest.fixture
def make_request():
    def _make(path: str, method: str = "GET", params: dict | None = None) -> Request:
        query_string = urlencode(params or {}, doseq=True).encode()
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "path": path,
            "query_string": query_string,
            "headers": [
                (b"user-agent", b"Unit Test Client/1.0 (unit-tests@example.org)"),
            ],
            "client": ("127.0.0.1", 12345),
            "scheme": "http",
            "server": ("testserver", 80),
        }
        return Request(scope)

    return _make
