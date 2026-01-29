const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface ExtractionJob {
  id: string
  url: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  result?: any
  error?: string
  created_at: string
  completed_at?: string
}

export interface Webset {
  id: string
  name: string
  search_query?: string
  search_criteria?: any
  entity_type?: string
  created_at: string
  updated_at: string
}

export interface WebsetItem {
  id: string
  webset_id: string
  url: string
  title?: string
  content_hash: string
  metadata?: any
  enrichments?: any
  astradb_doc_id?: string
  created_at: string
}

export interface Monitor {
  id: string
  webset_id: string
  cron_expression: string
  timezone: string
  behavior_type: 'search' | 'refresh' | 'hybrid'
  behavior_config?: any
  status: 'enabled' | 'disabled'
  last_run_at?: string
}

class APIClient {
  private baseURL: string

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`)
    }

    return response.json()
  }

  // Extraction Jobs
  async createExtractionJob(url: string): Promise<ExtractionJob> {
    return this.request<ExtractionJob>('/api/extraction/jobs', {
      method: 'POST',
      body: JSON.stringify({ url }),
    })
  }

  async getExtractionJob(jobId: string): Promise<ExtractionJob> {
    return this.request<ExtractionJob>(`/api/extraction/jobs/${jobId}`)
  }

  async listExtractionJobs(): Promise<ExtractionJob[]> {
    return this.request<ExtractionJob[]>('/api/extraction/jobs')
  }

  // Websets
  async createWebset(data: Partial<Webset>): Promise<Webset> {
    return this.request<Webset>('/api/websets', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getWebset(websetId: string): Promise<Webset> {
    return this.request<Webset>(`/api/websets/${websetId}`)
  }

  async listWebsets(): Promise<Webset[]> {
    return this.request<Webset[]>('/api/websets')
  }

  async updateWebset(websetId: string, data: Partial<Webset>): Promise<Webset> {
    return this.request<Webset>(`/api/websets/${websetId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async deleteWebset(websetId: string): Promise<void> {
    return this.request<void>(`/api/websets/${websetId}`, {
      method: 'DELETE',
    })
  }

  // Webset Items
  async getWebsetItems(websetId: string): Promise<WebsetItem[]> {
    return this.request<WebsetItem[]>(`/api/websets/${websetId}/items`)
  }

  // Monitors
  async createMonitor(data: Partial<Monitor>): Promise<Monitor> {
    return this.request<Monitor>('/api/monitors', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getMonitor(monitorId: string): Promise<Monitor> {
    return this.request<Monitor>(`/api/monitors/${monitorId}`)
  }

  async listMonitors(): Promise<Monitor[]> {
    return this.request<Monitor[]>('/api/monitors')
  }

  async updateMonitor(monitorId: string, data: Partial<Monitor>): Promise<Monitor> {
    return this.request<Monitor>(`/api/monitors/${monitorId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async deleteMonitor(monitorId: string): Promise<void> {
    return this.request<void>(`/api/monitors/${monitorId}`, {
      method: 'DELETE',
    })
  }

  async triggerMonitor(monitorId: string): Promise<void> {
    return this.request<void>(`/api/monitors/${monitorId}/trigger`, {
      method: 'POST',
    })
  }
}

export const apiClient = new APIClient()
