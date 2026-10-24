function rows(n, mrr0) {
  return Array.from({ length: n }, (_, i) => ({
    month: i + 1,
    new_customers: 5,
    churned_customers: 0,
    customers: 5 * (i + 1),
    mrr: mrr0 * (i + 1),
    gross_profit: mrr0 * (i + 1) * 0.8,
    marketing_spend: 2000,
    fixed_costs: 15000,
    net_income: mrr0 * (i + 1) * 0.8 - 17000,
    cash: 250000 - 1000 * (i + 1),
  }))
}

const assumptions = {
  price_per_month: 199,
  starting_customers: 0,
  new_customers_month_1: 5,
  new_customer_growth_pct: 10,
  monthly_churn_pct: 3,
  gross_margin_pct: 80,
  cac: 400,
  fixed_costs_per_month: 15000,
  starting_cash: 250000,
  months: 24,
}

function scenario(name, label, mrr0) {
  const r = rows(24, mrr0)
  return {
    name,
    label,
    assumptions,
    projection: {
      rows: r,
      metrics: {
        ending_customers: 120,
        ending_mrr: r[23].mrr,
        ending_arr: r[23].mrr * 12,
        total_revenue: 1,
        break_even_month: name === 'conservative' ? null : 14,
        cash_out_month: null,
        min_cash: 226000,
        funding_needed: 0,
        ltv: 5306.67,
        ltv_to_cac: 13.27,
        cac_payback_months: 2.51,
      },
    },
  }
}

export const finance = {
  assumptions,
  scenarios: [
    scenario('conservative', 'Conservative', 500),
    scenario('base', 'Base', 1000),
    scenario('optimistic', 'Optimistic', 1500),
  ],
  rationale: ['price_per_month: Estimate: typical SMB software price', 'cac: survey figure [1]'],
  adjustments: ['gross_margin_pct: 120 is outside 0-100, clamped to 100'],
}

export const report = {
  id: '1',
  request: { idea: 'AI receptionist for dental clinics' },
  research: {
    market_summary: 'Clinics struggle with scheduling.',
    target_customers: ['Dental clinics'],
    pain_points: ['Missed calls'],
    key_trends: ['Online booking'],
    risks: ['Integrations'],
    assumptions_to_verify: ['Clinic adoption rate'],
  },
  competitors: {
    competitors: [
      {
        name: 'Acme Reception',
        description: 'AI phone answering [1].',
        strengths: ['Dental focus'],
        weaknesses: ['Likely: price'],
        source_ids: [1],
      },
    ],
    alternatives: ['Front-desk staff'],
    differentiation: ['Integrations'],
    market_gaps: ['After-hours booking'],
    unverified_competitors: ['Ghost Corp'],
  },
  product: {
    product_vision: 'Never miss a patient call.',
    mvp_features: [
      { name: 'Call answering', description: 'AI answers calls', priority: 'must' },
      { name: 'SMS reminders', description: 'Reminders', priority: 'could' },
    ],
    user_journey: ['Patient calls', 'AI books'],
    differentiators: ['Dental workflows'],
    success_metrics: ['Calls answered'],
    pricing_options: ['Per location'],
    build_risks: ['ASR accuracy'],
  },
  finance,
  report: {
    title: 'ClinicFlow',
    executive_summary: 'AI scheduling assistant.',
    problem: 'Clinics miss many calls [1].',
    solution: 'An AI receptionist.',
    value_proposition: 'Less admin.',
    target_customers: ['Dental clinics'],
    go_to_market: ['Pilot with 5 clinics'],
    risks: ['Integrations'],
    next_steps: ['Interview 20 managers'],
    financial_summary: 'Base case projects growth under editable assumptions.',
    verification_needed: ['Clinic adoption rate'],
  },
  fact_check: {
    claims_checked: 3,
    removed_citations: 1,
    items: [
      { location: 'report.problem', claim: 'Clinics miss many calls.', source_id: 1, verdict: 'supported', reason: 'Stated directly.' },
      { location: 'research.key_trends[0]', claim: 'Online booking is standard.', source_id: 2, verdict: 'unsupported', reason: 'Source is about phones.' },
      { location: 'research.pain_points[0]', claim: 'Missed calls.', source_id: 1, verdict: 'partial', reason: 'Only partly.' },
    ],
    figure_flags: [
      { location: 'research.market_summary', text: 'The market is $9 billion.', figure: '$9 billion', issue: 'uncited' },
    ],
  },
  citations: [{ id: 1, title: 'Source A', url: 'https://www.example.org/a', snippet: 'Verbatim excerpt' }],
  retrieval: { status: 'ok', queries: ['dental missed calls'] },
  model: 'llama-3.3-70b-versatile',
  generated_at: '2026-10-24T12:00:00Z',
  data_provenance: 'web_sources',
}
