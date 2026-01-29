import { DashboardStats } from '@/components/analytics/DashboardStats'
import { TrendingTopics } from '@/components/analytics/TrendingTopics'

export function Analytics() {
  // Mock data - in production, this would come from API
  const stats = {
    totalWebsets: 0,
    totalDocuments: 0,
    activeMonitors: 0,
    recentExtractions: 0,
    trends: {
      websets: 0,
      documents: 0,
      monitors: 0,
    },
  }

  const activityData = []
  const websetDistribution = []

  const trendingTopics = []
  const trendData = []
  const relatedSearches = []

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Analytics</h2>
        <p className="text-muted-foreground">
          Insights and trends across your intelligence pipeline
        </p>
      </div>

      <DashboardStats
        stats={stats}
        activityData={activityData}
        websetDistribution={websetDistribution}
      />

      <TrendingTopics
        topics={trendingTopics}
        trendData={trendData}
        relatedSearches={relatedSearches}
      />
    </div>
  )
}
