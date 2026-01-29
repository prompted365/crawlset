import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, Webset, WebsetItem, Monitor, ExtractionJob } from './api'

// Websets
export function useWebsets() {
  return useQuery({
    queryKey: ['websets'],
    queryFn: () => apiClient.listWebsets(),
  })
}

export function useWebset(websetId: string) {
  return useQuery({
    queryKey: ['websets', websetId],
    queryFn: () => apiClient.getWebset(websetId),
    enabled: !!websetId,
  })
}

export function useWebsetItems(websetId: string) {
  return useQuery({
    queryKey: ['websets', websetId, 'items'],
    queryFn: () => apiClient.getWebsetItems(websetId),
    enabled: !!websetId,
  })
}

export function useCreateWebset() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Webset>) => apiClient.createWebset(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['websets'] })
    },
  })
}

export function useUpdateWebset(websetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Webset>) => apiClient.updateWebset(websetId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['websets'] })
      queryClient.invalidateQueries({ queryKey: ['websets', websetId] })
    },
  })
}

export function useDeleteWebset() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (websetId: string) => apiClient.deleteWebset(websetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['websets'] })
    },
  })
}

// Monitors
export function useMonitors() {
  return useQuery({
    queryKey: ['monitors'],
    queryFn: () => apiClient.listMonitors(),
  })
}

export function useMonitor(monitorId: string) {
  return useQuery({
    queryKey: ['monitors', monitorId],
    queryFn: () => apiClient.getMonitor(monitorId),
    enabled: !!monitorId,
  })
}

export function useCreateMonitor() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Monitor>) => apiClient.createMonitor(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] })
    },
  })
}

export function useUpdateMonitor(monitorId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Monitor>) => apiClient.updateMonitor(monitorId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] })
      queryClient.invalidateQueries({ queryKey: ['monitors', monitorId] })
    },
  })
}

export function useDeleteMonitor() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (monitorId: string) => apiClient.deleteMonitor(monitorId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] })
    },
  })
}

export function useTriggerMonitor() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (monitorId: string) => apiClient.triggerMonitor(monitorId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] })
    },
  })
}

// Extraction Jobs
export function useExtractionJobs() {
  return useQuery({
    queryKey: ['extraction-jobs'],
    queryFn: () => apiClient.listExtractionJobs(),
    refetchInterval: 5000, // Poll every 5 seconds for real-time updates
  })
}

export function useExtractionJob(jobId: string) {
  return useQuery({
    queryKey: ['extraction-jobs', jobId],
    queryFn: () => apiClient.getExtractionJob(jobId),
    enabled: !!jobId,
    refetchInterval: (data) => {
      // Stop polling when job is completed or failed
      return data && (data.status === 'completed' || data.status === 'failed') ? false : 2000
    },
  })
}

export function useCreateExtractionJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (url: string) => apiClient.createExtractionJob(url),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['extraction-jobs'] })
    },
  })
}
