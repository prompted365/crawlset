import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Plus } from 'lucide-react'
import { MonitorList } from '@/components/monitors/MonitorList'
import { MonitorForm } from '@/components/monitors/MonitorForm'
import { useMonitors, useWebsets, useCreateMonitor, useUpdateMonitor, useDeleteMonitor, useTriggerMonitor } from '@/lib/hooks'
import { Monitor } from '@/lib/api'
import { toast } from 'sonner'

export function Monitors() {
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingMonitor, setEditingMonitor] = useState<Monitor | undefined>()

  const { data: monitors = [], isLoading } = useMonitors()
  const { data: websets = [] } = useWebsets()
  const createMonitor = useCreateMonitor()
  const updateMonitor = useUpdateMonitor(editingMonitor?.id || '')
  const deleteMonitor = useDeleteMonitor()
  const triggerMonitor = useTriggerMonitor()

  const handleSave = async (data: Partial<Monitor>) => {
    try {
      if (editingMonitor) {
        await updateMonitor.mutateAsync(data)
        toast.success('Monitor updated successfully')
      } else {
        await createMonitor.mutateAsync(data)
        toast.success('Monitor created successfully')
      }
      setIsFormOpen(false)
      setEditingMonitor(undefined)
    } catch (error) {
      toast.error('Failed to save monitor')
    }
  }

  const handleEdit = (monitor: Monitor) => {
    setEditingMonitor(monitor)
    setIsFormOpen(true)
  }

  const handleDelete = async (monitor: Monitor) => {
    if (confirm('Are you sure you want to delete this monitor?')) {
      try {
        await deleteMonitor.mutateAsync(monitor.id)
        toast.success('Monitor deleted')
      } catch (error) {
        toast.error('Failed to delete monitor')
      }
    }
  }

  const handleToggle = async (monitor: Monitor, enabled: boolean) => {
    try {
      await updateMonitor.mutateAsync({
        ...monitor,
        status: enabled ? 'enabled' : 'disabled',
      })
      toast.success(`Monitor ${enabled ? 'enabled' : 'disabled'}`)
    } catch (error) {
      toast.error('Failed to toggle monitor')
    }
  }

  const handleTrigger = async (monitor: Monitor) => {
    try {
      await triggerMonitor.mutateAsync(monitor.id)
      toast.success('Monitor triggered successfully')
    } catch (error) {
      toast.error('Failed to trigger monitor')
    }
  }

  if (isLoading) {
    return <div className="flex items-center justify-center py-12">Loading...</div>
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Monitors</h2>
          <p className="text-muted-foreground">
            Automated tasks to keep your websets updated
          </p>
        </div>
        <Button onClick={() => setIsFormOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Monitor
        </Button>
      </div>

      <MonitorList
        monitors={monitors}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onToggle={handleToggle}
        onTrigger={handleTrigger}
      />

      <Dialog open={isFormOpen} onOpenChange={(open) => {
        setIsFormOpen(open)
        if (!open) setEditingMonitor(undefined)
      }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingMonitor ? 'Edit Monitor' : 'Create Monitor'}
            </DialogTitle>
            <DialogDescription>
              Configure an automated task to monitor and update your webset
            </DialogDescription>
          </DialogHeader>
          <MonitorForm
            monitor={editingMonitor}
            websets={websets}
            onSave={handleSave}
            onCancel={() => {
              setIsFormOpen(false)
              setEditingMonitor(undefined)
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
