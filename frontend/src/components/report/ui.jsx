import CitedText from '../CitedText'

export function Section({ title, children, className = '' }) {
  return (
    <section className={`rounded-xl border border-line bg-panel p-5 sm:p-6 ${className}`}>
      {title && <h2 className="mb-4 text-xs font-medium uppercase tracking-widest text-neutral-500">{title}</h2>}
      {children}
    </section>
  )
}

export function Prose({ text }) {
  return (
    <p className="text-[15px] leading-relaxed text-neutral-200">
      <CitedText text={text} />
    </p>
  )
}

export function BulletList({ items, ordered = false }) {
  if (!items?.length) return <p className="text-sm text-neutral-600">None.</p>
  const List = ordered ? 'ol' : 'ul'
  return (
    <List className="space-y-2.5">
      {items.map((item, i) => (
        <li key={i} className="flex gap-3 text-sm leading-relaxed text-neutral-300">
          {ordered ? (
            <span className="w-5 shrink-0 font-mono text-xs leading-6 text-neutral-600">{i + 1}.</span>
          ) : (
            <span className="mt-[9px] h-px w-2.5 shrink-0 bg-neutral-600" />
          )}
          <span>
            <CitedText text={item} />
          </span>
        </li>
      ))}
    </List>
  )
}

export function EmptyState({ children }) {
  return (
    <div className="rounded-xl border border-dashed border-line p-8 text-center text-sm text-neutral-500">
      {children}
    </div>
  )
}

export function Grid({ children }) {
  return <div className="grid gap-4 md:grid-cols-2">{children}</div>
}
