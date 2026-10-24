import { createSSEParser } from './sse'

describe('createSSEParser', () => {
  it('parses complete events with JSON data', () => {
    const push = createSSEParser()
    const events = push('event: agent_started\r\ndata: {"agent":"research"}\r\n\r\n')
    expect(events).toEqual([{ event: 'agent_started', data: { agent: 'research' } }])
  })

  it('buffers events split across chunks', () => {
    const push = createSSEParser()
    expect(push('event: complete\ndata: {"id":')).toEqual([])
    expect(push('"abc"}\n\nevent: error\n')).toEqual([{ event: 'complete', data: { id: 'abc' } }])
    expect(push('data: {"detail":"boom"}\n\n')).toEqual([{ event: 'error', data: { detail: 'boom' } }])
  })

  it('ignores keep-alive comments', () => {
    const push = createSSEParser()
    expect(push(': ping - 2026-10-24\n\n')).toEqual([])
  })
})
