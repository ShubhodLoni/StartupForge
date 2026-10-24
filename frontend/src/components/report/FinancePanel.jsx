import { Loader2, RotateCcw } from 'lucide-react'
import { useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  Rectangle,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { num, numFull, usd, usdFull } from '../../lib/format'
import CitedText from '../CitedText'
import { EmptyState, Section } from './ui'

const C = {
  grid: '#1a1a1a',
  zero: '#3a3a3a',
  tick: '#737373',
  bar: '#8a8a8a',
  surface: '#0a0a0a',
  base: '#f5f5f5',
  conservative: '#d95926',
  optimistic: '#199e70',
}

const FIELDS = [
  { key: 'price_per_month', label: 'Price / customer / month', unit: '$', step: 1 },
  { key: 'starting_customers', label: 'Customers at launch', step: 1 },
  { key: 'new_customers_month_1', label: 'New customers, month 1', step: 1 },
  { key: 'new_customer_growth_pct', label: 'Acquisition growth / month', unit: '%', step: 0.5 },
  { key: 'monthly_churn_pct', label: 'Churn / month', unit: '%', step: 0.5 },
  { key: 'gross_margin_pct', label: 'Gross margin', unit: '%', step: 1 },
  { key: 'cac', label: 'Customer acquisition cost', unit: '$', step: 10 },
  { key: 'fixed_costs_per_month', label: 'Fixed costs / month', unit: '$', step: 500 },
  { key: 'starting_cash', label: 'Starting cash', unit: '$', step: 1000 },
  { key: 'months', label: 'Horizon (months)', step: 1 },
]

const axisProps = {
  stroke: C.zero,
  tick: { fill: C.tick, fontSize: 11, fontFamily: 'Geist Mono Variable, monospace' },
  tickLine: false,
  axisLine: false,
}

function ChartTooltip({ active, payload, label, format = usdFull }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-line-strong bg-black/95 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1.5 text-neutral-500">Month {label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} className="flex items-center gap-2 text-neutral-200">
          <span className="h-0.5 w-3 rounded" style={{ background: p.color || p.fill || p.stroke }} />
          <span className="text-neutral-400">{p.name}</span>
          <span className="ml-auto pl-4 font-mono tabular-nums text-white">{format(p.value)}</span>
        </p>
      ))}
    </div>
  )
}

function Tile({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-line bg-panel p-4">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="mt-2 text-2xl font-medium tracking-tight text-white">{value}</p>
      {hint && <p className="mt-1 text-xs text-neutral-600">{hint}</p>}
    </div>
  )
}

function LegendKey({ color, label }) {
  return (
    <span className="flex items-center gap-1.5 text-xs text-neutral-400">
      <span className="h-0.5 w-3.5 rounded" style={{ background: color }} />
      {label}
    </span>
  )
}

function EndLabel({ index, x, y, value, lastIndex, text }) {
  if (index !== lastIndex || value == null) return null
  return (
    <text x={x + 8} y={y} dy={4} fill="#a3a3a3" fontSize={11}>
      {text}
    </text>
  )
}

function SignedBar(props) {
  const radius = props.value >= 0 ? [3, 3, 0, 0] : [0, 0, 3, 3]
  return <Rectangle {...props} radius={radius} />
}

