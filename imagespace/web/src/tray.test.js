import { test } from 'node:test'
import assert from 'node:assert/strict'
import { inTray, removeFromTray, toggleTray } from './tray.js'

test('x on a tray thumb drops that pin and leaves the rest', () => {
  const a = { id: '/data/a.jpg', content_type: 'image/jpeg' }
  const b = { id: '/data/b.jpg', content_type: 'image/jpeg' }
  let rows = []
  rows = toggleTray(rows, a)
  rows = toggleTray(rows, b)
  assert.equal(rows.length, 2)
  rows = removeFromTray(rows, a.id)
  assert.equal(inTray(rows, a.id), false)
  assert.equal(inTray(rows, b.id), true)
  assert.deepEqual(rows, [b])
})
