import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { API_BASE, PRODUCT_IMAGES } from '../constants'

function CheckoutModal({ product, quantity, onClose, onConfirm, ordering, taxPreview, confirmed }) {
  const [form, setForm] = useState({
    name: 'Alex Johnson', email: 'alex.johnson@email.com', address: '123 Main St, San Francisco, CA 94105',
    cardNumber: '4242 4242 4242 4242', expiry: '12/27', cvv: '123',
  })

  const set = field => e => setForm(f => ({ ...f, [field]: e.target.value }))

  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        {confirmed ? (
          <div className="modal-confirmation">
            <div className="modal-confirmation-title">Order confirmed</div>
            <div className="modal-confirmation-sub">
              Thank you, {form.name.split(' ')[0]}. Your {product.name} is on its way.
            </div>
            <button className="order-btn" onClick={onClose}>Done</button>
          </div>
        ) : (
          <>
            <div className="modal-header">
              <span className="modal-title">Checkout</span>
              <button className="modal-close" onClick={onClose}>✕</button>
            </div>

            <div className="modal-summary">
              <span>{product.name} × {quantity}</span>
              <span>${(product.price * quantity).toFixed(2)}</span>
            </div>

            {taxPreview && (
              <div className="modal-tax-breakdown">
                <div className="modal-tax-row">
                  <span>Subtotal</span>
                  <span>${taxPreview.subtotal.toFixed(2)}</span>
                </div>
                <div className="modal-tax-row">
                  <span>Tax</span>
                  <span>${taxPreview.taxAmount.toFixed(2)}</span>
                </div>
                <div className="modal-tax-row modal-tax-total">
                  <span>Total</span>
                  <span>${taxPreview.total.toFixed(2)}</span>
                </div>
              </div>
            )}

            <div className="modal-section-label">Contact</div>
            <div className="modal-row">
              <input className="modal-input" placeholder="Full name" value={form.name} onChange={set('name')} />
              <input className="modal-input" placeholder="Email" value={form.email} onChange={set('email')} />
            </div>
            <input className="modal-input modal-input-full" placeholder="Shipping address" value={form.address} onChange={set('address')} />

            <div className="modal-section-label">Payment</div>
            <input className="modal-input modal-input-full" placeholder="Card number" maxLength={19} value={form.cardNumber} onChange={set('cardNumber')} />
            <div className="modal-row">
              <input className="modal-input" placeholder="MM / YY" maxLength={7} value={form.expiry} onChange={set('expiry')} />
              <input className="modal-input" placeholder="CVV" maxLength={4} value={form.cvv} onChange={set('cvv')} />
            </div>
            <div style={{marginTop: '4px'}} />

            <button className="order-btn" onClick={() => onConfirm()} disabled={ordering}>
              {ordering ? 'Processing…' : 'Confirm Order'}
            </button>
          </>
        )}
      </div>
    </div>,
    document.body
  )
}

export default function ProductView({ productId, products, onBack, onOrderSuccess }) {
  const product = products.find(p => p.id === productId)
  const [quantity, setQuantity] = useState(1)
  const [showCheckout, setShowCheckout] = useState(false)
  const [ordering, setOrdering] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [taxPreview, setTaxPreview] = useState(null)
  const [renderError, setRenderError] = useState(null)

  if (renderError) throw renderError

  useEffect(() => {
    if (!showCheckout || !product) return
    setTaxPreview(null)
    fetch(`${API_BASE}/orders/tax-preview?productId=${product.id}&quantity=${quantity}&shippingState=CA`)
      .then(res => {
        if (!res.ok) setRenderError(new Error(`Tax preview failed with status ${res.status}`))
        return res.json()
      })
      .then(data => setTaxPreview(data))
      .catch(err => setRenderError(err))
  }, [showCheckout, product, quantity])

  const handleOrder = async () => {
    setOrdering(true)
    try {
      const res = await fetch(`${API_BASE}/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ productId, quantity, total: taxPreview?.total ?? 0 }),
      })
      if (!res.ok) {
        setRenderError(new Error(`Order failed with status ${res.status}`))
      } else {
        await onOrderSuccess()
        setConfirmed(true)
      }
    } catch (err) {
      setRenderError(err)
    } finally {
      setOrdering(false)
    }
  }

  if (!product) return null

  const { name, price } = product

  return (
    <>
      {showCheckout && (
        <CheckoutModal
          product={product}
          quantity={quantity}
          onClose={() => { setShowCheckout(false); setConfirmed(false) }}
          onConfirm={handleOrder}
          ordering={ordering}
          taxPreview={taxPreview}
          confirmed={confirmed}
        />
      )}
      <div className="product-view">
        <nav className="back-nav">
          <button className="back-btn" onClick={onBack}>← Back</button>
        </nav>

        <div className="product-detail">
          <p className="detail-eyebrow">Personal Electronics</p>
          <h1 className="detail-name">{name}</h1>
          <p className="detail-price">${price.toFixed(2)}</p>
          <div className="detail-media">
            <div className="detail-image">
              <img src={PRODUCT_IMAGES[name]} alt={name} />
            </div>
            <div className="detail-description">
              {product.description && product.description.split('\n\n').filter(Boolean).map((para, i) => (
                <p key={i}>{para}</p>
              ))}
            </div>
          </div>

          <div className="order-form">
            <div>
              <label className="qty-label">Quantity</label>
              <div className="qty-input-group">
                <button
                  className="qty-btn"
                  onClick={() => setQuantity(q => Math.max(1, q - 1))}
                  aria-label="Decrease quantity"
                >
                  −
                </button>
                <input
                  type="number"
                  className="qty-input"
                  value={quantity}
                  min={1}
                  onChange={e => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  aria-label="Quantity"
                />
                <button
                  className="qty-btn"
                  onClick={() => setQuantity(q => q + 1)}
                  aria-label="Increase quantity"
                >
                  +
                </button>
              </div>
            </div>

            <button
              className="order-btn"
              onClick={() => setShowCheckout(true)}
              disabled={ordering}
            >
              Place order
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
