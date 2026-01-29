import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { JsonEditor } from '@/components/utility/JsonEditor'
import { Webset } from '@/lib/api'

interface WebsetFormProps {
  webset?: Webset
  onSave: (data: Partial<Webset>) => void
  onCancel: () => void
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

export function WebsetForm({ webset, onSave, onCancel }: WebsetFormProps) {
  const [name, setName] = useState(webset?.name || '')
  const [description, setDescription] = useState('')
  const [searchQuery, setSearchQuery] = useState(webset?.search_query || '')
  const [searchCriteria, setSearchCriteria] = useState(webset?.search_criteria || {})
  const [entityType, setEntityType] = useState(webset?.entity_type || '')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const data: Partial<Webset> = {
      name,
      search_query: searchQuery || undefined,
      search_criteria: Object.keys(searchCriteria).length > 0 ? searchCriteria : undefined,
      entity_type: entityType || undefined,
    }

    onSave(data)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="name">Name *</Label>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My Research Webset"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="A collection of research articles and papers on..."
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="entity-type">Entity Type</Label>
        <Select value={entityType} onValueChange={setEntityType}>
          <SelectTrigger id="entity-type">
            <SelectValue placeholder="Select entity type..." />
          </SelectTrigger>
          <SelectContent>
            {ENTITY_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="search-query">Search Query</Label>
        <Input
          id="search-query"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="machine learning research"
        />
        <p className="text-xs text-muted-foreground">
          Optional: Query to automatically find and add content to this webset
        </p>
      </div>

      <div className="space-y-2">
        <Label>Search Criteria (JSON)</Label>
        <JsonEditor
          value={searchCriteria}
          onChange={setSearchCriteria}
          placeholder='{\n  "domains": ["arxiv.org"],\n  "keywords": ["neural", "networks"]\n}'
        />
        <p className="text-xs text-muted-foreground">
          Optional: Advanced search criteria for automatic content discovery
        </p>
      </div>

      <div className="flex gap-2 justify-end">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">
          {webset ? 'Update Webset' : 'Create Webset'}
        </Button>
      </div>
    </form>
  )
}
