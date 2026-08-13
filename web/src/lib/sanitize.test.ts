/* Runs in plain Node (node --test), no bundler — proves lib/ is framework-free. */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { safePayload } from './sanitize.ts'

const shape = { defaults: { front: '(missing front)', back: '(missing back)', hint: '' } }

test('valid payload passes through', () => {
  assert.deepEqual(safePayload(shape, { front: 'a', back: 'b', hint: 'c' }), {
    front: 'a',
    back: 'b',
    hint: 'c',
  })
})

test('garbage degrades to defaults, never throws', () => {
  for (const garbage of [null, undefined, 42, 'text', [], { front: 7, back: null }]) {
    const out = safePayload(shape, garbage)
    assert.equal(out.front, '(missing front)')
    assert.equal(out.back, '(missing back)')
  }
})

test('undeclared keys are dropped', () => {
  const out = safePayload(shape, { front: 'a', back: 'b', evil: 'x' })
  assert.equal('evil' in out, false)
})

test('a throwing fix() falls back to defaults', () => {
  const out = safePayload(
    {
      defaults: { n: 1 },
      fix() {
        throw new Error('boom')
      },
    },
    { n: 5 },
  )
  assert.deepEqual(out, { n: 1 })
})

test('mismatched kinds (array vs object) are rejected per-key', () => {
  const arrShape = { defaults: { items: [] as unknown[] } }
  assert.deepEqual(safePayload(arrShape, { items: { not: 'array' } }), { items: [] })
  assert.deepEqual(safePayload(arrShape, { items: [1, 2] }), { items: [1, 2] })
})
