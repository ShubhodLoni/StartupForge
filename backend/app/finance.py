from pydantic import BaseModel, Field

BOUNDS: dict[str, tuple[float, float]] = {
    "price_per_month": (0.0, 1_000_000.0),
    "starting_customers": (0.0, 10_000_000.0),
    "new_customers_month_1": (0.0, 1_000_000.0),
    "new_customer_growth_pct": (-50.0, 100.0),
    "monthly_churn_pct": (0.0, 100.0),
    "gross_margin_pct": (0.0, 100.0),
    "cac": (0.0, 1_000_000.0),
    "fixed_costs_per_month": (0.0, 100_000_000.0),
    "starting_cash": (0.0, 10_000_000_000.0),
}

SCENARIOS: list[dict] = [
    {"name": "conservative", "label": "Conservative", "acquisition": 0.75, "growth": 0.5, "churn": 1.5},
    {"name": "base", "label": "Base", "acquisition": 1.0, "growth": 1.0, "churn": 1.0},
    {"name": "optimistic", "label": "Optimistic", "acquisition": 1.25, "growth": 1.5, "churn": 0.75},
]


def _field(name: str, description: str):
    lo, hi = BOUNDS[name]
    return Field(..., ge=lo, le=hi, description=description)


class FinanceAssumptions(BaseModel):
    price_per_month: float = _field("price_per_month", "Average revenue per customer per month, USD")
    starting_customers: float = _field("starting_customers", "Paying customers at month 0")
    new_customers_month_1: float = _field("new_customers_month_1", "New paying customers acquired in month 1")
    new_customer_growth_pct: float = _field(
        "new_customer_growth_pct", "Month-over-month growth of new customer acquisition, percent"
    )
    monthly_churn_pct: float = _field("monthly_churn_pct", "Share of customers lost each month, percent")
    gross_margin_pct: float = _field("gross_margin_pct", "Gross margin, percent of revenue")
    cac: float = _field("cac", "Customer acquisition cost per new customer, USD")
    fixed_costs_per_month: float = _field("fixed_costs_per_month", "Salaries, tools, rent, etc. per month, USD")
    starting_cash: float = _field("starting_cash", "Cash in the bank at month 0, USD")
    months: int = Field(24, ge=6, le=60, description="Projection horizon in months")


class MonthRow(BaseModel):
    month: int
    new_customers: float
    churned_customers: float
    customers: float
    mrr: float
    gross_profit: float
    marketing_spend: float
    fixed_costs: float
    net_income: float
    cash: float


class Metrics(BaseModel):
    ending_customers: float
    ending_mrr: float
    ending_arr: float
    total_revenue: float
    break_even_month: int | None = Field(description="First month with net income >= 0")
    cash_out_month: int | None = Field(description="First month the cash balance goes negative")
    min_cash: float
    funding_needed: float = Field(description="Extra cash needed to never go below zero")
    ltv: float | None = Field(description="Gross-margin lifetime value; None when churn is 0")
    ltv_to_cac: float | None
    cac_payback_months: float | None


class Projection(BaseModel):
    rows: list[MonthRow]
    metrics: Metrics


class Scenario(BaseModel):
    name: str
    label: str
    assumptions: FinanceAssumptions
    projection: Projection


class FinancialModel(BaseModel):
    assumptions: FinanceAssumptions
    scenarios: list[Scenario]
    rationale: list[str] = Field(default_factory=list, description="Why each assumption was chosen")
    adjustments: list[str] = Field(default_factory=list, description="Proposed values clamped into valid ranges")
    original_assumptions: FinanceAssumptions | None = Field(
        None, description="The agent's assumptions, kept when the founder edits them"
    )


def _r(x: float) -> float:
    return round(x, 2)


def project(a: FinanceAssumptions) -> Projection:
    growth = a.new_customer_growth_pct / 100
    churn = a.monthly_churn_pct / 100
    margin = a.gross_margin_pct / 100

    customers, cash = a.starting_customers, a.starting_cash
    rows: list[MonthRow] = []
    total_revenue = 0.0
    for m in range(1, a.months + 1):
        new = a.new_customers_month_1 * (1 + growth) ** (m - 1)
        churned = customers * churn
        customers = customers - churned + new
        mrr = customers * a.price_per_month
        gross_profit = mrr * margin
        marketing = new * a.cac
        net = gross_profit - marketing - a.fixed_costs_per_month
        cash += net
        total_revenue += mrr
        rows.append(
            MonthRow(
                month=m,
                new_customers=_r(new),
                churned_customers=_r(churned),
                customers=_r(customers),
                mrr=_r(mrr),
                gross_profit=_r(gross_profit),
                marketing_spend=_r(marketing),
                fixed_costs=_r(a.fixed_costs_per_month),
                net_income=_r(net),
                cash=_r(cash),
            )
        )

    unit_margin = a.price_per_month * margin
    ltv = unit_margin / churn if churn > 0 else None
    min_cash = min([a.starting_cash] + [r.cash for r in rows])
    metrics = Metrics(
        ending_customers=rows[-1].customers,
        ending_mrr=rows[-1].mrr,
        ending_arr=_r(rows[-1].mrr * 12),
        total_revenue=_r(total_revenue),
        break_even_month=next((r.month for r in rows if r.net_income >= 0), None),
        cash_out_month=next((r.month for r in rows if r.cash < 0), None),
        min_cash=_r(min_cash),
        funding_needed=_r(max(0.0, -min_cash)),
        ltv=_r(ltv) if ltv is not None else None,
        ltv_to_cac=_r(ltv / a.cac) if ltv is not None and a.cac > 0 else None,
        cac_payback_months=_r(a.cac / unit_margin) if unit_margin > 0 else None,
    )
    return Projection(rows=rows, metrics=metrics)


def scenario_assumptions(base: FinanceAssumptions, spec: dict) -> FinanceAssumptions:
    lo_g, hi_g = BOUNDS["new_customer_growth_pct"]
    return base.model_copy(
        update={
            "new_customers_month_1": base.new_customers_month_1 * spec["acquisition"],
            "new_customer_growth_pct": min(hi_g, max(lo_g, base.new_customer_growth_pct * spec["growth"])),
            "monthly_churn_pct": min(100.0, base.monthly_churn_pct * spec["churn"]),
        }
    )


def build_model(
    assumptions: FinanceAssumptions, rationale: list[str] | None = None, adjustments: list[str] | None = None
) -> FinancialModel:
    scenarios = []
    for spec in SCENARIOS:
        sa = scenario_assumptions(assumptions, spec)
        scenarios.append(Scenario(name=spec["name"], label=spec["label"], assumptions=sa, projection=project(sa)))
    return FinancialModel(
        assumptions=assumptions,
        scenarios=scenarios,
        rationale=rationale or [],
        adjustments=adjustments or [],
    )


def sanitize(values: dict) -> tuple[FinanceAssumptions, list[str]]:
    clean, notes = {}, []
    for name, (lo, hi) in BOUNDS.items():
        raw = values.get(name)
        try:
            v = float(raw)
        except (TypeError, ValueError):
            v = lo
            notes.append(f"{name}: missing or invalid value, set to {lo:g}")
        if v != v:
            v = lo
        if v < lo or v > hi:
            clamped = min(hi, max(lo, v))
            notes.append(f"{name}: {v:g} is outside {lo:g}-{hi:g}, clamped to {clamped:g}")
            v = clamped
        clean[name] = v
    return FinanceAssumptions(**clean), notes
