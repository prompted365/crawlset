import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Plus } from 'lucide-react'
import { WebsetList } from '@/components/websets/WebsetList'
import { WebsetForm } from '@/components/websets/WebsetForm'
import { WebsetDetail } from '@/components/websets/WebsetDetail'
import { useWebsets, useWebsetItems, useCreateWebset, useUpdateWebset, useDeleteWebset } from '@/lib/hooks'
import { Webset } from '@/lib/api'
import { toast } from 'sonner'

export function Websets() {
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingWebset, setEditingWebset] = useState<Webset | undefined>()
  const [viewingWebset, setViewingWebset] = useState<Webset | undefined>()

  const { data: websets = [], isLoading } = useWebsets()
  const { data: items = [] } = useWebsetItems(viewingWebset?.id || '')
  const createWebset = useCreateWebset()
  const updateWebset = useUpdateWebset(editingWebset?.id || '')
  const deleteWebset = useDeleteWebset()

  const handleSave = async (data: Partial<Webset>) => {
    try {
      if (editingWebset) {
        await updateWebset.mutateAsync(data)
        toast.success('Webset updated successfully')
      } else {
        await createWebset.mutateAsync(data)
        toast.success('Webset created successfully')
      }
      setIsFormOpen(false)
      setEditingWebset(undefined)
    } catch (error) {
      toast.error('Failed to save webset')
    }
  }

  const handleEdit = (webset: Webset) => {
    setEditingWebset(webset)
    setIsFormOpen(true)
  }

  const handleDelete = async (webset: Webset) => {
    if (confirm(`Are you sure you want to delete "${webset.name}"?`)) {
      try {
        await deleteWebset.mutateAsync(webset.id)
        toast.success('Webset deleted')
      } catch (error) {
        toast.error('Failed to delete webset')
      }
    }
  }

  const handleView = (webset: Webset) => {
    setViewingWebset(webset)
  }

  if (isLoading) {
    return <div className="flex items-center justify-center py-12">Loading...</div>
  }

  if (viewingWebset) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => setViewingWebset(undefined)}>
          Back to Websets
        </Button>
        <WebsetDetail
          webset={viewingWebset}
          items={items}
          onExport={() => console.log('Export webset')}
        />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Websets</h2>
          <p className="text-muted-foreground">
            Manage your web intelligence collections
          </p>
        </div>
        <Button onClick={() => setIsFormOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Webset
        </Button>
      </div>

      <WebsetList
        websets={websets}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onView={handleView}
      />

      <Dialog open={isFormOpen} onOpenChange={(open) => {
        setIsFormOpen(open)
        if (!open) setEditingWebset(undefined)
      }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingWebset ? 'Edit Webset' : 'Create Webset'}
            </DialogTitle>
            <DialogDescription>
              Configure your web intelligence collection
            </DialogDescription>
          </DialogHeader>
          <WebsetForm
            webset={editingWebset}
            onSave={handleSave}
            onCancel={() => {
              setIsFormOpen(false)
              setEditingWebset(undefined)
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
