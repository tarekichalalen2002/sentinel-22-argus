const CLASS_MAP = {
  pending: 'pill-pending',
  active: 'pill-active',
  enrolled: 'pill-enrolled',
  authorized: 'pill-authorized',
  revoked: 'pill-revoked',
  human: 'pill-human',
  animal: 'pill-animal',
  'unknown object': 'pill-unknown',
  unknown: 'pill-unknown',
}

export default function StatusPill({ status }) {
  const key = String(status || '').toLowerCase()
  return <span className={`pill ${CLASS_MAP[key] || 'pill-pending'}`}>{status}</span>
}
