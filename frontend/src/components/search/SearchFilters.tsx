import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { Calendar } from 'lucide-react'
import { Webset } from '@/lib/api'

export interface SearchFiltersState {
  websets: string[]
  entityTypes: string[]
  dateRange?: {
    from: Date
    to: Date
  }
}

interface SearchFiltersProps {
  websets: Webset[]
  onApply: (filters: SearchFiltersState) => void
  onClear: () => void
}

const ENTITY_TYPES = [
  'person',
  'organization',
  'location',
  'event',
  'product',
  'article',
  'research',
  'general',
]

export function SearchFilters({ websets, onApply, onClear }: SearchFiltersProps) {
  const [selectedWebsets, setSelectedWebsets] = useState<string[]>([])
  const [selectedEntityTypes, setSelectedEntityTypes] = useState<string[]>([])

  const toggleWebset = (websetId: string) => {
    setSelectedWebsets((prev) =>
      prev.includes(websetId)
        ? prev.filter((id) => id !== websetId)
        : [...prev, websetId]
    )
  }

  const toggleEntityType = (entityType: string) => {
    setSelectedEntityTypes((prev) =>
      prev.includes(entityType)
        ? prev.filter((type) => type !== entityType)
        : [...prev, entityType]
    )
  }

  const handleApply = () => {
    onApply({
      websets: selectedWebsets,
      entityTypes: selectedEntityTypes,
    })
  }

  const handleClear = () => {
    setSelectedWebsets([])
    setSelectedEntityTypes([])
    onClear()
  }

  const activeFilterCount = selectedWebsets.length + selectedEntityTypes.length

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Filters</CardTitle>
            <CardDescription>Narrow down your search results</CardDescription>
          </div>
          {activeFilterCount > 0 && (
            <Badge variant="secondary">{activeFilterCount} active</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          <Label className="text-sm font-medium">Websets</Label>
          {websets.length === 0 ? (
            <p className="text-sm text-muted-foreground">No websets available</p>
          ) : (
            <div className="space-y-2">
              {websets.map((webset) => (
                <div key={webset.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={`webset-${webset.id}`}
                    checked={selectedWebsets.includes(webset.id)}
                    onCheckedChange={() => toggleWebset(webset.id)}
                  />
                  <Label
                    htmlFor={`webset-${webset.id}`}
                    className="text-sm font-normal cursor-pointer"
                  >
                    {webset.name}
                  </Label>
                </div>
              ))}
            </div>
          )}
        </div>

        <Separator />

        <div className="space-y-3">
          <Label className="text-sm font-medium">Entity Types</Label>
          <div className="space-y-2">
            {ENTITY_TYPES.map((type) => (
              <div key={type} className="flex items-center space-x-2">
                <Checkbox
                  id={`entity-${type}`}
                  checked={selectedEntityTypes.includes(type)}
                  onCheckedChange={() => toggleEntityType(type)}
                />
                <Label
                  htmlFor={`entity-${type}`}
                  className="text-sm font-normal cursor-pointer capitalize"
                >
                  {type}
                </Label>
              </div>
            ))}
          </div>
        </div>

        <Separator />

        <div className="space-y-3">
          <Label className="text-sm font-medium">Date Range</Label>
          <Button variant="outline" className="w-full justify-start text-left font-normal">
            <Calendar className="mr-2 h-4 w-4" />
            <span>Pick a date range</span>
          </Button>
          <p className="text-xs text-muted-foreground">Date range filtering coming soon</p>
        </div>

        <Separator />

        <div className="flex gap-2">
          <Button onClick={handleApply} className="flex-1">
            Apply Filters
          </Button>
          <Button onClick={handleClear} variant="outline">
            Clear
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
