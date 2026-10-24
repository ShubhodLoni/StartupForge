const KEY_PREFIX = 'sf:report:'
const INDEX_KEY = 'sf:reports'
const MAX_REPORTS = 20

export function saveReport(report) {
  localStorage.setItem(KEY_PREFIX + report.id, JSON.stringify(report))
  const index = listReports().filter((r) => r.id !== report.id)
  index.unshift({ id: report.id, title: report.report.title, generated_at: report.generated_at })
  for (const stale of index.splice(MAX_REPORTS)) localStorage.removeItem(KEY_PREFIX + stale.id)
  localStorage.setItem(INDEX_KEY, JSON.stringify(index))
}

export function loadReport(id) {
  try {
    return JSON.parse(localStorage.getItem(KEY_PREFIX + id))
  } catch {
    return null
  }
}

export function listReports() {
  try {
    return JSON.parse(localStorage.getItem(INDEX_KEY)) || []
  } catch {
    return []
  }
}
