import { useState, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import cronstrue from 'cronstrue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Info } from 'lucide-react'

interface CronBuilderProps {
  value: string
  onChange: (value: string) => void
}

const PRESETS = {
  'Every hour': '0 * * * *',
  'Every day at midnight': '0 0 * * *',
  'Every day at noon': '0 12 * * *',
  'Every Monday at 9am': '0 9 * * 1',
  'Every weekday at 9am': '0 9 * * 1-5',
  'Every Sunday at midnight': '0 0 * * 0',
  'Every 15 minutes': '*/15 * * * *',
  'Every 30 minutes': '*/30 * * * *',
}

export function CronBuilder({ value, onChange }: CronBuilderProps) {
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    try {
      const desc = cronstrue.toString(value)
      setDescription(desc)
      setError(null)
    } catch (e) {
      setError((e as Error).message)
      setDescription('')
    }
  }, [value])

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Preset Schedules</Label>
        <Select onValueChange={onChange}>
          <SelectTrigger>
            <SelectValue placeholder="Select a preset..." />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(PRESETS).map(([label, cron]) => (
              <SelectItem key={cron} value={cron}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Cron Expression</Label>
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="0 * * * *"
          className="font-mono"
        />
        <p className="text-xs text-muted-foreground">
          Format: minute hour day month weekday
        </p>
      </div>

      {description && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <strong>Schedule:</strong> {description}
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
