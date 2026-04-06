import { PRODUCT_IMAGES } from '../constants'

function ProductCard({ product, onClick }) {
  const { name, price } = product

  return (
    <div className="product-card" onClick={onClick} role="button" tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onClick()}>
      <div className="card-inner">
        <div className="card-top">
        </div>
        <div className="card-image">
          <img src={PRODUCT_IMAGES[name]} alt={name} />
        </div>
        <div className="card-body">
          <h2 className="card-name">{name}</h2>
        </div>
        <div className="card-footer">
          <span className="card-price">${price.toFixed(2)}</span>
          <span className="card-cta">View →</span>
        </div>
      </div>
    </div>
  )
}

export default function StoreView({ products, loading, onSelectProduct }) {
  return (
    <div className="store-view">
      <header className="header">
        <div className="header-inner">
          <div className="logo-block">
            <h1 className="logo">ARC</h1>
            <span className="logo-sub">Store</span>
          </div>
          <div className="header-meta">Peripherals · SS 2026</div>
        </div>
      </header>

      <main className="products-section">
        <div className="section-header">
          <span className="section-label">Collection</span>
          <span className="product-count">
            {loading ? '—' : `${products.length} Peripherals`}
          </span>
        </div>

        <div className="product-grid">
          {loading ? (
            <div className="loading">Loading</div>
          ) : (
            products.map(product => (
              <ProductCard
                key={product.id}
                product={product}
                onClick={() => onSelectProduct(product.id)}
              />
            ))
          )}
        </div>
      </main>

      <footer className="footer">Arc © 2026</footer>
    </div>
  )
}
