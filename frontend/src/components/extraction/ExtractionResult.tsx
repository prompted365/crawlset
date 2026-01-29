import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { MarkdownRenderer } from '@/components/utility/MarkdownRenderer'
import { ExternalLink, Save, FileJson } from 'lucide-react'
import { ExtractionJob, Webset } from '@/lib/api'

interface ExtractionResultProps {
  job: ExtractionJob
  websets?: Webset[]
  onSaveToWebset?: (websetId: string) => void
}

export function ExtractionResult({ job, websets = [], onSaveToWebset }: ExtractionResultProps) {
  const [selectedWebset, setSelectedWebset] = useState('')
  const [showRawJson, setShowRawJson] = useState(false)

  if (!job.result) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          No result available
        </CardContent>
      </Card>
    )
  }

  const result = job.result

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <CardTitle className="text-lg">
                {result.title || 'Extracted Content'}
              </CardTitle>
              <CardDescription className="flex items-center gap-1 truncate">
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline inline-flex items-center gap-1"
                >
                  {job.url}
                  <ExternalLink className="h-3 w-3" />
                </a>
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {result.metadata && (
            <div className="flex flex-wrap gap-2">
              {result.metadata.author && (
                <Badge variant="outline">By {result.metadata.author}</Badge>
              )}
              {result.metadata.date && (
                <Badge variant="outline">{result.metadata.date}</Badge>
              )}
              {result.metadata.tags?.map((tag: string) => (
                <Badge key={tag} variant="secondary">{tag}</Badge>
              ))}
            </div>
          )}

          <Tabs defaultValue="content" className="space-y-4">
            <TabsList>
              <TabsTrigger value="content">Content</TabsTrigger>
              <TabsTrigger value="metadata">Metadata</TabsTrigger>
              <TabsTrigger value="citations">Citations</TabsTrigger>
            </TabsList>

            <TabsContent value="content" className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Extracted Content</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowRawJson(!showRawJson)}
                >
                  <FileJson className="mr-1 h-3 w-3" />
                  {showRawJson ? 'Show Formatted' : 'Show Raw JSON'}
                </Button>
              </div>

              {showRawJson ? (
                <pre className="bg-muted p-4 rounded-lg overflow-auto text-xs">
                  {JSON.stringify(result, null, 2)}
                </pre>
              ) : (
                <div className="border rounded-lg p-6 bg-background">
                  {result.content_markdown ? (
                    <MarkdownRenderer content={result.content_markdown} />
                  ) : result.content ? (
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      {result.content}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">No content available</p>
                  )}
                </div>
              )}
            </TabsContent>

            <TabsContent value="metadata">
              <div className="border rounded-lg p-4 bg-muted/50">
                <pre className="text-xs overflow-auto">
                  {JSON.stringify(result.metadata || {}, null, 2)}
                </pre>
              </div>
            </TabsContent>

            <TabsContent value="citations">
              <div className="space-y-2">
                {result.citations && result.citations.length > 0 ? (
                  result.citations.map((citation: any, index: number) => (
                    <Card key={index}>
                      <CardContent className="pt-4">
                        <p className="text-sm">{citation.text || citation}</p>
                        {citation.url && (
                          <a
                            href={citation.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-muted-foreground hover:underline inline-flex items-center gap-1 mt-1"
                          >
                            {citation.url}
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </CardContent>
                    </Card>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No citations found
                  </p>
                )}
              </div>
            </TabsContent>
          </Tabs>

          {websets.length > 0 && onSaveToWebset && (
            <div className="flex items-end gap-2 pt-4 border-t">
              <div className="flex-1 space-y-2">
                <Label htmlFor="webset-select">Save to Webset</Label>
                <Select value={selectedWebset} onValueChange={setSelectedWebset}>
                  <SelectTrigger id="webset-select">
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
              <Button
                onClick={() => selectedWebset && onSaveToWebset(selectedWebset)}
                disabled={!selectedWebset}
              >
                <Save className="mr-2 h-4 w-4" />
                Save
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
