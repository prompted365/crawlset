import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ExternalLink, Eye, XCircle, RotateCw } from 'lucide-react'
import { StatusBadge } from '@/components/utility/StatusBadge'
import { ExtractionJob } from '@/lib/api'
import { format } from 'date-fns'

interface ExtractionJobListProps {
  jobs: ExtractionJob[]
  onViewResult?: (job: ExtractionJob) => void
  onCancel?: (job: ExtractionJob) => void
  onRetry?: (job: ExtractionJob) => void
}

export function ExtractionJobList({ jobs, onViewResult, onCancel, onRetry }: ExtractionJobListProps) {
  if (jobs.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          No extraction jobs yet
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {jobs.map((job) => (
        <Card key={job.id}>
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <CardTitle className="text-base truncate flex items-center gap-2">
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline inline-flex items-center gap-1 truncate"
                  >
                    {job.url}
                    <ExternalLink className="h-3 w-3 shrink-0" />
                  </a>
                </CardTitle>
                <CardDescription className="text-xs">
                  Started {format(new Date(job.created_at), 'MMM d, yyyy HH:mm')}
                  {job.completed_at && (
                    <> • Completed {format(new Date(job.completed_at), 'HH:mm')}</>
                  )}
                </CardDescription>
              </div>
              <StatusBadge status={job.status} />
            </div>
          </CardHeader>

          {(job.error || job.status === 'completed') && (
            <CardContent>
              {job.error && (
                <div className="text-sm text-destructive mb-3">
                  Error: {job.error}
                </div>
              )}

              <div className="flex gap-2">
                {job.status === 'completed' && onViewResult && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onViewResult(job)}
                  >
                    <Eye className="mr-1 h-3 w-3" />
                    View Result
                  </Button>
                )}

                {job.status === 'failed' && onRetry && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onRetry(job)}
                  >
                    <RotateCw className="mr-1 h-3 w-3" />
                    Retry
                  </Button>
                )}

                {(job.status === 'pending' || job.status === 'processing') && onCancel && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onCancel(job)}
                  >
                    <XCircle className="mr-1 h-3 w-3" />
                    Cancel
                  </Button>
                )}
              </div>
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  )
}
