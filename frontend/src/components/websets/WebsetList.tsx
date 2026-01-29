import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Edit, Trash2, Eye, Search } from 'lucide-react'
import { Webset } from '@/lib/api'
import { format } from 'date-fns'

interface WebsetListProps {
  websets: Webset[]
  onEdit?: (webset: Webset) => void
  onDelete?: (webset: Webset) => void
  onView?: (webset: Webset) => void
}

type SortOption = 'name' | 'created' | 'updated'

export function WebsetList({ websets, onEdit, onDelete, onView }: WebsetListProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('updated')

  const filteredWebsets = websets
    .filter((webset) =>
      webset.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      webset.search_query?.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name)
        case 'created':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'updated':
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        default:
          return 0
      }
    })

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search websets..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8"
          />
        </div>
        <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortOption)}>
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="updated">Last Updated</SelectItem>
            <SelectItem value="created">Date Created</SelectItem>
            <SelectItem value="name">Name</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {filteredWebsets.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {searchTerm ? 'No websets match your search' : 'No websets created yet'}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredWebsets.map((webset) => (
            <Card key={webset.id} className="flex flex-col">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-base truncate">{webset.name}</CardTitle>
                    <CardDescription className="text-xs">
                      Updated {format(new Date(webset.updated_at), 'MMM d, yyyy')}
                    </CardDescription>
                  </div>
                  {webset.entity_type && (
                    <Badge variant="secondary" className="text-xs shrink-0">
                      {webset.entity_type}
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col justify-between gap-3">
                {webset.search_query && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    Query: {webset.search_query}
                  </p>
                )}

                <div className="flex gap-1">
                  {onView && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onView(webset)}
                      className="flex-1"
                    >
                      <Eye className="mr-1 h-3 w-3" />
                      View
                    </Button>
                  )}
                  {onEdit && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onEdit(webset)}
                    >
                      <Edit className="h-3 w-3" />
                    </Button>
                  )}
                  {onDelete && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onDelete(webset)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
