import './App.css'
import { ErrorBoundary } from './components/ErrorBoundary'
import { StatementList } from './components/StatementList'
import { StatementUpload } from './components/StatementUpload'
import { TransactionTable } from './components/TransactionTable'
import { useFinanceData } from './hooks/useFinanceData'

function App() {
  const {
    statements,
    transactions,
    categories,
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
        <p className="subtitle">
          Upload a bank statement and see your transactions.
        </p>
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
            <StatementList statements={statements} />
            <TransactionTable
              transactions={transactions}
              categories={categories}
              savingIds={savingIds}
              hasMore={hasMore}
              isLoadingMore={isLoadingMore}
              onLoadMore={() => void loadMore()}
              onCategoryChange={(id, category) => void updateCategory(id, category)}
            />
          </>
        )}
      </ErrorBoundary>
    </main>
  )
}

export default App
