import React from 'react'

function LoadingSpinner({ size = 'md', message = '' }) {
  const sizes = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-4',
    lg: 'w-12 h-12 border-4',
  }

  return (
    <div className="flex flex-col items-center justify-center gap-3" role="status" aria-label="Loading">
      <div
        className={`${sizes[size] || sizes.md} border-primary-500 border-t-transparent rounded-full animate-spin`}
      />
      {message && <p className="text-sm text-gray-500">{message}</p>}
    </div>
  )
}

export default LoadingSpinner
