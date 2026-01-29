import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, Database, Monitor, TrendingUp, TrendingDown } from 'lucide-react'
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface DashboardStatsProps {
  stats: {
    totalWebsets: number
    totalDocuments: number
    activeMonitors: number
    recentExtractions: number
    trends?: {
      websets: number
      documents: number
      monitors: number
    }
  }
  activityData?: Array<{ date: string; extractions: number; updates: number }>
  websetDistribution?: Array<{ name: string; count: number }>
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8']

export function DashboardStats({ stats, activityData = [], websetDistribution = [] }: DashboardStatsProps) {
  const formatTrend = (value: number) => {
    if (value === 0) return null
    const isPositive = value > 0
    return (
      <div className={`flex items-center text-xs ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
        {isPositive ? <TrendingUp className="h-3 w-3 mr-1" /> : <TrendingDown className="h-3 w-3 mr-1" />}
        {Math.abs(value)}%
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Websets</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalWebsets}</div>
            {stats.trends && formatTrend(stats.trends.websets)}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalDocuments.toLocaleString()}</div>
            {stats.trends && formatTrend(stats.trends.documents)}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Monitors</CardTitle>
            <Monitor className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.activeMonitors}</div>
            {stats.trends && formatTrend(stats.trends.monitors)}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recent Extractions</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.recentExtractions}</div>
            <p className="text-xs text-muted-foreground">Last 24 hours</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Activity Over Time</CardTitle>
            <CardDescription>Extraction and update activity in the last 7 days</CardDescription>
          </CardHeader>
          <CardContent>
            {activityData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={activityData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="extractions" stroke="#0088FE" strokeWidth={2} />
                  <Line type="monotone" dataKey="updates" stroke="#00C49F" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-sm text-muted-foreground">
                No activity data available
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Content Distribution</CardTitle>
            <CardDescription>Documents per webset</CardDescription>
          </CardHeader>
          <CardContent>
            {websetDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={websetDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {websetDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-sm text-muted-foreground">
                No distribution data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
