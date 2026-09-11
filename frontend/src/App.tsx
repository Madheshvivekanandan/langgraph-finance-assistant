import { BrowserRouter, Route, Routes } from 'react-router'
import { AppShell } from './components/shell/AppShell'
import { OverviewView } from './views/OverviewView'
import { PipelineView } from './views/PipelineView'
import { ReviewView } from './views/ReviewView'
import { StatementsView } from './views/StatementsView'
import { TransactionsView } from './views/TransactionsView'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<OverviewView />} />
          <Route path="transactions" element={<TransactionsView />} />
          <Route path="statements" element={<StatementsView />} />
          <Route path="review" element={<ReviewView />} />
          <Route path="pipeline" element={<PipelineView />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
