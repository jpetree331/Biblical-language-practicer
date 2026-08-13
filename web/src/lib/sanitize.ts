/* Framework-free (Divergence Rule 2): no React, no fetch, no DOM.
   Unit-testable in plain Node.

   Defensive-load sanitizer: every payload read from the DB passes through
   safePayload before any component touches it. A hand-corrupted row must
   degrade to defaults, never crash the app. */

export type PayloadShape<T extends Record<string, unknown>> = {
  defaults: T
  /** Optional refiner for cross-field invariants (e.g. cloze ranges).
   *  Runs after structural coercion; if it throws, defaults win. */
  fix?: (payload: T) => T
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function sameKind(a: unknown, b: unknown): boolean {
  if (Array.isArray(a) !== Array.isArray(b)) return false
  if (a === null || b === null) return a === b
  return typeof a === typeof b
}

/** Coerce unknown data to the shape of `defaults`: keep declared keys whose
 *  runtime kind matches the default's kind, fill everything else from
 *  defaults, drop undeclared keys. */
export function safePayload<T extends Record<string, unknown>>(
  shape: PayloadShape<T>,
  raw: unknown,
): T {
  const out = clone(shape.defaults)
  if (raw !== null && typeof raw === 'object' && !Array.isArray(raw)) {
    const source = raw as Record<string, unknown>
    for (const key of Object.keys(shape.defaults)) {
      if (key in source && sameKind(source[key], shape.defaults[key])) {
        ;(out as Record<string, unknown>)[key] = clone(source[key])
      }
    }
  }
  if (shape.fix) {
    try {
      return shape.fix(out)
    } catch {
      return clone(shape.defaults)
    }
  }
  return out
}
