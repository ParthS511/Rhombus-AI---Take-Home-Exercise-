export const PAGE_SIZE = 25
export const TERMINAL_STATUSES = new Set(['succeeded', 'failed', 'canceled'])

export function statusLabel(status) {
  const labels = {
    pending: 'Queued',
    running: 'Running',
    succeeded: 'Succeeded',
    failed: 'Failed',
    canceled: 'Canceled',
  }
  return labels[status] || 'Idle'
}
