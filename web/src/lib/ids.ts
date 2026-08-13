/* Framework-free (Divergence Rule 2): no React, no fetch, no DOM.
   Unit-testable in plain Node. */

/** Prefixed unique id. crypto.randomUUID is unavailable in non-secure
 *  contexts (plain-HTTP LAN), so fall back to time + randomness. */
export function makeId(prefix = 'id'): string {
  const uuid =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}-${Math.random()
          .toString(36)
          .slice(2, 6)}`
  return `${prefix}_${uuid}`
}
