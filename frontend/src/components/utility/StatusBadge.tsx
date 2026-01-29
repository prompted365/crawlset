import { Badge } from "@/components/ui/badge"
import { CheckCircle, Clock, XCircle, AlertCircle, Loader2 } from "lucide-react"

interface StatusBadgeProps {
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'enabled' | 'disabled'
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = {
    pending: {
      variant: 'secondary' as const,
      icon: Clock,
      label: 'Pending'
    },
    processing: {
      variant: 'default' as const,
      icon: Loader2,
      label: 'Processing',
      animate: true
    },
    completed: {
      variant: 'default' as const,
      icon: CheckCircle,
      label: 'Completed'
    },
    failed: {
      variant: 'destructive' as const,
      icon: XCircle,
      label: 'Failed'
    },
    enabled: {
      variant: 'default' as const,
      icon: CheckCircle,
      label: 'Enabled'
    },
    disabled: {
      variant: 'secondary' as const,
      icon: AlertCircle,
      label: 'Disabled'
    }
  }

  const { variant, icon: Icon, label, animate } = config[status]

  return (
    <Badge variant={variant} className={className}>
      <Icon className={`mr-1 h-3 w-3 ${animate ? 'animate-spin' : ''}`} />
      {label}
    </Badge>
  )
}
