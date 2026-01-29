import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Search, Filter, X } from 'lucide-react'

interface SearchBarProps {
  onSearch: (query: string, mode: SearchMode) => void
  onFilterClick?: () => void
  defaultMode?: SearchMode
}

export type SearchMode = 'hybrid' | 'semantic' | 'lexical'

export function SearchBar({ onSearch, onFilterClick, defaultMode = 'hybrid' }: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<SearchMode>(defaultMode)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query, mode)
    }
  }

  const handleClear = () => {
    setQuery('')
  }

  const cycleModes = () => {
    const modes: SearchMode[] = ['hybrid', 'semantic', 'lexical']
    const currentIndex = modes.indexOf(mode)
    setMode(modes[(currentIndex + 1) % modes.length])
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search across all websets..."
            className="pl-10 pr-10"
          />
          {query && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleClear}
              className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {onFilterClick && (
          <Button type="button" variant="outline" onClick={onFilterClick}>
            <Filter className="h-4 w-4" />
          </Button>
        )}

        <Button type="submit">Search</Button>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Search mode:</span>
        <Badge
          variant={mode === 'hybrid' ? 'default' : 'outline'}
          className="cursor-pointer"
          onClick={cycleModes}
        >
          {mode === 'hybrid' && 'Hybrid (AI + Keyword)'}
          {mode === 'semantic' && 'Semantic (AI Only)'}
          {mode === 'lexical' && 'Lexical (Keyword Only)'}
        </Badge>
        <span className="text-xs text-muted-foreground">Click to change</span>
      </div>
    </form>
  )
}
