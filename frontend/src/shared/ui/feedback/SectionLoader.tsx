export function SectionLoader({ label = 'Loading information' }: { label?: string }) {
  return <div className="section-loader" role="status"><span className="section-loader__bar" /><span className="section-loader__bar" /><span className="section-loader__bar section-loader__bar--short" /><span className="sr-only">{label}</span></div>
}
