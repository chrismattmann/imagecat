import { test } from 'node:test'
import assert from 'node:assert/strict'
import { addFilter, filterClauses, filterLabel, isActiveFilter, looksLikeFieldQuery, removeFilter } from './filters.js'

test('clicking an EXIF value stacks a chip and skips duplicates', () => {
  let filters = []
  filters = addFilter(filters, 'Exif_IFD0_Artist', 'Matteo Chinellato')
  filters = addFilter(filters, 'tiff_Make', 'Canon')
  filters = addFilter(filters, 'Exif_IFD0_Artist', 'Matteo Chinellato')
  assert.equal(filters.length, 2)
  assert.deepEqual(filterClauses(filters), [
    'Exif_IFD0_Artist:"Matteo Chinellato"',
    'tiff_Make:"Canon"'
  ])
  assert.equal(filterLabel(filters[0]), 'Exif_IFD0_Artist: "Matteo Chinellato"')
  assert.equal(isActiveFilter(filters, 'tiff_Make', 'Canon'), true)
})

test('x removes one chip and leaves the rest', () => {
  const filters = removeFilter([
    { field: 'tiff_Make', value: 'Canon' },
    { field: 'tiff_Model', value: 'EOS' }
  ], 0)
  assert.deepEqual(filters, [{ field: 'tiff_Model', value: 'EOS' }])
})

test('a field:"value" in the search box is a field query; OCR text is not', () => {
  assert.equal(looksLikeFieldQuery('Exif_IFD0_Artist:"Matteo Chinellato"'), true)
  assert.equal(looksLikeFieldQuery('Elisa'), false)
  assert.equal(looksLikeFieldQuery('*'), false)
})
