import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ExternalLink, RefreshCw, Trash2 } from 'lucide-react'
import { WebsetItem } from '@/lib/api'
import { format } from 'date-fns'

interface WebsetItemCardProps {
  item: WebsetItem
  onReExtract?: (item: WebsetItem) => void
  onRemove?: (item: WebsetItem) => void
}

export function WebsetItemCard({ item, onReExtract, onRemove }: WebsetItemCardProps) {
  const enrichmentKeys = item.enrichments ? Object.keys(item.enrichments) : []

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base truncate">
              {item.title || 'Untitled'}
            </CardTitle>
            <CardDescription className="truncate">
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:underline inline-flex items-center gap-1"
              >
                {item.url}
                <ExternalLink className="h-3 w-3" />
              </a>
            </CardDescription>
          </div>
          <div className="flex gap-1">
            {onReExtract && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onReExtract(item)}
                title="Re-extract content"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            )}
            {onRemove && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onRemove(item)}
                title="Remove from webset"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {enrichmentKeys.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {enrichmentKeys.slice(0, 5).map((key) => (
                <Badge key={key} variant="secondary" className="text-xs">
                  {key}
                </Badge>
              ))}
              {enrichmentKeys.length > 5 && (
                <Badge variant="outline" className="text-xs">
                  +{enrichmentKeys.length - 5} more
                </Badge>
              )}
            </div>
          )}

          {item.metadata?.excerpt && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {item.metadata.excerpt}
            </p>
          )}

          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Added {format(new Date(item.created_at), 'MMM d, yyyy')}</span>
            {item.astradb_doc_id && (
              <Badge variant="outline" className="text-xs">
                Indexed
              </Badge>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
