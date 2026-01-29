import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Download, Settings } from 'lucide-react'
import { Webset, WebsetItem } from '@/lib/api'
import { WebsetItemCard } from './WebsetItemCard'

interface WebsetDetailProps {
  webset: Webset
  items: WebsetItem[]
  onExport?: () => void
  onReExtractItem?: (item: WebsetItem) => void
  onRemoveItem?: (item: WebsetItem) => void
}

export function WebsetDetail({
  webset,
  items,
  onExport,
  onReExtractItem,
  onRemoveItem
}: WebsetDetailProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 12

  const totalPages = Math.ceil(items.length / itemsPerPage)
  const paginatedItems = items.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">{webset.name}</h2>
          <p className="text-muted-foreground">
            {items.length} {items.length === 1 ? 'item' : 'items'} in this webset
          </p>
        </div>
        {onExport && (
          <Button onClick={onExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        )}
      </div>

      <Tabs defaultValue="items" className="space-y-4">
        <TabsList>
          <TabsTrigger value="items">Items</TabsTrigger>
          <TabsTrigger value="monitors">Monitors</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="items" className="space-y-4">
          {paginatedItems.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                No items in this webset yet
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {paginatedItems.map((item) => (
                  <WebsetItemCard
                    key={item.id}
                    item={item}
                    onReExtract={onReExtractItem}
                    onRemove={onRemoveItem}
                  />
                ))}
              </div>

              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {currentPage} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </TabsContent>

        <TabsContent value="monitors">
          <Card>
            <CardHeader>
              <CardTitle>Associated Monitors</CardTitle>
              <CardDescription>
                Automated tasks that keep this webset updated
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground text-center py-8">
                No monitors configured for this webset
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics">
          <Card>
            <CardHeader>
              <CardTitle>Analytics</CardTitle>
              <CardDescription>
                Insights and statistics about this webset
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground text-center py-8">
                Analytics coming soon
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle>Webset Settings</CardTitle>
              <CardDescription>
                Configure webset properties and behavior
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <div className="text-sm font-medium">Entity Type</div>
                <div className="text-sm text-muted-foreground">
                  {webset.entity_type || 'Not set'}
                </div>
              </div>

              {webset.search_query && (
                <div className="grid gap-2">
                  <div className="text-sm font-medium">Search Query</div>
                  <div className="text-sm text-muted-foreground">
                    {webset.search_query}
                  </div>
                </div>
              )}

              {webset.search_criteria && (
                <div className="grid gap-2">
                  <div className="text-sm font-medium">Search Criteria</div>
                  <pre className="text-xs bg-muted p-3 rounded overflow-auto">
                    {JSON.stringify(webset.search_criteria, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
