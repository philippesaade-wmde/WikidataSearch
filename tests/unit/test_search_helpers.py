"""Unit tests for search helpers, including reciprocal rank fusion, deduplication, query cleaning, search routing, and embedding lookup by ID."""

import importlib
import sys
import types


def _ensure_service_import_stubs():
    """Install lightweight stubs into system modules for unit tests without real extneral dependencies"""
    if "requests" not in sys.modules:
        fake_requests = types.ModuleType("requests")
        fake_requests.get = lambda *args, **kwargs: None
        fake_requests.post = lambda *args, **kwargs: None
        sys.modules["requests"] = fake_requests

    if "stopwordsiso" not in sys.modules:
        fake_stopwordsiso = types.ModuleType("stopwordsiso")
        fake_stopwordsiso.stopwords = lambda _lang: {"the", "a", "an"}
        sys.modules["stopwordsiso"] = fake_stopwordsiso

    if "astrapy" not in sys.modules:
        fake_astrapy = types.ModuleType("astrapy")
        fake_astrapy.DataAPIClient = object
        sys.modules["astrapy"] = fake_astrapy

    if "astrapy.api_options" not in sys.modules:
        fake_api_options = types.ModuleType("astrapy.api_options")
        fake_api_options.APIOptions = object
        fake_api_options.TimeoutOptions = object
        sys.modules["astrapy.api_options"] = fake_api_options

    if "wikidatasearch.services.jina" not in sys.modules:
        fake_jina = types.ModuleType("wikidatasearch.services.jina")

        class _DummyJina:
            """Minimal Jina client stub"""
            def __init__(self, *_args, **_kwargs):
                """Accept arbitrary constructor args in tests."""
                pass

        fake_jina.JinaAIAPI = _DummyJina
        sys.modules["wikidatasearch.services.jina"] = fake_jina


def _service_classes():
    """Import and return search service classes with the dependency stubs."""
    _ensure_service_import_stubs()

    hybrid_module = importlib.import_module("wikidatasearch.services.search.HybridSearch")
    keyword_module = importlib.import_module("wikidatasearch.services.search.KeywordSearch")
    vector_module = importlib.import_module("wikidatasearch.services.search.VectorSearch")

    return hybrid_module.HybridSearch, keyword_module.KeywordSearch, vector_module.VectorSearch

def test_reciprocal_rank_fusion_merges_sources_and_accumulates_rrf(test_ctx):
    """Validate reciprocal rank fusion sources and accumulates rrf score."""
    HybridSearch, _, _ = _service_classes()
    vector_results = [
        {"QID": "Q42", "similarity_score": 0.95},
        {"QID": "Q5", "similarity_score": 0.90},
    ]
    keyword_results = [
        {"QID": "Q5", "similarity_score": 0.80},
        {"QID": "Q42", "similarity_score": 0.70},
    ]

    fused = HybridSearch.reciprocal_rank_fusion(
        [
            ("Vector Search", vector_results),
            ("Keyword Search", keyword_results),
        ]
    )

    by_id = {row["QID"]: row for row in fused}
    assert set(by_id.keys()) == {"Q42", "Q5"}
    assert by_id["Q42"]["source"] == "Vector Search, Keyword Search"
    assert by_id["Q5"]["source"] == "Vector Search, Keyword Search"
    assert by_id["Q42"]["similarity_score"] == 0.95
    assert by_id["Q5"]["similarity_score"] == 0.90
    assert by_id["Q42"]["rrf_score"] > 0
    assert by_id["Q5"]["rrf_score"] > 0


