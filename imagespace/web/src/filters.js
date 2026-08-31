import { canSearchField, fieldSearchQuery } from './api.js'

export function looksLikeFieldQuery(q) {
  return /^[A-Za-z_][\w.]*\s*:/.test(String(q || '').trim())
}

export function sameFilter(a, b) {
  return Boolean(a && b && a.field === b.field && String(a.value) === String(b.value))
}

export function addFilter(filters, field, value) {
  const list = Array.isArray(filters) ? filters.slice() : []
  if (!canSearchField(field) || value == null || value === '') {
    return list
  }
  const next = { field: String(field), value: String(value) }
  if (list.some((row) => sameFilter(row, next))) {
    return list
  }
  list.push(next)
  return list
}

export function removeFilter(filters, index) {
  return (filters || []).filter((_, i) => i !== index)
}

export function filterClause(filter) {
  if (!filter) {
    return ''
  }
  return fieldSearchQuery(filter.field, filter.value)
}

export function filterClauses(filters) {
  return (filters || []).map(filterClause).filter(Boolean)
}

export function filterLabel(filter) {
  if (!filter) {
    return ''
  }
  return filter.field + ': "' + filter.value + '"'
}

export function isActiveFilter(filters, field, value) {
  return (filters || []).some((row) => sameFilter(row, { field, value }))
}
