import axios from 'axios'

import { createSSEParser } from '../lib/sse'

const API_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({ baseURL: API_URL, timeout: 15000 })

export async function getHealth() {
  const { data } = await api.get('/api/health')
  return data
}

function errorDetail(body, status) {
  const detail = body?.detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  return detail || `Request failed with status ${status}`
}

export async function streamReport(payload, { onEvent, signal } = {}) {
  const res = await fetch(`${API_URL}/api/reports/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(payload),
    signal,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(errorDetail(body, res.status))
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  const parse = createSSEParser()

  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    for (const evt of parse(decoder.decode(value, { stream: true }))) onEvent?.(evt)
  }
}

export const recomputeFinance = (assumptions) => call(api.post('/api/finance/projection', assumptions))

async function call(promise) {
  try {
    return (await promise).data
  } catch (err) {
    const res = err.response
    const error = new Error(res ? errorDetail(res.data, res.status) : 'Could not reach the backend.')
    error.status = res?.status
    throw error
  }
}

export const listReports = (limit = 20) => call(api.get('/api/reports', { params: { limit } }))
export const getReport = (id) => call(api.get(`/api/reports/${id}`))

export const updateReportFinance = (id, assumptions) => call(api.put(`/api/reports/${id}/finance`, assumptions))
