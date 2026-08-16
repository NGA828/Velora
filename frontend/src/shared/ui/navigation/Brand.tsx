interface BrandProps {
  compact?: boolean
  inverse?: boolean
}

export function Brand({ compact = false, inverse = false }: BrandProps) {
  return (
    <div className={`brand ${inverse ? 'brand--inverse' : ''}`} aria-label="Velora">
      <span className="brand__mark" aria-hidden="true">
        <span className="brand__mark-line brand__mark-line--vertical" />
        <span className="brand__mark-line brand__mark-line--horizontal" />
      </span>
      {!compact && (
        <span className="brand__wordmark">
          Velora
          <small>Hospital workspace</small>
        </span>
      )}
    </div>
  )
}