def test_vector_remove_duplicates_prefers_best_similarity_and_keeps_unique_results(test_ctx):
    """Validate removing duplicates that keeps unique results with the highest similarity scores"""
    _, _, VectorSearch = _service_classes()
    raw_results = [
        {"metadata": {"QID": "Q42"}, "$similarity": 0.60, "$vector": [0.1], "content": "A"},
        {"metadata": {"QID": "Q42"}, "$similarity": 0.95, "$vector": [0.9], "content": "B"},
        {"metadata": {"PID": "P31"}, "$similarity": 0.70, "$vector": [0.2], "content": "C"},
    ]

    deduped = VectorSearch.remove_duplicates(
        raw_results,
        return_vectors=True,
        return_text=True,
    )

    assert len(deduped) == 2
    assert deduped[0]["QID"] == "Q42"
    assert deduped[0]["similarity_score"] == 0.95
    assert deduped[0]["vector"] == [0.9]
    assert deduped[0]["text"] == "B"
    assert deduped[1]["PID"] == "P31"
    assert deduped[1]["similarity_score"] == 0.70


def test_reciprocal_rank_fusion_drops_non_positive_similarity(test_ctx):
    """Validate reciprocal rank fusion that drops negative similarity scores."""
    HybridSearch, _, _ = _service_classes()
    fused = HybridSearch.reciprocal_rank_fusion(
        [
            (
                "Vector Search",
                [
                    {"QID": "Q3", "similarity_score": 0.25},
                    {"QID": "Q1", "similarity_score": 0.0},
                    {"QID": "Q2", "similarity_score": -0.1},
                ],
            )
        ]
    )

    assert [row["QID"] for row in fused] == ["Q3"]


def test_keyword_clean_query_removes_stopwords_and_caps_length(test_ctx):
    """Validate KeywordSearch's clean query that removes stopwords and caps length."""
    _, KeywordSearch, _ = _service_classes()
    keyword = KeywordSearch()

    cleaned = keyword._clean_query("the quick brown fox", "all")
    assert "the" not in cleaned.lower()
    assert "quick" in cleaned.lower()
    assert len(cleaned) <= 300

    very_long = "word " * 500
    cleaned_long = keyword._clean_query(very_long, "en")
    assert len(cleaned_long) <= 300


def test_vector_find_routes_pid_filters_to_property_collection(test_ctx):
    """Validate PID filters route to the property vector database."""
    _, _, VectorSearch = _service_classes()

    class _FakeCollection:
        """Minimal collection stub that records find calls."""

        def __init__(self, name):
            """Store the collection name and initialize captured calls."""
            self.name = name
            self.calls = []

        def find(self, *args, **kwargs):
            """Capture call arguments and return one deterministic row."""
            self.calls.append({"args": args, "kwargs": kwargs})
            if self.name == "property":
                return [{"metadata": {"PID": "P31"}, "$similarity": 0.9}]
            return [{"metadata": {"QID": "Q42"}, "$similarity": 0.9}]

    vector = VectorSearch.__new__(VectorSearch)
    vector.icollection = _FakeCollection("item")
    vector.pcollection = _FakeCollection("property")
    vector.max_K = 50

    rows = vector.find(
        {"metadata.PID": {"$in": ["P31"]}},
        projection={"metadata": 1},
        limit=None,
    )

    assert rows and rows[0]["metadata"]["PID"] == "P31"
    assert len(vector.pcollection.calls) == 1
    assert len(vector.icollection.calls) == 0


def test_get_embedding_by_id_marks_property_ids_as_property_filter(test_ctx):
    """Validate that property lookups build the correct filter before querying."""
    _, _, VectorSearch = _service_classes()

    captured = {}

    def _fake_find(filter, projection=None, limit=50, sort=None, include_similarity=True):
        """Capture incoming filter and return one vector row."""
        captured.update(filter)
        return [{"metadata": {"PID": "P31"}, "$vector": [0.1, 0.2]}]

    vector = VectorSearch.__new__(VectorSearch)
    vector.find = _fake_find

    item, embedding = vector.get_embedding_by_id("P31")

    assert item["metadata"]["PID"] == "P31"
    assert embedding == [0.1, 0.2]
    assert captured["metadata.PID"] == "P31"
    assert captured["metadata.IsProperty"] is True
