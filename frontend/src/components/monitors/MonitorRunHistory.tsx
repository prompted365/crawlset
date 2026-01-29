import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { format } from 'date-fns'
import { CheckCircle, XCircle, Clock, TrendingUp } from 'lucide-react'

interface MonitorRun {
  id: string
  monitor_id: string
  status: 'success' | 'failed' | 'running'
  started_at: string
  completed_at?: string
  duration_ms?: number
  items_added: number
  items_updated: number
  error_message?: string
}

interface MonitorRunHistoryProps {
  runs: MonitorRun[]
}

export function MonitorRunHistory({ runs }: MonitorRunHistoryProps) {
  if (runs.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          No run history available
        </CardContent>
      </Card>
    )
  }

  const successfulRuns = runs.filter((r) => r.status === 'success').length
  const failedRuns = runs.filter((r) => r.status === 'failed').length
  const totalItems = runs.reduce((sum, r) => sum + r.items_added + r.items_updated, 0)

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runs.length}</div>
            <p className="text-xs text-muted-foreground">
              {successfulRuns} successful, {failedRuns} failed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Items Processed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalItems}</div>
            <p className="text-xs text-muted-foreground">
              Total items added or updated
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {runs.length > 0 ? Math.round((successfulRuns / runs.length) * 100) : 0}%
            </div>
            <p className="text-xs text-muted-foreground">
              Monitor reliability
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Runs</CardTitle>
          <CardDescription>Monitor execution history</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Items</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((run) => (
                <TableRow key={run.id}>
                  <TableCell>
                    <Badge
                      variant={
                        run.status === 'success'
                          ? 'default'
                          : run.status === 'failed'
                          ? 'destructive'
                          : 'secondary'
                      }
                    >
                      {run.status === 'success' && <CheckCircle className="mr-1 h-3 w-3" />}
                      {run.status === 'failed' && <XCircle className="mr-1 h-3 w-3" />}
                      {run.status === 'running' && <Clock className="mr-1 h-3 w-3" />}
                      {run.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">
                    {format(new Date(run.started_at), 'MMM d, HH:mm')}
                  </TableCell>
                  <TableCell className="text-sm">
                    {run.duration_ms ? `${(run.duration_ms / 1000).toFixed(1)}s` : '-'}
                  </TableCell>
                  <TableCell className="text-sm">
                    {run.items_added > 0 && (
                      <span className="text-green-600">+{run.items_added}</span>
                    )}
                    {run.items_updated > 0 && (
                      <span className="text-blue-600 ml-2">~{run.items_updated}</span>
                    )}
                    {run.items_added === 0 && run.items_updated === 0 && '-'}
                  </TableCell>
                  <TableCell>
                    {run.error_message && (
                      <Alert variant="destructive" className="py-2">
                        <AlertDescription className="text-xs">
                          {run.error_message}
                        </AlertDescription>
                      </Alert>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
