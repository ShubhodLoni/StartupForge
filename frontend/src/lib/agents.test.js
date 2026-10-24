import { summarizeAgentOutput } from './agents'

describe('summarizeAgentOutput', () => {
  it('summarizes successful search', () => {
    const output = { sources: [{}, {}, {}], retrieval: { status: 'ok', queries: ['a', 'b'] } }
    expect(summarizeAgentOutput('search', output)).toBe('3 sources from 2 searches')
  })

  it('explains disabled search', () => {
    expect(summarizeAgentOutput('search', { sources: [], retrieval: { status: 'disabled' } })).toMatch(/off/)
  })

  it('summarizes competitors and finance', () => {
    expect(summarizeAgentOutput('competitor', { competitors: { competitors: [{}] } })).toBe('1 verified competitor')
    const finance = {
      scenarios: [{ name: 'base', projection: { rows: new Array(24), metrics: { ending_mrr: 12500 } } }],
    }
    expect(summarizeAgentOutput('finance', { finance })).toBe('Base case: $12.5K MRR at month 24')
  })

  it('summarizes RAG indexing and the critic', () => {
    const output = { sources: [], retrieval: { status: 'ok', mode: 'rag', pages: 9, chunks: 41, queries: ['a'] } }
    expect(summarizeAgentOutput('search', output)).toBe('9 pages → 41 passages indexed')
    const fc = { claims_checked: 12, removed_citations: 1 }
    expect(summarizeAgentOutput('critic', { fact_check: fc })).toBe('12 claims checked · 1 citation removed')
  })

  it('returns null for agents without a summary', () => {
    expect(summarizeAgentOutput('research', {})).toBeNull()
  })
})
