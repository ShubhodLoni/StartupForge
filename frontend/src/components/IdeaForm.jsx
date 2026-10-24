import { ArrowRight, Loader2 } from 'lucide-react'
import { useState } from 'react'

const MIN_IDEA = 10
const MAX_IDEA = 2000

const inputClass =
  'w-full rounded-lg border border-line bg-black px-3.5 py-2.5 text-sm text-white placeholder:text-neutral-600 outline-none transition focus:border-neutral-500 disabled:opacity-50'

export default function IdeaForm({ onSubmit, disabled }) {
  const [idea, setIdea] = useState('')
  const [industry, setIndustry] = useState('')
  const [targetMarket, setTargetMarket] = useState('')
  const [touched, setTouched] = useState(false)

  const trimmed = idea.trim()
  const ideaError =
    trimmed.length < MIN_IDEA ? `Describe your idea in at least ${MIN_IDEA} characters.` : null

  function handleSubmit(e) {
    e.preventDefault()
    setTouched(true)
    if (ideaError || disabled) return
    onSubmit({
      idea: trimmed,
      industry: industry.trim() || null,
      target_market: targetMarket.trim() || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      <div>
        <label htmlFor="idea" className="mb-1.5 block text-sm text-neutral-300">
          Startup idea
        </label>
        <textarea
          id="idea"
          rows={5}
          maxLength={MAX_IDEA}
          value={idea}
          disabled={disabled}
          onChange={(e) => setIdea(e.target.value)}
          onBlur={() => setTouched(true)}
          placeholder="e.g. An AI receptionist that answers calls and books appointments for small dental clinics"
          className={`${inputClass} resize-y`}
          aria-invalid={touched && !!ideaError}
          aria-describedby="idea-help"
        />
        <div id="idea-help" className="mt-1.5 flex justify-between text-xs">
          <span className={touched && ideaError ? 'text-red-400' : 'text-neutral-500'}>
            {touched && ideaError ? ideaError : 'What are you building, and for whom?'}
          </span>
          <span className="text-neutral-500">
            {idea.length}/{MAX_IDEA}
          </span>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="industry" className="mb-1.5 block text-sm text-neutral-300">
            Industry <span className="text-neutral-600">(optional)</span>
          </label>
          <input
            id="industry"
            maxLength={100}
            value={industry}
            disabled={disabled}
            onChange={(e) => setIndustry(e.target.value)}
            placeholder="Healthcare"
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="target_market" className="mb-1.5 block text-sm text-neutral-300">
            Target market <span className="text-neutral-600">(optional)</span>
          </label>
          <input
            id="target_market"
            maxLength={200}
            value={targetMarket}
            disabled={disabled}
            onChange={(e) => setTargetMarket(e.target.value)}
            placeholder="Independent clinics in the US"
            className={inputClass}
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={disabled}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-medium text-black transition hover:bg-neutral-200 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
      >
        {disabled ? <Loader2 className="size-4 animate-spin" /> : <ArrowRight className="size-4" />}
        {disabled ? 'Agents working…' : 'Analyze idea'}
      </button>
    </form>
  )
}
