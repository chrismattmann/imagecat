export async function readJson(response) {
  const text = await response.text()
  let body = {}
  if (text) {
    try {
      body = JSON.parse(text)
    } catch (e) {
      body = { error: text }
    }
  }
  if (!response.ok) {
    throw new Error(body.detail || body.error || text || response.statusText)
  }
  return body
}

export function search(q, start, rows, filters) {
  const params = new URLSearchParams()
  params.set('q', q || '*')
  params.set('start', String(start || 0))
  params.set('rows', String(rows || 24))
  ;(filters || []).forEach((item) => {
    const clause = typeof item === 'string' ? item : fieldSearchQuery(item.field, item.value)
    if (clause) {
      params.append('fq', clause)
    }
  })
  return fetch(`/api/search?${params}`).then(readJson)
}

export function getDoc(id) {
  const params = new URLSearchParams()
  params.set('id', id)
  return fetch(`/api/doc?${params}`).then(readJson)
}

export function getHealth() {
  return fetch('/api/health').then(readJson)
}

export function similar(id, n, space) {
  const params = new URLSearchParams()
  params.set('id', id)
  params.set('n', String(n || 24))
  if (space && space !== 'clip') {
    params.set('space', space)
  }
  return fetch(`/api/similar?${params}`).then(readJson)
}

export function refineIqr(positive, negative, n) {
  return fetch('/api/iqr/refine', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      positive: positive || [],
      negative: negative || [],
      n: n || 24
    })
  }).then(readJson)
}

export function fileSrc(id, width) {
  const params = new URLSearchParams()
  params.set('id', id)
  if (width) {
    params.set('w', String(width))
  }
  return `/api/file?${params}`
}

export function scalar(value) {
  if (Array.isArray(value) && value.length) {
    return value[0]
  }
  return value
}

export function fieldEntries(doc) {
  const skip = { highlight: true, _root_: true }
  return Object.keys(doc || {})
    .filter((key) => !skip[key])
    .sort()
    .map((key) => [key, doc[key]])
}

const SKIP_FIELD_SEARCH = {
  highlight: true,
  clip_score: true,
  iqr_score: true,
  meta_score: true,
  jaccard_keys_f: true,
  jaccard_vals_f: true,
  _root_: true,
  _version_: true,
  text: true,
  text_rev: true
}

export function canSearchField(key) {
  return Boolean(key) && !SKIP_FIELD_SEARCH[key] && /^[A-Za-z_][\w.]*$/.test(key)
}

export function valueList(val) {
  if (Array.isArray(val)) {
    return val.filter((item) => item != null && item !== '' && typeof item !== 'object')
  }
  if (val == null || val === '' || typeof val === 'object') {
    return []
  }
  return [val]
}

export function fieldSearchQuery(field, value) {
  if (!canSearchField(field) || value == null || value === '') {
    return ''
  }
  const text = String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"')
  return field + ':"' + text + '"'
}
