import json

from app.config import Settings, get_settings
from app.main import app, get_search_client
from app.schemas import StartupReport

IDEA = {"idea": "AI receptionist for small dental clinics", "industry": "Healthcare"}


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.replace("\r\n", "\n").strip().split("\n\n"):
        event, data = None, []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data.append(line[len("data:"):].strip())
        if event:
            events.append((event, json.loads("\n".join(data))))
    return events


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["agents"] == ["search", "research", "competitor", "product", "finance", "report", "critic"]
    assert body["storage"] == "memory"
    assert "search_configured" in body


def test_create_report(client):
    res = client.post("/api/reports", json=IDEA)
    assert res.status_code == 200
    body = res.json()
    assert body["report"]["title"] == "ClinicFlow"
    assert body["research"]["target_customers"] == ["Small dental clinics"]
    assert [c["id"] for c in body["citations"]] == [1, 2, 3, 4]
    assert body["competitors"]["competitors"][0]["name"] == "Acme Reception"
    assert body["product"]["mvp_features"][0]["priority"] == "must"
    assert len(body["finance"]["scenarios"]) == 3
    assert body["citations"][0]["url"] == "https://example.org/missed-calls"
    assert body["citations"][1]["snippet"] == "Staff spend hours on the phone."
    assert body["retrieval"]["status"] == "ok"
    assert body["data_provenance"] == "web_sources"
    assert body["request"]["idea"] == IDEA["idea"]


def test_report_without_search_has_no_citations(client):
    app.dependency_overrides[get_search_client] = lambda: None
    body = client.post("/api/reports", json=IDEA).json()
    assert body["citations"] == []
    assert body["retrieval"]["status"] == "disabled"
    assert body["data_provenance"] == "llm_knowledge_unverified"


def test_rejects_short_idea(client):
    assert client.post("/api/reports", json={"idea": "short"}).status_code == 422


def test_pipeline_failure_returns_502(client, fake_llm):
    fake_llm.fail_on = StartupReport
    res = client.post("/api/reports", json=IDEA)
    assert res.status_code == 502
    assert "upstream LLM failure" in res.json()["detail"]


def test_missing_api_key_returns_503():
    app.dependency_overrides[get_settings] = lambda: Settings(groq_api_key="", _env_file=None)
    try:
        from fastapi.testclient import TestClient

        res = TestClient(app).post("/api/reports", json=IDEA)
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 503
    assert "GROQ_API_KEY" in res.json()["detail"]


def test_stream_emits_agent_progress_then_report(client):
    res = client.post("/api/reports/stream", json=IDEA)
    assert res.status_code == 200
    events = parse_sse(res.text)

    names = [(e, d.get("agent")) for e, d in events]
    expected = []
    for agent in ["search", "research", "competitor", "product", "finance", "report", "critic"]:
        expected += [("agent_started", agent), ("agent_completed", agent)]
    assert names == expected + [("complete", None)]
    assert len(events[1][1]["output"]["sources"]) == 4
    assert events[3][1]["output"]["research"]["pain_points"]
    assert events[-1][1]["report"]["title"] == "ClinicFlow"


def test_stream_reports_errors(client, fake_llm):
    fake_llm.fail_on = StartupReport
    events = parse_sse(client.post("/api/reports/stream", json=IDEA).text)
    assert events[-1][0] == "error"
    assert "upstream LLM failure" in events[-1][1]["detail"]
    assert all(e != "complete" for e, _ in events)


def test_finance_projection_endpoint_is_deterministic(client):
    body = {
        "price_per_month": 100, "starting_customers": 0, "new_customers_month_1": 10,
        "new_customer_growth_pct": 0, "monthly_churn_pct": 0, "gross_margin_pct": 80, "cac": 200,
        "fixed_costs_per_month": 1000, "starting_cash": 5000, "months": 6,
    }
    first = client.post("/api/finance/projection", json=body).json()
    assert first == client.post("/api/finance/projection", json=body).json()
    base = first["scenarios"][1]
    assert base["projection"]["rows"][0]["cash"] == 2800
    assert base["projection"]["metrics"]["break_even_month"] == 4


def test_finance_projection_rejects_invalid_assumptions(client):
    res = client.post("/api/finance/projection", json={"price_per_month": -1})
    assert res.status_code == 422
