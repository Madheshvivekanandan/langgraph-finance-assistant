import { TransactionTable } from '../components/TransactionTable'
import { useFinanceDataContext } from '../hooks/useFinanceDataContext'

export function TransactionsView() {
  const {
    transactions,
    categories,
    savingIds,
    hasMore,
    isLoadingMore,
    loadMore,
    updateCategory,
  } = useFinanceDataContext()

  return (
    <div data-view="transactions">
      <TransactionTable
        transactions={transactions}
        categories={categories}
        savingIds={savingIds}
        hasMore={hasMore}
        isLoadingMore={isLoadingMore}
        onLoadMore={() => void loadMore()}
        onCategoryChange={(id, category) => void updateCategory(id, category)}
      />
    </div>
  )
}
