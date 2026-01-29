import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ExtractionForm, ExtractionFormData } from '@/components/extraction/ExtractionForm'
import { ExtractionJobList } from '@/components/extraction/ExtractionJobList'
import { ExtractionResult } from '@/components/extraction/ExtractionResult'
import { useExtractionJobs, useCreateExtractionJob, useWebsets } from '@/lib/hooks'
import { ExtractionJob } from '@/lib/api'
import { toast } from 'sonner'

export function Extraction() {
  const [viewingJob, setViewingJob] = useState<ExtractionJob | undefined>()

  const { data: jobs = [] } = useExtractionJobs()
  const { data: websets = [] } = useWebsets()
  const createJob = useCreateExtractionJob()

  const handleSubmit = async (data: ExtractionFormData) => {
    try {
      for (const url of data.urls) {
        await createJob.mutateAsync(url)
      }
      toast.success(`Started ${data.urls.length} extraction ${data.urls.length === 1 ? 'job' : 'jobs'}`)
    } catch (error) {
      toast.error('Failed to start extraction')
    }
  }

  const handleViewResult = (job: ExtractionJob) => {
    setViewingJob(job)
  }

  const handleRetry = async (job: ExtractionJob) => {
    try {
      await createJob.mutateAsync(job.url)
      toast.success('Retry started')
    } catch (error) {
      toast.error('Failed to retry extraction')
    }
  }

  if (viewingJob) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setViewingJob(undefined)}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Back to Extractions
        </button>
        <ExtractionResult
          job={viewingJob}
          websets={websets}
          onSaveToWebset={(websetId) => {
            console.log('Save to webset:', websetId)
            toast.success('Saved to webset')
          }}
        />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Content Extraction</h2>
        <p className="text-muted-foreground">
          Extract and process web content
        </p>
      </div>

      <Tabs defaultValue="extract" className="space-y-4">
        <TabsList>
          <TabsTrigger value="extract">Extract Content</TabsTrigger>
          <TabsTrigger value="jobs">
            Extraction Jobs
            {jobs.length > 0 && (
              <span className="ml-2 rounded-full bg-primary px-2 py-0.5 text-xs text-primary-foreground">
                {jobs.length}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="extract">
          <Card>
            <CardHeader>
              <CardTitle>Extract from URL</CardTitle>
              <CardDescription>
                Extract content from single or multiple URLs
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ExtractionForm onSubmit={handleSubmit} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="jobs">
          <ExtractionJobList
            jobs={jobs}
            onViewResult={handleViewResult}
            onRetry={handleRetry}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
