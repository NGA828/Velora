import { StatusBadge } from '../../../shared/ui/data-display/StatusBadge'
import { displayPercent, displayPercentLabel, scoreDetail, type VitalScore } from './stability'

export function VitalStabilityMeter({
  score,
  size = 'md',
  showDetail = true,
}: {
  score: VitalScore
  size?: 'sm' | 'md' | 'lg'
  showDetail?: boolean
}) {
  const percent = displayPercent(score)
  const tone = score.status === 'CRITICAL' ? 'critical' : score.status === 'STABLE' ? 'stable' : 'unassessed'
  const dimension = size === 'lg' ? 132 : size === 'sm' ? 56 : 88
  const stroke = size === 'sm' ? 6 : 8
  const radius = (dimension - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const progress = percent == null ? 0 : Math.min(100, Math.max(0, percent))
  const dash = (progress / 100) * circumference

  return (
    <div className={`vital-score vital-score--${size} vital-score--${tone}`}>
      <div className="vital-score__meter" style={{ width: dimension, height: dimension }}>
        <svg viewBox={`0 0 ${dimension} ${dimension}`} role="img" aria-label={displayPercentLabel(score)}>
          <circle className="vital-score__track" cx={dimension / 2} cy={dimension / 2} r={radius} strokeWidth={stroke} />
          <circle
            className="vital-score__progress"
            cx={dimension / 2}
            cy={dimension / 2}
            r={radius}
            strokeWidth={stroke}
            strokeDasharray={`${dash} ${circumference}`}
            transform={`rotate(-90 ${dimension / 2} ${dimension / 2})`}
          />
        </svg>
        <strong>{percent == null ? '—' : `${percent}%`}</strong>
      </div>
      <div className="vital-score__copy">
        <div className="vital-score__heading">
          <StatusBadge status={score.status} />
          <span>{displayPercentLabel(score)}</span>
        </div>
        {showDetail && <p>{scoreDetail(score)}</p>}
      </div>
    </div>
  )
}

export function VitalStabilityChip({ score }: { score: VitalScore }) {
  const percent = displayPercent(score)
  const tone = score.status === 'CRITICAL' ? 'critical' : score.status === 'STABLE' ? 'stable' : 'unassessed'
  return (
    <span className={`vital-score-chip vital-score-chip--${tone}`}>
      <StatusBadge status={score.status} />
      <strong>{percent == null ? 'Not scored' : `${percent}%`}</strong>
    </span>
  )
}
