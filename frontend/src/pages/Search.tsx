import { useState } from 'react'
import { SearchBar, SearchMode } from '@/components/search/SearchBar'
import { SearchResults, SearchResult } from '@/components/search/SearchResults'
import { SearchFilters, SearchFiltersState } from '@/components/search/SearchFilters'
import { useWebsets } from '@/lib/hooks'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'

export function Search() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<SearchMode>('hybrid')
  const [results, setResults] = useState<SearchResult[]>([])
  const [filters, setFilters] = useState<SearchFiltersState>({ websets: [], entityTypes: [] })
  const [showFilters, setShowFilters] = useState(false)

  const { data: websets = [] } = useWebsets()

  const handleSearch = async (searchQuery: string, searchMode: SearchMode) => {
    setQuery(searchQuery)
    setMode(searchMode)

    // TODO: Implement actual search API call
    // For now, this is a placeholder
    console.log('Searching:', { query: searchQuery, mode: searchMode, filters })

    // Mock results
    setResults([])
  }

  const handleApplyFilters = (newFilters: SearchFiltersState) => {
    setFilters(newFilters)
    setShowFilters(false)

    // Re-run search with new filters
    if (query) {
      handleSearch(query, mode)
    }
  }

  const handleClearFilters = () => {
    setFilters({ websets: [], entityTypes: [] })

    // Re-run search without filters
    if (query) {
      handleSearch(query, mode)
    }
  }

  const handleExport = () => {
    // TODO: Implement export functionality
    console.log('Exporting results:', results)
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight mb-2">Search</h2>
        <p className="text-muted-foreground">
          Search across all your websets using AI-powered semantic search
        </p>
      </div>

      <SearchBar
        onSearch={handleSearch}
        onFilterClick={() => setShowFilters(true)}
      />

      {query && (
        <SearchResults
          results={results}
          query={query}
          onExport={handleExport}
        />
      )}

      <Sheet open={showFilters} onOpenChange={setShowFilters}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Search Filters</SheetTitle>
            <SheetDescription>
              Refine your search with advanced filters
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            <SearchFilters
              websets={websets}
              onApply={handleApplyFilters}
              onClear={handleClearFilters}
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
