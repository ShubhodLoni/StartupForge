import { createContext, useContext } from 'react'

export const CitationContext = createContext({ ids: new Set(), openSource: null })
export const useCitations = () => useContext(CitationContext)
