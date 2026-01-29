import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Button } from '@/components/ui/button'
import { Check, Copy } from 'lucide-react'
import { useState } from 'react'

interface MarkdownRendererProps {
  content: string
  className?: string
}

function CodeBlock({ language, value }: { language: string; value: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group">
      <Button
        onClick={handleCopy}
        size="sm"
        variant="ghost"
        className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        {copied ? (
          <Check className="h-4 w-4" />
        ) : (
          <Copy className="h-4 w-4" />
        )}
      </Button>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: '0.5rem',
        }}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  )
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={`prose prose-sm dark:prose-invert max-w-none ${className || ''}`}>
      <ReactMarkdown
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '')
            return !inline && match ? (
              <CodeBlock
                language={match[1]}
                value={String(children).replace(/\n$/, '')}
              />
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
