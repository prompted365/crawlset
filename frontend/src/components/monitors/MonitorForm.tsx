import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { CronBuilder } from '@/components/utility/CronBuilder'
import { JsonEditor } from '@/components/utility/JsonEditor'
import { Monitor, Webset } from '@/lib/api'

interface MonitorFormProps {
  monitor?: Monitor
  websets: Webset[]
  onSave: (data: Partial<Monitor>) => void
  onCancel: () => void
}

const TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Australia/Sydney',
]

export function MonitorForm({ monitor, websets, onSave, onCancel }: MonitorFormProps) {
  const [websetId, setWebsetId] = useState(monitor?.webset_id || '')
  const [cronExpression, setCronExpression] = useState(monitor?.cron_expression || '0 * * * *')
  const [timezone, setTimezone] = useState(monitor?.timezone || 'UTC')
  const [behaviorType, setBehaviorType] = useState<'search' | 'refresh' | 'hybrid'>(
    monitor?.behavior_type || 'search'
  )
  const [behaviorConfig, setBehaviorConfig] = useState(monitor?.behavior_config || {})

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const data: Partial<Monitor> = {
      webset_id: websetId,
      cron_expression: cronExpression,
      timezone,
      behavior_type: behaviorType,
      behavior_config: Object.keys(behaviorConfig).length > 0 ? behaviorConfig : undefined,
      status: monitor?.status || 'enabled',
    }

    onSave(data)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="webset">Webset *</Label>
        <Select value={websetId} onValueChange={setWebsetId} required>
          <SelectTrigger id="webset">
            <SelectValue placeholder="Select a webset..." />
          </SelectTrigger>
          <SelectContent>
            {websets.map((webset) => (
              <SelectItem key={webset.id} value={webset.id}>
                {webset.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Schedule *</Label>
        <CronBuilder value={cronExpression} onChange={setCronExpression} />
      </div>

      <div className="space-y-2">
        <Label htmlFor="timezone">Timezone</Label>
        <Select value={timezone} onValueChange={setTimezone}>
          <SelectTrigger id="timezone">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TIMEZONES.map((tz) => (
              <SelectItem key={tz} value={tz}>
                {tz}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Behavior Type *</Label>
        <RadioGroup value={behaviorType} onValueChange={(v) => setBehaviorType(v as any)}>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="search" id="search" />
            <Label htmlFor="search" className="font-normal cursor-pointer">
              <div>
                <div className="font-medium">Search</div>
                <div className="text-xs text-muted-foreground">
                  Run search query to find new content
                </div>
              </div>
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="refresh" id="refresh" />
            <Label htmlFor="refresh" className="font-normal cursor-pointer">
              <div>
                <div className="font-medium">Refresh</div>
                <div className="text-xs text-muted-foreground">
                  Re-extract existing items to check for updates
                </div>
              </div>
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="hybrid" id="hybrid" />
            <Label htmlFor="hybrid" className="font-normal cursor-pointer">
              <div>
                <div className="font-medium">Hybrid</div>
                <div className="text-xs text-muted-foreground">
                  Both search for new content and refresh existing items
                </div>
              </div>
            </Label>
          </div>
        </RadioGroup>
      </div>

      <div className="space-y-2">
        <Label>Behavior Configuration (JSON)</Label>
        <JsonEditor
          value={behaviorConfig}
          onChange={setBehaviorConfig}
          placeholder='{\n  "max_results": 10,\n  "filters": {...}\n}'
          minHeight="150px"
        />
        <p className="text-xs text-muted-foreground">
          Optional: Additional configuration for the monitor behavior
        </p>
      </div>

      <div className="flex gap-2 justify-end">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">
          {monitor ? 'Update Monitor' : 'Create Monitor'}
        </Button>
      </div>
    </form>
  )
}
