import pytest
from pydantic import ValidationError

from app.finance import FinanceAssumptions, build_model, project, sanitize

BASE = dict(
    price_per_month=100,
    starting_customers=0,
    new_customers_month_1=10,
    new_customer_growth_pct=0,
    monthly_churn_pct=0,
    gross_margin_pct=80,
    cac=200,
    fixed_costs_per_month=1000,
    starting_cash=5000,
    months=6,
)


def a(**overrides):
    return FinanceAssumptions(**{**BASE, **overrides})


def test_hand_computed_months():
    rows = project(a()).rows
    assert (rows[0].customers, rows[0].mrr, rows[0].net_income, rows[0].cash) == (10, 1000, -2200, 2800)
    assert (rows[1].customers, rows[1].net_income, rows[1].cash) == (20, -1400, 1400)
    assert rows[2].net_income == -600
    assert rows[3].net_income == 200


def test_metrics():
    m = project(a()).metrics
    assert m.break_even_month == 4
    assert m.cash_out_month is None
    assert m.min_cash == 800
    assert m.funding_needed == 0
    assert m.ending_customers == 60
    assert m.ending_mrr == 6000
    assert m.ending_arr == 72000
    assert m.ltv is None
    assert m.cac_payback_months == 2.5


def test_churn_and_growth():
    rows = project(a(monthly_churn_pct=10, new_customer_growth_pct=50, starting_customers=100)).rows
    assert rows[0].churned_customers == 10
    assert rows[0].customers == 100
    assert rows[1].new_customers == 15
    assert rows[1].customers == 105


def test_unit_economics_with_churn():
    m = project(a(monthly_churn_pct=5)).metrics
    assert m.ltv == 1600
    assert m.ltv_to_cac == 8


def test_funding_needed_and_cash_out():
    m = project(a(starting_cash=0)).metrics
    assert m.cash_out_month == 1
    assert m.min_cash == -4200
    assert m.funding_needed == 4200


def test_deterministic():
    assert project(a(monthly_churn_pct=3.3)) == project(a(monthly_churn_pct=3.3))


def test_scenarios_ordered():
    model = build_model(a(monthly_churn_pct=5, new_customer_growth_pct=10, months=24))
    names = [s.name for s in model.scenarios]
    assert names == ["conservative", "base", "optimistic"]
    mrr = [s.projection.metrics.ending_mrr for s in model.scenarios]
    assert mrr[0] < mrr[1] < mrr[2]
    assert model.scenarios[1].assumptions == model.assumptions


def test_validation_rejects_out_of_range():
    with pytest.raises(ValidationError):
        a(monthly_churn_pct=150)


def test_sanitize_clamps_and_reports():
    values = {**BASE, "monthly_churn_pct": 140, "cac": -5, "price_per_month": "abc"}
    clean, notes = sanitize(values)
    assert clean.monthly_churn_pct == 100
    assert clean.cac == 0
    assert clean.price_per_month == 0
    assert len(notes) == 3
