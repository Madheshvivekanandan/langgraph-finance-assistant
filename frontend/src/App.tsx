import './App.css'
import { ChatPanel } from './components/ChatPanel'
import { Dashboard } from './components/Dashboard'
import { ErrorBoundary } from './components/ErrorBoundary'
import { StatementList } from './components/StatementList'
import { StatementUpload } from './components/StatementUpload'
import { TransactionTable } from './components/TransactionTable'
import { useFinanceData } from './hooks/useFinanceData'

function App() {
  const {
    statements,
    categories,
    months,
    categorySummary,
    transactions,
    selectedMonth,
    setSelectedMonth,
    selectedCategory,
    setSelectedCategory,
    savingIds,
    updateCategory,
    status,
    errorMessage,
    hasMore,
    isLoadingMore,
    loadMore,
    reload,
  } = useFinanceData()

  return (
    <main className="app">
      <header>
        <h1>My Finance</h1>
        <p className="subtitle">Where your money went, and what you can ask about it.</p>
      </header>

      <ErrorBoundary>
        <StatementUpload onUploaded={() => void reload()} />

        {status === 'loading' && <p className="message">Loading…</p>}

        {status === 'error' && (
          <p className="message message-error" role="alert">
            {errorMessage}
          </p>
        )}

        {status === 'ready' && (
          <>
            <Dashboard
              months={months}
              categorySummary={categorySummary}
              categories={categories}
              selectedMonth={selectedMonth}
              onMonthChange={setSelectedMonth}
              selectedCategory={selectedCategory}
              onCategoryChange={setSelectedCategory}
            />
            <TransactionTable
              transactions={transactions}
              categories={categories}
              savingIds={savingIds}
              hasMore={hasMore}
              isLoadingMore={isLoadingMore}
              onLoadMore={() => void loadMore()}
              onCategoryChange={(id, category) => void updateCategory(id, category)}
            />
            <StatementList statements={statements} />
          </>
        )}
      </ErrorBoundary>

      <ErrorBoundary>
        <ChatPanel />
      </ErrorBoundary>
    </main>
  )
}

export default App
