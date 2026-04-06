import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    return (
      <div className="crash-screen">
        <div className="crash-inner">
          <p className="crash-label">Unhandled Exception</p>
          <h1 className="crash-title">Application Error</h1>
          <div className="crash-message">{error.message}</div>
          {error.stack && (
            <pre className="crash-stack">{error.stack}</pre>
          )}
        </div>
      </div>
    )
  }
}
