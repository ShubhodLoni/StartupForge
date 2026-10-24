const compactUsd = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  notation: 'compact',
  maximumFractionDigits: 1,
})
const fullUsd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
const compactNum = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })
const fullNum = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

export const usd = (v) => (v == null ? '—' : compactUsd.format(v))
export const usdFull = (v) => (v == null ? '—' : fullUsd.format(v))
export const num = (v) => (v == null ? '—' : compactNum.format(v))
export const numFull = (v) => (v == null ? '—' : fullNum.format(v))
