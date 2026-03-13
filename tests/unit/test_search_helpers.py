import importlib
import sys
import types


def _ensure_service_import_stubs():
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
            def __init__(self, *_args, **_kwargs):
                pass

        fake_jina.JinaAIAPI = _DummyJina
        sys.modules["wikidatasearch.services.jina"] = fake_jina


def _service_classes():
    _ensure_service_import_stubs()

    hybrid_module = importlib.import_module("wikidatasearch.services.search.HybridSearch")
    keyword_module = importlib.import_module("wikidatasearch.services.search.KeywordSearch")
    vector_module = importlib.import_module("wikidatasearch.services.search.VectorSearch")

    return hybrid_module.HybridSearch, keyword_module.KeywordSearch, vector_module.VectorSearch

def test_reciprocal_rank_fusion_merges_sources_and_accumulates_rrf(test_ctx):
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


def test_vector_remove_duplicates_prefers_best_similarity_and_limits_k(test_ctx):
    _, _, VectorSearch = _service_classes()
    raw_results = [
        {"metadata": {"QID": "Q42"}, "$similarity": 0.60, "$vector": [0.1], "content": "A"},
        {"metadata": {"QID": "Q42"}, "$similarity": 0.95, "$vector": [0.9], "content": "B"},
        {"metadata": {"PID": "P31"}, "$similarity": 0.70, "$vector": [0.2], "content": "C"},
    ]

    deduped = VectorSearch.remove_duplicates(
        raw_results,
        K=1,
        return_vectors=True,
        return_text=True,
    )

    assert len(deduped) == 1
    assert deduped[0]["QID"] == "Q42"
    assert deduped[0]["similarity_score"] == 0.95
    assert deduped[0]["vector"] == [0.9]
    assert deduped[0]["text"] == "B"


def test_keyword_clean_query_removes_stopwords_and_caps_length(test_ctx):
    _, KeywordSearch, _ = _service_classes()
    keyword = KeywordSearch()

    cleaned = keyword._clean_query("the quick brown fox", "all")
    assert "the" not in cleaned.lower()
    assert "quick" in cleaned.lower()
    assert len(cleaned) <= 300

    very_long = "word " * 500
    cleaned_long = keyword._clean_query(very_long, "en")
    assert len(cleaned_long) <= 300
