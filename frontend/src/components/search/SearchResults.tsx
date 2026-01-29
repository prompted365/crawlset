import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ExternalLink, Download } from 'lucide-react'
import { WebsetItem } from '@/lib/api'

export interface SearchResult extends WebsetItem {
  score?: number
  highlights?: string[]
}

interface SearchResultsProps {
  results: SearchResult[]
  query: string
  onExport?: () => void
}

type SortOption = 'relevance' | 'date' | 'title'

export function SearchResults({ results, query, onExport }: SearchResultsProps) {
  const [sortBy, setSortBy] = useState<SortOption>('relevance')

  const sortedResults = [...results].sort((a, b) => {
    switch (sortBy) {
      case 'relevance':
        return (b.score || 0) - (a.score || 0)
      case 'date':
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      case 'title':
        return (a.title || '').localeCompare(b.title || '')
      default:
        return 0
    }
  })

  if (results.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground mb-2">No results found for "{query}"</p>
          <p className="text-sm text-muted-foreground">
            Try adjusting your search terms or filters
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Found {results.length} {results.length === 1 ? 'result' : 'results'} for "{query}"
        </p>
        <div className="flex items-center gap-2">
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="relevance">Relevance</SelectItem>
              <SelectItem value="date">Date</SelectItem>
              <SelectItem value="title">Title</SelectItem>
            </SelectContent>
          </Select>
          {onExport && (
            <Button variant="outline" size="sm" onClick={onExport}>
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {sortedResults.map((result) => (
          <Card key={result.id}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <CardTitle className="text-base">
                    {result.title || 'Untitled'}
                  </CardTitle>
                  <CardDescription className="flex items-center gap-2 mt-1">
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline inline-flex items-center gap-1 truncate"
                    >
                      {result.url}
                      <ExternalLink className="h-3 w-3 shrink-0" />
                    </a>
                  </CardDescription>
                </div>
                {result.score !== undefined && (
                  <Badge variant="secondary">
                    {Math.round(result.score * 100)}% match
                  </Badge>
                )}
              </div>
            </CardHeader>

            <CardContent className="space-y-2">
              {result.highlights && result.highlights.length > 0 ? (
                <div className="space-y-1">
                  {result.highlights.map((highlight, idx) => (
                    <p
                      key={idx}
                      className="text-sm text-muted-foreground"
                      dangerouslySetInnerHTML={{ __html: highlight }}
                    />
                  ))}
                </div>
              ) : result.metadata?.excerpt ? (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {result.metadata.excerpt}
                </p>
              ) : null}

              {result.enrichments && Object.keys(result.enrichments).length > 0 && (
                <div className="flex flex-wrap gap-1 pt-2">
                  {Object.keys(result.enrichments)
                    .slice(0, 5)
                    .map((key) => (
                      <Badge key={key} variant="outline" className="text-xs">
                        {key}
                      </Badge>
                    ))}
                  {Object.keys(result.enrichments).length > 5 && (
                    <Badge variant="outline" className="text-xs">
                      +{Object.keys(result.enrichments).length - 5} more
                    </Badge>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
