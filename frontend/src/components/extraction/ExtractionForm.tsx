import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { JsonEditor } from '@/components/utility/JsonEditor'
import { Loader2 } from 'lucide-react'

interface ExtractionFormProps {
  onSubmit: (data: ExtractionFormData) => Promise<void>
}

export interface ExtractionFormData {
  urls: string[]
  parse_mode?: string
  extract_schema?: any
  options?: any
}

export function ExtractionForm({ onSubmit }: ExtractionFormProps) {
  const [singleUrl, setSingleUrl] = useState('')
  const [batchUrls, setBatchUrls] = useState('')
  const [parseMode, setParseMode] = useState('markdown')
  const [extractSchema, setExtractSchema] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      const urls = singleUrl
        ? [singleUrl]
        : batchUrls.split('\n').filter((url) => url.trim())

      await onSubmit({
        urls,
        parse_mode: parseMode,
        extract_schema: Object.keys(extractSchema).length > 0 ? extractSchema : undefined,
      })

      // Reset form
      setSingleUrl('')
      setBatchUrls('')
      setExtractSchema({})
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Tabs defaultValue="single">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="single">Single URL</TabsTrigger>
          <TabsTrigger value="batch">Batch URLs</TabsTrigger>
        </TabsList>

        <TabsContent value="single" className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="url">URL to Extract</Label>
            <Input
              id="url"
              type="url"
              value={singleUrl}
              onChange={(e) => setSingleUrl(e.target.value)}
              placeholder="https://example.com/article"
              required={!batchUrls}
            />
          </div>
        </TabsContent>

        <TabsContent value="batch" className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="batch-urls">URLs (one per line)</Label>
            <Textarea
              id="batch-urls"
              value={batchUrls}
              onChange={(e) => setBatchUrls(e.target.value)}
              placeholder="https://example.com/article1&#10;https://example.com/article2&#10;https://example.com/article3"
              rows={8}
              required={!singleUrl}
            />
            <p className="text-xs text-muted-foreground">
              Enter one URL per line for batch extraction
            </p>
          </div>
        </TabsContent>
      </Tabs>

      <div className="space-y-2">
        <Label htmlFor="parse-mode">Parse Mode</Label>
        <Select value={parseMode} onValueChange={setParseMode}>
          <SelectTrigger id="parse-mode">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="markdown">Markdown</SelectItem>
            <SelectItem value="html">HTML</SelectItem>
            <SelectItem value="text">Plain Text</SelectItem>
            <SelectItem value="structured">Structured Data</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Extraction Schema (Optional)</Label>
        <JsonEditor
          value={extractSchema}
          onChange={setExtractSchema}
          placeholder='{\n  "title": "string",\n  "author": "string",\n  "date": "string"\n}'
          minHeight="150px"
        />
        <p className="text-xs text-muted-foreground">
          Define a JSON schema to extract specific fields from the content
        </p>
      </div>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Extracting...
          </>
        ) : (
          'Extract Content'
        )}
      </Button>
    </form>
  )
}
