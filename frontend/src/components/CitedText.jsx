import { useCitations } from './report/citations'

const MARKER_RE = /\s*\[(\d+(?:\s*,\s*\d+)*)\]/g

export default function CitedText({ text, citationIds }) {
  const ctx = useCitations()
  const ids = citationIds ?? ctx.ids
  const parts = []
  let last = 0
  for (const match of text.matchAll(MARKER_RE)) {
    parts.push(text.slice(last, match.index))
    const valid = match[1]
      .split(',')
      .map((n) => Number(n.trim()))
      .filter((id) => ids.has(id))
    if (valid.length) {
      parts.push(
        <sup key={match.index} className="ml-0.5 whitespace-nowrap">
          {valid.map((id) => (
            <a
              key={id}
              href={`#source-${id}`}
              onClick={(e) => {
                if (!ctx.openSource) return
                e.preventDefault()
                ctx.openSource(id)
              }}
              className="font-mono text-[0.7rem] text-neutral-500 transition hover:text-white"
              aria-label={`Source ${id}`}
            >
              [{id}]
            </a>
          ))}
        </sup>,
      )
    }
    last = match.index + match[0].length
  }
  parts.push(text.slice(last))
  return <>{parts}</>
}
