# Advanced Frontend Components Instructions

## Location
`/Users/breydentaylor/operationTorque/intelligence-pipeline/frontend/src/components/`

## Components to Create

### 1. Webset Management (`websets/`)

**WebsetList.tsx**
- Display all websets in cards/table
- Show stats (item count, last updated)
- Filter and search
- Sort options
- Quick actions (edit, delete, view)

**WebsetForm.tsx**
- Create/edit webset form
- Fields: name, description, search_query, search_criteria (JSON editor), entity_type
- Validation
- Save/cancel actions

**WebsetDetail.tsx**
- Full webset view with tabs:
  - Items (paginated list)
  - Monitors (associated monitors)
  - Analytics (charts and stats)
  - Settings
- Item list with enrichment badges
- Export button

**WebsetItemCard.tsx**
- Display single webset item
- Thumbnail/preview
- Title, URL, excerpt
- Enrichment tags
- Actions (view, re-extract, remove)

### 2. Extraction (`extraction/`)

**ExtractionForm.tsx**
- URL input with validation
- Batch URL textarea
- Extraction options (parse_mode, extract_schema, etc)
- Submit button
- Progress indicator

**ExtractionJobList.tsx**
- Real-time job status updates
- Job cards with status badges
- Cancel/retry buttons
- View results

**ExtractionResult.tsx**
- Display extracted content
- Metadata display
- Citations and links
- Raw JSON toggle
- Save to webset button

### 3. Monitoring (`monitors/`)

**MonitorList.tsx**
- All monitors with status indicators
- Cron expression display
- Next run time
- Enable/disable toggle
- Edit/delete actions

**MonitorForm.tsx**
- Webset selector
- Cron expression builder (visual + text)
- Behavior type selector (search/refresh/hybrid)
- Behavior configuration (JSON editor)
- Timezone selector
- Test cron button

**MonitorRunHistory.tsx**
- Run history table
- Status, duration, items added/updated
- Error messages
- Charts of activity over time

### 4. Search (`search/`)

**SearchBar.tsx**
- Main search input with autocomplete
- Search mode toggle (hybrid/semantic/lexical)
- Filters button
- Voice search (optional)

**SearchResults.tsx**
- Results list with relevance scores
- Highlighting of matched terms
- Faceted filters (webset, date, entity type)
- Sort options
- Export results

**SearchFilters.tsx**
- Date range picker
- Webset selector (multi)
- Entity type checkboxes
- Custom metadata filters

### 5. Analytics (`analytics/`)

**DashboardStats.tsx**
- Enhanced stats cards with trends
- Charts (line, bar, pie)
- Activity heatmap
- Top entities/topics

**WebsetAnalytics.tsx**
- Webset-specific insights
- Growth chart
- Content distribution
- Entity network graph

**TrendingTopics.tsx**
- Trending entities over time
- Topic clusters
- Related searches

### 6. Shared UI (`ui/`)

Add these shadcn/ui components:
- Badge
- Dialog
- Table
- Tabs
- Select
- Textarea
- Label
- Alert
- Progress
- Separator
- Skeleton
- Toast
- Calendar
- Popover
- Command
- Checkbox
- RadioGroup
- Switch
- Accordion

### 7. Utility Components

**JsonEditor.tsx**
- Monaco/CodeMirror for JSON editing
- Validation
- Formatting

**CronBuilder.tsx**
- Visual cron expression builder
- Presets (hourly, daily, weekly)
- Human-readable description

**MarkdownRenderer.tsx**
- Render markdown content
- Syntax highlighting
- Copy code blocks

**StatusBadge.tsx**
- Colored badges for job/monitor status
- Icons
- Tooltips

## State Management
Use React hooks and context:
- WebsetContext for global webset state
- SearchContext for search state
- NotificationContext for toasts

## API Integration
- Use apiClient from lib/api.ts
- Add React Query for caching and real-time updates
- WebSocket for real-time job status (optional)

## Styling
- Tailwind CSS utilities
- shadcn/ui components
- Consistent spacing/colors
- Responsive design (mobile-first)
- Dark mode support
