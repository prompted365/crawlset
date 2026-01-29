import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Webset } from '@/lib/api'
import { TrendingUp, FileText, Tag } from 'lucide-react'

interface WebsetAnalyticsProps {
  webset: Webset
  analytics: {
    totalItems: number
    growthData: Array<{ date: string; items: number }>
    topEntities: Array<{ name: string; count: number; type: string }>
    contentTypes: Array<{ type: string; count: number }>
  }
}

export function WebsetAnalytics({ webset, analytics }: WebsetAnalyticsProps) {
  const recentGrowth = analytics.growthData.length > 1
    ? analytics.growthData[analytics.growthData.length - 1].items -
      analytics.growthData[analytics.growthData.length - 2].items
    : 0

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Items</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.totalItems}</div>
            <p className="text-xs text-muted-foreground">
              {webset.entity_type && `Entity type: ${webset.entity_type}`}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recent Growth</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {recentGrowth > 0 ? `+${recentGrowth}` : recentGrowth}
            </div>
            <p className="text-xs text-muted-foreground">Last period</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unique Entities</CardTitle>
            <Tag className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.topEntities.length}</div>
            <p className="text-xs text-muted-foreground">Extracted entities</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Growth Over Time</CardTitle>
          <CardDescription>Number of items added to this webset</CardDescription>
        </CardHeader>
        <CardContent>
          {analytics.growthData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={analytics.growthData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="items" stroke="#8884d8" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-sm text-muted-foreground">
              No growth data available
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top Entities</CardTitle>
            <CardDescription>Most frequently occurring entities</CardDescription>
          </CardHeader>
          <CardContent>
            {analytics.topEntities.length > 0 ? (
              <div className="space-y-3">
                {analytics.topEntities.slice(0, 10).map((entity, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{entity.name}</span>
                      <Badge variant="secondary" className="text-xs">
                        {entity.type}
                      </Badge>
                    </div>
                    <Badge variant="outline">{entity.count}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No entities extracted yet
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Content Types</CardTitle>
            <CardDescription>Distribution of content types</CardDescription>
          </CardHeader>
          <CardContent>
            {analytics.contentTypes.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={analytics.contentTypes}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="type" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No content type data available
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
