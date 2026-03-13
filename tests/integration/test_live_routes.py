import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import pytest


pytestmark = pytest.mark.integration
LOCAL_BASE_URL = "http://127.0.0.1:8080"


def _api_get(path: str, params: dict | None = None, expected_status: int | None = 200) -> dict:
    base_url = LOCAL_BASE_URL
    query = f"?{urlencode(params or {}, doseq=True)}" if params else ""
    req = Request(
        f"{base_url}{path}{query}",
        method="GET",
        headers={
            "User-Agent": "Pytest Integration Suite/1.0 (integration-tests@example.org)",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(req, timeout=60) as res:
            status = res.status
            body_bytes = res.read()
            headers = dict(res.headers.items())
    except HTTPError as e:
        status = e.code
        body_bytes = e.read()
        headers = dict(e.headers.items()) if e.headers else {}
    except URLError as e:
        pytest.fail(f"Local API is unreachable at {base_url}: {e}")

    body_text = body_bytes.decode("utf-8", errors="replace")
    try:
        payload = json.loads(body_text)
    except json.JSONDecodeError:
        payload = body_text

    if expected_status is not None:
        assert status == expected_status, f"{path} expected {expected_status}, got {status}: {payload}"

    return {"status": status, "payload": payload, "headers": headers}


def _ids(rows: list[dict]) -> set[str]:
    return {row.get("QID") or row.get("PID") for row in rows if isinstance(row, dict)}


def _scores_non_increasing(rows: list[dict]) -> bool:
    scores = [row.get("similarity_score", 0.0) for row in rows]
    return all(left >= right for left, right in zip(scores, scores[1:]))


def test_root_returns_html():
    result = _api_get("/", expected_status=200)
    content_type = result["headers"].get("Content-Type") or result["headers"].get("content-type", "")
    assert "text/html" in content_type


def test_languages_contract():
    result = _api_get("/languages", expected_status=200)
    payload = result["payload"]

    assert isinstance(payload, dict)
    assert set(payload.keys()) == {"vectordb_langs", "other_langs"}
    assert "all" not in set(payload["vectordb_langs"])


def test_item_query_contract_and_limit():
    k = 5
    result = _api_get(
        "/item/query/",
        params={"query": "Douglas Adams", "lang": "all", "K": k, "rerank": False},
        expected_status=200,
    )
    rows = result["payload"]

    assert isinstance(rows, list)
    assert len(rows) <= k
    assert all("QID" in row for row in rows)
    assert all("similarity_score" in row for row in rows)


def test_property_query_contract_and_limit():
    k = 5
    result = _api_get(
        "/property/query/",
        params={"query": "instance of", "lang": "all", "K": k, "rerank": False},
        expected_status=200,
    )
    rows = result["payload"]

    assert isinstance(rows, list)
    assert len(rows) <= k
    assert all("PID" in row for row in rows)
    assert all("similarity_score" in row for row in rows)


def test_similarity_score_mixed_ids_contract():
    qid = "Q42,P31,Q5"
    result = _api_get(
        "/similarity-score/",
        params={"query": "capital of France", "qid": qid, "lang": "all"},
        expected_status=200,
    )
    rows = result["payload"]
    requested = {value.strip() for value in qid.split(",")}

    assert isinstance(rows, list)
    assert _ids(rows).issubset(requested)
    assert all(("QID" in row) ^ ("PID" in row) for row in rows)
    assert all("similarity_score" in row for row in rows)
    assert _scores_non_increasing(rows)


def test_reject_return_vectors_for_item_property_and_similarity():
    item = _api_get(
        "/item/query/",
        params={"query": "Douglas Adams", "return_vectors": True},
        expected_status=422,
    )
    prop = _api_get(
        "/property/query/",
        params={"query": "instance of", "return_vectors": True},
        expected_status=422,
    )
    sim = _api_get(
        "/similarity-score/",
        params={"query": "capital of France", "qid": "Q42", "return_vectors": True},
        expected_status=422,
    )

    assert item["status"] == 422
    assert prop["status"] == 422
    assert sim["status"] == 422


def test_similarity_score_rejects_more_than_100_ids():
    many_ids = ",".join(f"Q{i}" for i in range(1, 105))
    result = _api_get(
        "/similarity-score/",
        params={"query": "test query", "qid": many_ids, "lang": "all"},
        expected_status=422,
    )
    payload = result["payload"]

    assert isinstance(payload, dict)
    assert "detail" in payload


def test_item_query_rejects_empty_query():
    result = _api_get(
        "/item/query/",
        params={"query": "", "lang": "all", "K": 5},
        expected_status=422,
    )
    assert result["status"] == 422


def test_property_query_rejects_empty_query():
    result = _api_get(
        "/property/query/",
        params={"query": "", "lang": "all", "K": 5},
        expected_status=422,
    )
    assert result["status"] == 422


def test_similarity_score_rejects_empty_query():
    result = _api_get(
        "/similarity-score/",
        params={"query": "", "qid": "Q42", "lang": "all"},
        expected_status=422,
    )
    assert result["status"] == 422


def test_similarity_score_rejects_missing_qid():
    result = _api_get(
        "/similarity-score/",
        params={"query": "capital of France", "lang": "all"},
        expected_status=422,
    )
    assert result["status"] == 422


def test_item_query_rejects_k_too_large():
    result = _api_get(
        "/item/query/",
        params={"query": "Douglas Adams", "lang": "all", "K": 9999},
        expected_status=422,
    )
    assert result["status"] == 422


def test_property_query_rejects_k_too_large():
    result = _api_get(
        "/property/query/",
        params={"query": "instance of", "lang": "all", "K": 9999},
        expected_status=422,
    )
    assert result["status"] == 422
