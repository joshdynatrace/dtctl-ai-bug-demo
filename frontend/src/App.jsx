import { useState, useEffect, useCallback } from 'react'
import './index.css'
import { API_BASE } from './constants'
import ErrorBoundary from './components/ErrorBoundary'
import StoreView from './components/StoreView'
import ProductView from './components/ProductView'

function AppInner() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState('store')
  const [selectedId, setSelectedId] = useState(null)

  const fetchProducts = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/products`)
      const data = await res.json()
      setProducts(data)
    } catch (err) {
      console.error('Failed to fetch products:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchProducts()
  }, [fetchProducts])

  if (view === 'product' && selectedId != null) {
    return (
      <ProductView
        productId={selectedId}
        products={products}
        onBack={() => setView('store')}
        onOrderSuccess={fetchProducts}
      />
    )
  }

  return (
    <StoreView
      products={products}
      loading={loading}
      onSelectProduct={id => { setSelectedId(id); setView('product') }}
    />
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppInner />
    </ErrorBoundary>
  )
}
