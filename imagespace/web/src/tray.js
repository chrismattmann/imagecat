const KEY = 'imagespace.tray.v1'

export function loadTray() {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(raw) ? raw.filter((row) => row && row.id) : []
  } catch (e) {
    return []
  }
}

export function saveTray(rows) {
  localStorage.setItem(KEY, JSON.stringify(rows))
}

export function inTray(rows, id) {
  return rows.some((row) => row.id === id)
}

export function removeFromTray(rows, id) {
  return rows.filter((row) => row.id !== id)
}

export function toggleTray(rows, doc) {
  if (!doc || !doc.id) {
    return rows
  }
  if (inTray(rows, doc.id)) {
    return removeFromTray(rows, doc.id)
  }
  const next = rows.concat([{ id: doc.id, content_type: doc.content_type }])
  return next
}
