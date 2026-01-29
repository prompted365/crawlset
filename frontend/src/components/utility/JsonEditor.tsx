import { useState } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface JsonEditorProps {
  value: any
  onChange: (value: any) => void
  placeholder?: string
  minHeight?: string
}

export function JsonEditor({ value, onChange, placeholder = '{}', minHeight = '200px' }: JsonEditorProps) {
  const [text, setText] = useState(JSON.stringify(value, null, 2))
  const [error, setError] = useState<string | null>(null)
  const [isValid, setIsValid] = useState(true)

  const handleChange = (newText: string) => {
    setText(newText)

    try {
      const parsed = JSON.parse(newText)
      setError(null)
      setIsValid(true)
      onChange(parsed)
    } catch (e) {
      setError((e as Error).message)
      setIsValid(false)
    }
  }

  const formatJson = () => {
    try {
      const parsed = JSON.parse(text)
      const formatted = JSON.stringify(parsed, null, 2)
      setText(formatted)
      setError(null)
      setIsValid(true)
      onChange(parsed)
    } catch (e) {
      setError((e as Error).message)
      setIsValid(false)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isValid ? (
            <Check className="h-4 w-4 text-green-500" />
          ) : (
            <AlertCircle className="h-4 w-4 text-red-500" />
          )}
          <span className="text-sm text-muted-foreground">
            {isValid ? 'Valid JSON' : 'Invalid JSON'}
          </span>
        </div>
        <Button onClick={formatJson} variant="ghost" size="sm">
          Format
        </Button>
      </div>

      <Textarea
        value={text}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={placeholder}
        className="font-mono text-sm"
        style={{ minHeight }}
      />

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
