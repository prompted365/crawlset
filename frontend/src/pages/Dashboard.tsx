import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { DashboardStats } from "@/components/analytics/DashboardStats"
import { useWebsets, useMonitors, useExtractionJobs } from "@/lib/hooks"

export function Dashboard() {
  const { data: websets = [] } = useWebsets()
  const { data: monitors = [] } = useMonitors()
  const { data: jobs = [] } = useExtractionJobs()

  const activeMonitors = monitors.filter(m => m.status === 'enabled').length
  const recentJobs = jobs.filter(j => {
    const createdAt = new Date(j.created_at)
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    return createdAt >= yesterday
  }).length

  const stats = {
    totalWebsets: websets.length,
    totalDocuments: 0, // This would come from API
    activeMonitors,
    recentExtractions: recentJobs,
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Monitor your web intelligence pipeline
        </p>
      </div>

      <DashboardStats stats={stats} />

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest extraction jobs and monitor runs
            </CardDescription>
          </CardHeader>
          <CardContent>
            {jobs.length > 0 ? (
              <div className="space-y-2">
                {jobs.slice(0, 5).map((job) => (
                  <div key={job.id} className="text-sm border-b pb-2 last:border-0">
                    <div className="font-medium truncate">{job.url}</div>
                    <div className="text-xs text-muted-foreground">
                      Status: {job.status}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground text-center py-8">
                No recent activity
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common tasks and workflows
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button className="w-full" variant="outline">
              Create New Webset
            </Button>
            <Button className="w-full" variant="outline">
              Extract Content
            </Button>
            <Button className="w-full" variant="outline">
              Configure Monitor
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
