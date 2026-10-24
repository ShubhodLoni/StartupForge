IDEA = {"idea": "AI receptionist for small dental clinics"}

EDIT = {
    "price_per_month": 299, "starting_customers": 0, "new_customers_month_1": 5,
    "new_customer_growth_pct": 10, "monthly_churn_pct": 3, "gross_margin_pct": 80, "cac": 400,
    "fixed_costs_per_month": 15000, "starting_cash": 250000, "months": 12,
}


def test_reports_are_saved_listed_and_fetched(client):
    created = client.post("/api/reports", json=IDEA).json()

    listed = client.get("/api/reports").json()
    assert [r["id"] for r in listed] == [created["id"]]
    assert listed[0]["title"] == "ClinicFlow"

    fetched = client.get(f"/api/reports/{created['id']}").json()
    assert fetched == created


def test_streamed_reports_are_saved(client):
    client.post("/api/reports/stream", json=IDEA)
    assert len(client.get("/api/reports").json()) == 1


def test_unknown_report_is_404(client):
    assert client.get("/api/reports/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/api/reports/not-a-uuid").status_code == 404


def test_finance_edit_is_recomputed_server_side_and_saved(client):
    created = client.post("/api/reports", json=IDEA).json()
    agent_assumptions = created["finance"]["assumptions"]

    res = client.put(f"/api/reports/{created['id']}/finance", json=EDIT)
    assert res.status_code == 200
    model = res.json()
    base = model["scenarios"][1]["projection"]
    assert len(base["rows"]) == 12
    assert base["rows"][0]["mrr"] == 5 * 299
    assert model["original_assumptions"] == agent_assumptions
    assert model["rationale"] == created["finance"]["rationale"]

    model2 = client.put(f"/api/reports/{created['id']}/finance", json={**EDIT, "price_per_month": 100}).json()
    assert model2["original_assumptions"] == agent_assumptions

    saved = client.get(f"/api/reports/{created['id']}").json()
    assert saved["finance"]["assumptions"]["price_per_month"] == 100


def test_finance_edit_validates_and_404s(client):
    created = client.post("/api/reports", json=IDEA).json()
    assert client.put(f"/api/reports/{created['id']}/finance", json={**EDIT, "monthly_churn_pct": 400}).status_code == 422
    assert client.put("/api/reports/00000000-0000-0000-0000-000000000000/finance", json=EDIT).status_code == 404
