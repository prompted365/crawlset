import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dashboard } from '@/pages/Dashboard'
import { Websets } from '@/pages/Websets'
import { Extraction } from '@/pages/Extraction'
import { Monitors } from '@/pages/Monitors'
import { Search } from '@/pages/Search'
import { Analytics } from '@/pages/Analytics'

type Page = 'dashboard' | 'websets' | 'extraction' | 'monitors' | 'search' | 'analytics'

function App() {
  const [activePage, setActivePage] = useState<Page>('dashboard')

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-foreground">
              Intelligence Pipeline
            </h1>
            <nav className="flex gap-2">
              <Button
                onClick={() => setActivePage('dashboard')}
                variant={activePage === 'dashboard' ? 'default' : 'ghost'}
              >
                Dashboard
              </Button>
              <Button
                onClick={() => setActivePage('websets')}
                variant={activePage === 'websets' ? 'default' : 'ghost'}
              >
                Websets
              </Button>
              <Button
                onClick={() => setActivePage('extraction')}
                variant={activePage === 'extraction' ? 'default' : 'ghost'}
              >
                Extraction
              </Button>
              <Button
                onClick={() => setActivePage('monitors')}
                variant={activePage === 'monitors' ? 'default' : 'ghost'}
              >
                Monitors
              </Button>
              <Button
                onClick={() => setActivePage('search')}
                variant={activePage === 'search' ? 'default' : 'ghost'}
              >
                Search
              </Button>
              <Button
                onClick={() => setActivePage('analytics')}
                variant={activePage === 'analytics' ? 'default' : 'ghost'}
              >
                Analytics
              </Button>
            </nav>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {activePage === 'dashboard' && <Dashboard />}
        {activePage === 'websets' && <Websets />}
        {activePage === 'extraction' && <Extraction />}
        {activePage === 'monitors' && <Monitors />}
        {activePage === 'search' && <Search />}
        {activePage === 'analytics' && <Analytics />}
      </main>
    </div>
  )
}

export default App
