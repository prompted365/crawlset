import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendingUp, Flame } from 'lucide-react'

interface Topic {
  name: string
  count: number
  trend: 'up' | 'down' | 'stable'
  change: number
}

interface TrendData {
  date: string
  [key: string]: number | string
}

interface TrendingTopicsProps {
  topics: Topic[]
  trendData?: TrendData[]
  relatedSearches?: string[]
}

export function TrendingTopics({ topics, trendData = [], relatedSearches = [] }: TrendingTopicsProps) {
  const sortedTopics = [...topics].sort((a, b) => {
    if (a.trend === 'up' && b.trend !== 'up') return -1
    if (a.trend !== 'up' && b.trend === 'up') return 1
    return b.count - a.count
  })

  const getTrendBadge = (trend: 'up' | 'down' | 'stable', change: number) => {
    if (trend === 'up') {
      return (
        <Badge variant="default" className="bg-green-600">
          <TrendingUp className="h-3 w-3 mr-1" />
          +{change}%
        </Badge>
      )
    } else if (trend === 'down') {
      return (
        <Badge variant="destructive">
          <TrendingUp className="h-3 w-3 mr-1 rotate-180" />
          -{change}%
        </Badge>
      )
    } else {
      return (
        <Badge variant="secondary">
          Stable
        </Badge>
      )
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Flame className="h-5 w-5 text-orange-500" />
            Trending Topics
          </CardTitle>
          <CardDescription>
            Most discussed topics and entities across all websets
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sortedTopics.length > 0 ? (
            <div className="space-y-3">
              {sortedTopics.map((topic, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="text-xl font-bold text-muted-foreground w-8">
                      #{index + 1}
                    </div>
                    <div>
                      <div className="font-medium">{topic.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {topic.count} mentions
                      </div>
                    </div>
                  </div>
                  {getTrendBadge(topic.trend, topic.change)}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No trending topics available yet
            </p>
          )}
        </CardContent>
      </Card>

      {trendData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Topic Trends Over Time</CardTitle>
            <CardDescription>Mention frequency of top topics</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                {topics.slice(0, 5).map((topic, index) => (
                  <Line
                    key={topic.name}
                    type="monotone"
                    dataKey={topic.name}
                    stroke={`hsl(${(index * 360) / 5}, 70%, 50%)`}
                    strokeWidth={2}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {relatedSearches.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Related Searches</CardTitle>
            <CardDescription>
              Popular search queries related to trending topics
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {relatedSearches.map((search, index) => (
                <Badge key={index} variant="outline" className="text-sm py-1 px-3">
                  {search}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
