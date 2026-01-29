import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Edit, Trash2, Play, Clock } from 'lucide-react'
import { Monitor } from '@/lib/api'
import { format } from 'date-fns'
import cronstrue from 'cronstrue'

interface MonitorListProps {
  monitors: Monitor[]
  onEdit?: (monitor: Monitor) => void
  onDelete?: (monitor: Monitor) => void
  onToggle?: (monitor: Monitor, enabled: boolean) => void
  onTrigger?: (monitor: Monitor) => void
}

export function MonitorList({ monitors, onEdit, onDelete, onToggle, onTrigger }: MonitorListProps) {
  if (monitors.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          No monitors configured yet
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {monitors.map((monitor) => {
        let scheduleDescription = ''
        try {
          scheduleDescription = cronstrue.toString(monitor.cron_expression)
        } catch {
          scheduleDescription = monitor.cron_expression
        }

        return (
          <Card key={monitor.id}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <CardTitle className="text-base flex items-center gap-2">
                    Monitor #{monitor.id.slice(0, 8)}
                    <Badge variant={monitor.status === 'enabled' ? 'default' : 'secondary'}>
                      {monitor.status}
                    </Badge>
                    <Badge variant="outline">{monitor.behavior_type}</Badge>
                  </CardTitle>
                  <CardDescription className="text-xs mt-1">
                    <Clock className="inline h-3 w-3 mr-1" />
                    {scheduleDescription}
                  </CardDescription>
                </div>

                {onToggle && (
                  <Switch
                    checked={monitor.status === 'enabled'}
                    onCheckedChange={(checked) => onToggle(monitor, checked)}
                  />
                )}
              </div>
            </CardHeader>

            <CardContent>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground text-xs">Webset ID</div>
                    <div className="font-mono text-xs">{monitor.webset_id.slice(0, 12)}...</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs">Timezone</div>
                    <div className="text-xs">{monitor.timezone}</div>
                  </div>
                </div>

                {monitor.last_run_at && (
                  <div className="text-xs text-muted-foreground">
                    Last run: {format(new Date(monitor.last_run_at), 'MMM d, yyyy HH:mm')}
                  </div>
                )}

                <div className="flex gap-2">
                  {onTrigger && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onTrigger(monitor)}
                    >
                      <Play className="mr-1 h-3 w-3" />
                      Run Now
                    </Button>
                  )}
                  {onEdit && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onEdit(monitor)}
                    >
                      <Edit className="h-3 w-3" />
                    </Button>
                  )}
                  {onDelete && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onDelete(monitor)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