function MrrChart({ scenarios }) {
  const data = useMemo(
    () =>
      scenarios[0].projection.rows.map((row, i) => {
        const point = { month: row.month }
        for (const s of scenarios) point[s.name] = s.projection.rows[i]?.mrr
        return point
      }),
    [scenarios],
  )
  const last = data.length - 1
  return (
    <Section title="Monthly recurring revenue by scenario">
      <div className="mb-3 flex flex-wrap gap-4">
        {scenarios.map((s) => (
          <LegendKey key={s.name} color={C[s.name]} label={s.label} />
        ))}
      </div>
      <div className="h-72" role="img" aria-label="Line chart of monthly recurring revenue for each scenario">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 88, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={C.grid} vertical={false} />
            <XAxis dataKey="month" {...axisProps} interval="preserveStartEnd" minTickGap={24} />
            <YAxis {...axisProps} tickFormatter={usd} width={56} />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: C.zero }} />
            {scenarios.map((s) => (
              <Line
                key={s.name}
                dataKey={s.name}
                name={s.label}
                stroke={C[s.name]}
                strokeWidth={s.name === 'base' ? 2 : 1.5}
                dot={false}
                activeDot={{ r: 4, stroke: C.surface, strokeWidth: 2 }}
                isAnimationActive={false}
              >
                <LabelList dataKey={s.name} content={<EndLabel lastIndex={last} text={s.label} />} />
              </Line>
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Section>
  )
}

function CashChart({ rows }) {
  return (
    <Section title="Cash balance">
      <div className="h-56" role="img" aria-label="Area chart of cash balance by month">
        <ResponsiveContainer>
          <AreaChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={C.grid} vertical={false} />
            <XAxis dataKey="month" {...axisProps} interval="preserveStartEnd" minTickGap={24} />
            <YAxis {...axisProps} tickFormatter={usd} width={56} />
            <ReferenceLine y={0} stroke={C.zero} />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: C.zero }} />
            <Area
              dataKey="cash"
              name="Cash"
              stroke={C.base}
              strokeWidth={2}
              fill={C.base}
              fillOpacity={0.06}
              activeDot={{ r: 4, stroke: C.surface, strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Section>
  )
}

function NetIncomeChart({ rows }) {
  return (
    <Section title="Net income per month">
      <div className="h-56" role="img" aria-label="Bar chart of monthly net income">
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
            <CartesianGrid stroke={C.grid} vertical={false} />
            <XAxis dataKey="month" {...axisProps} interval="preserveStartEnd" minTickGap={24} />
            <YAxis {...axisProps} tickFormatter={usd} width={56} />
            <ReferenceLine y={0} stroke={C.zero} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
            <Bar
              dataKey="net_income"
              name="Net income"
              fill={C.bar}
              maxBarSize={24}
              shape={<SignedBar />}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Section>
  )
}

function ProjectionTable({ rows }) {
  return (
    <details className="group rounded-xl border border-line bg-panel">
      <summary className="cursor-pointer select-none px-5 py-4 text-sm text-neutral-400 hover:text-white">
        Monthly table
      </summary>
      <div className="overflow-x-auto border-t border-line">
        <table className="w-full text-right font-mono text-xs tabular-nums">
          <thead className="text-neutral-500">
            <tr>
              {['Month', 'Customers', 'MRR', 'Gross profit', 'Marketing', 'Net income', 'Cash'].map((h) => (
                <th key={h} className="px-4 py-2.5 font-normal first:text-left">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="text-neutral-300">
            {rows.map((r) => (
              <tr key={r.month} className="border-t border-line">
                <td className="px-4 py-2 text-left text-neutral-500">{r.month}</td>
                <td className="px-4 py-2">{numFull(Math.round(r.customers))}</td>
                <td className="px-4 py-2">{usdFull(r.mrr)}</td>
                <td className="px-4 py-2">{usdFull(r.gross_profit)}</td>
                <td className="px-4 py-2">{usdFull(r.marketing_spend)}</td>
                <td className={`px-4 py-2 ${r.net_income < 0 ? 'text-red-400' : ''}`}>{usdFull(r.net_income)}</td>
                <td className={`px-4 py-2 ${r.cash < 0 ? 'text-red-400' : ''}`}>{usdFull(r.cash)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

function AssumptionsEditor({ finance, onRecalculate }) {
  const original = finance.original_assumptions || finance.assumptions
  const [values, setValues] = useState(() => toStrings(finance.assumptions))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function submit(next) {
    setBusy(true)
    setError(null)
    try {
      const parsed = Object.fromEntries(FIELDS.map((f) => [f.key, Number(next[f.key])]))
      const bad = FIELDS.find((f) => next[f.key] === '' || Number.isNaN(parsed[f.key]))
      if (bad) throw new Error(`${bad.label} must be a number.`)
      await onRecalculate(parsed)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const edited = FIELDS.some((f) => Number(values[f.key]) !== Number(original[f.key]))

  return (
    <Section title="Assumptions">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit(values)
        }}
        className="space-y-5"
      >
        <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2 lg:grid-cols-5">
          {FIELDS.map((f) => (
            <label key={f.key} className="block">
              <span className="mb-1 block text-xs text-neutral-500">{f.label}</span>
              <span className="flex items-center rounded-md border border-line bg-black focus-within:border-neutral-500">
                {f.unit === '$' && <span className="pl-2.5 text-xs text-neutral-600">$</span>}
                <input
                  type="number"
                  inputMode="decimal"
                  step={f.step}
                  value={values[f.key]}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                  className="w-full min-w-0 bg-transparent px-2.5 py-1.5 font-mono text-sm text-white outline-none"
                  aria-label={f.label}
                />
                {f.unit === '%' && <span className="pr-2.5 text-xs text-neutral-600">%</span>}
              </span>
            </label>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-md bg-white px-3.5 py-1.5 text-sm font-medium text-black transition hover:bg-neutral-200 disabled:opacity-60"
          >
            {busy && <Loader2 className="size-3.5 animate-spin" />}
            Recalculate
          </button>
          {edited && (
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                const reset = toStrings(original)
                setValues(reset)
                submit(reset)
              }}
              className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-neutral-400 transition hover:text-white"
            >
              <RotateCcw className="size-3.5" /> Reset to agent’s values
            </button>
          )}
          {error && (
            <p role="alert" className="text-sm text-red-400">
              {error}
            </p>
          )}
        </div>
      </form>

      {(finance.rationale?.length > 0 || finance.adjustments?.length > 0) && (
        <div className="mt-6 grid gap-6 border-t border-line pt-5 md:grid-cols-2">
          {finance.rationale?.length > 0 && (
            <div>
              <p className="mb-2 text-xs uppercase tracking-widest text-neutral-600">Why the agent chose these</p>
              <ul className="space-y-1.5 text-sm leading-relaxed text-neutral-400">
                {finance.rationale.map((r, i) => (
                  <li key={i}>
                    <CitedText text={r} />
                  </li>
                ))}
              </ul>
            </div>
          )}
          {finance.adjustments?.length > 0 && (
            <div>
              <p className="mb-2 text-xs uppercase tracking-widest text-neutral-600">Corrected by the engine</p>
              <ul className="space-y-1.5 font-mono text-xs leading-relaxed text-neutral-500">
                {finance.adjustments.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Section>
  )
}

function toStrings(assumptions) {
  return Object.fromEntries(FIELDS.map((f) => [f.key, String(assumptions[f.key] ?? '')]))
}

export default function FinancePanel({ finance, onRecalculate }) {
  const [scenarioName, setScenarioName] = useState('base')
  if (!finance) return <EmptyState>Not available for this report. Run a new analysis to generate it.</EmptyState>

  const scenario = finance.scenarios.find((s) => s.name === scenarioName) || finance.scenarios[1]
  const { rows, metrics: m } = scenario.projection
  const months = rows.length

  return (
    <div className="space-y-4">
      <p className="text-sm leading-relaxed text-neutral-500">
        Illustrative projections, not forecasts. Every number below is computed with fixed formulas from the
        assumptions at the bottom. The AI only proposed the starting assumptions, so edit them to match your data.
        Customer counts are averages and are rounded for display.
      </p>

      <div className="flex items-center justify-between gap-4">
        <div role="tablist" aria-label="Scenario" className="inline-flex rounded-lg border border-line p-0.5">
          {finance.scenarios.map((s) => (
            <button
              key={s.name}
              role="tab"
              aria-selected={s.name === scenario.name}
              onClick={() => setScenarioName(s.name)}
              className={`rounded-md px-3 py-1 text-xs transition ${
                s.name === scenario.name ? 'bg-white text-black' : 'text-neutral-400 hover:text-white'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Tile label={`MRR at month ${months}`} value={usd(m.ending_mrr)} hint={`${usd(m.ending_arr)} ARR`} />
        <Tile label="Customers" value={num(Math.round(m.ending_customers))} hint={`at month ${months}`} />
        <Tile
          label="Break-even"
          value={m.break_even_month ? `Month ${m.break_even_month}` : 'Not reached'}
          hint={m.break_even_month ? 'first profitable month' : `within ${months} months`}
        />
        <Tile
          label="Funding needed"
          value={usd(m.funding_needed)}
          hint={m.cash_out_month ? `cash runs out in month ${m.cash_out_month}` : 'cash stays positive'}
        />
        <Tile
          label="LTV : CAC"
          value={m.ltv_to_cac != null ? `${m.ltv_to_cac.toFixed(1)}×` : '—'}
          hint={m.cac_payback_months != null ? `${m.cac_payback_months.toFixed(1)} mo CAC payback` : null}
        />
      </div>

      <MrrChart scenarios={finance.scenarios} />
      <div className="grid gap-4 lg:grid-cols-2">
        <CashChart rows={rows} />
        <NetIncomeChart rows={rows} />
      </div>
      <ProjectionTable rows={rows} />
      <AssumptionsEditor key={JSON.stringify(finance.assumptions)} finance={finance} onRecalculate={onRecalculate} />
    </div>
  )
}
