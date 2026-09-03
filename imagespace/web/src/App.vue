<template>
  <div class="shell">
    <aside class="tray">
      <h2>
        <img class="tray-mark" src="/mark.png" width="22" height="22" alt=""/>
        Saved
      </h2>
      <p v-if="!tray.length" class="empty">Save an image from the grid to pin it here.</p>
      <div v-for="row in tray" :key="row.id" class="tray-item" :class="{ active: open && open.id === row.id }">
        <button type="button" class="tray-thumb" :title="basename(row.id)" @click="openDoc(row.id)">
          <img :src="fileSrc(row.id, 180)" :alt="basename(row.id)" loading="lazy" decoding="async"/>
        </button>
        <button type="button" class="tray-remove" title="Remove from tray" :aria-label="'Remove ' + basename(row.id) + ' from tray'" @click.stop="dropSaved(row)">×</button>
      </div>
    </aside>
    <div class="main">
      <header class="mast">
        <div class="brand">
          <img class="brand-mark" src="/mark.png" width="48" height="48" alt="ImageSpace"/>
          <div>
            <h1>ImageSpace</h1>
            <p>ImageCat Solr {{ health && health.numFound != null ? health.numFound + ' docs' : '' }}</p>
          </div>
        </div>
        <div class="search-stack">
          <form class="search" @submit.prevent="runSearch(0)">
            <input v-model="q" type="search" placeholder="OCR / metadata, or * to browse" @keydown.enter.prevent="runSearch(0)" @search="onSearchBox"/>
            <button type="submit">Search</button>
          </form>
          <div v-if="filters.length || addingFilter" class="filters">
            <span v-for="(chip, i) in filters" :key="chip.field + ':' + chip.value" class="chip">
              <span class="chip-text" :title="filterLabel(chip)">{{ filterLabel(chip) }}</span>
              <button class="chip-x" type="button" :title="'Remove ' + chip.field" @click="dropFilter(i)">×</button>
            </span>
            <button v-if="!addingFilter" class="chip-add" type="button" title="Add filter" @click="startAddFilter">+</button>
            <form v-else class="chip-new" @submit.prevent="submitNewFilter">
              <input ref="newFieldEl" v-model="newField" list="field-hints" placeholder="field" @keydown.escape.prevent="cancelAddFilter"/>
              <input v-model="newValue" placeholder="value" @keydown.escape.prevent="cancelAddFilter"/>
              <button type="submit" class="chip-add" title="Add">+</button>
              <button type="button" class="chip-x" title="Cancel" @click="cancelAddFilter">×</button>
            </form>
            <datalist id="field-hints">
              <option v-for="name in fieldHints" :key="name" :value="name"/>
            </datalist>
          </div>
        </div>
        <div v-if="similarTo" class="query-wrap">
          <button class="query-image" type="button" :title="similarTo" @click="openDoc(similarTo)">
            <img :src="fileSrc(similarTo, 180)" :alt="basename(similarTo)" decoding="async"/>
            <span>
              <em>{{ similarLabel }}</em>
              {{ basename(similarTo) }}
            </span>
          </button>
          <button class="query-clear" type="button" title="Clear similar" @click="clearSimilar">×</button>
        </div>
      </header>
      <p v-if="error" class="banner">{{ error }}</p>
      <p class="status">{{ statusLine }}</p>
      <div class="iqr-bar">
        <span v-if="canIqr">IQR {{ iqrPos.length }} relevant / {{ iqrNeg.length }} not</span>
        <span v-else title="Keras 3 (Torch backend) is not installed in this ImageSpace process">IQR off (needs Keras)</span>
        <button :disabled="!canIqr || !iqrPos.length || !iqrNeg.length || loading" title="Fit the Keras head on CLIP vectors and rerank" @click="runIqr">Refine</button>
        <button class="ghost" :disabled="!iqrPos.length && !iqrNeg.length && !iqrActive" @click="clearIqr">Clear labels</button>
      </div>
      <div class="grid">
        <article v-for="doc in docs" :key="doc.id" class="tile" :class="{ pos: isPos(doc.id), neg: isNeg(doc.id) }">
          <img :src="fileSrc(doc.id, 360)" :alt="basename(doc.id)" loading="lazy" decoding="async" @click="openDoc(doc.id)"/>
          <p class="ocr">{{ scoreLine(doc) }}</p>
          <div class="actions">
            <button class="ghost" @click="toggle(doc)">{{ saved(doc.id) ? 'Remove' : 'Save' }}</button>
            <button class="ghost" @click="openDoc(doc.id)">Details</button>
            <button :disabled="!canSimilar" :title="canSimilar ? 'CLIP neighbors' : 'Build the CLIP index first'" @click="runSimilar(doc, 'clip')">Similar</button>
            <button class="ghost" :disabled="!canFg(doc)" :title="fgTitle(doc)" @click="runSimilar(doc, 'fg')">FG</button>
            <button class="ghost" :disabled="!canBg(doc)" :title="bgTitle(doc)" @click="runSimilar(doc, 'bg')">BG</button>
            <button class="ghost" :disabled="!canMeta" :title="canMeta ? 'Same metadata names (camera/pipeline)' : 'Run IndexMetadataJaccard first'" @click="runSimilar(doc, 'keys')">Keys</button>
            <button class="ghost" :disabled="!canMeta" :title="canMeta ? 'Same metadata values' : 'Run IndexMetadataJaccard first'" @click="runSimilar(doc, 'vals')">Vals</button>
            <button class="ghost" :class="{ on: isPos(doc.id) }" :disabled="!canIqr" title="Relevant" @click="markPos(doc.id)">+</button>
            <button class="ghost" :class="{ on: isNeg(doc.id) }" :disabled="!canIqr" title="Not relevant" @click="markNeg(doc.id)">−</button>
          </div>
        </article>
      </div>
      <p v-if="loading && !docs.length" class="status">Loading…</p>
      <p v-else-if="!docs.length && !loading" class="status">No images for this query.</p>
      <button v-if="docs.length < numFound" class="more ghost" type="button" :disabled="loading" @click="loadMore">Load more</button>
    </div>
    <div v-if="open" class="detail" @click.self="open = null">
      <div class="detail-card">
        <div class="detail-top">
          <img :src="fileSrc(open.id, 1280)" :alt="basename(open.id)" decoding="async"/>
          <div>
            <h2>{{ basename(open.id) }}</h2>
            <p class="status">{{ open.id }}</p>
            <div class="row">
              <button class="ghost" @click="toggle(open)">{{ saved(open.id) ? 'Remove from tray' : 'Save to tray' }}</button>
              <button :disabled="!canSimilar" :title="canSimilar ? 'CLIP neighbors' : 'Build the CLIP index first'" @click="runSimilar(open, 'clip')">Find similar</button>
              <button class="ghost" :disabled="!canFg(open)" :title="fgTitle(open)" @click="runSimilar(open, 'fg')">Similar FG</button>
              <button class="ghost" :disabled="!canBg(open)" :title="bgTitle(open)" @click="runSimilar(open, 'bg')">Similar BG</button>
              <button class="ghost" :disabled="!canMeta" :title="canMeta ? 'Same metadata names (camera/pipeline)' : 'Run IndexMetadataJaccard first'" @click="runSimilar(open, 'keys')">Keys</button>
              <button class="ghost" :disabled="!canMeta" :title="canMeta ? 'Same metadata values' : 'Run IndexMetadataJaccard first'" @click="runSimilar(open, 'vals')">Vals</button>
              <button class="ghost" :class="{ on: isPos(open.id) }" :disabled="!canIqr" @click="markPos(open.id)">Relevant</button>
              <button class="ghost" :class="{ on: isNeg(open.id) }" :disabled="!canIqr" @click="markNeg(open.id)">Not relevant</button>
              <button class="ghost" @click="open = null">Close</button>
            </div>
          </div>
        </div>
        <dl>
          <template v-for="[key, val] in fieldEntries(open)" :key="key">
            <dt>{{ key }}</dt>
            <dd>
              <template v-if="canSearchField(key) && valueList(val).length">
                <button
                  v-for="(item, i) in valueList(val)"
                  :key="i"
                  class="field-hit"
                  :class="{ on: isActiveFilter(filters, key, item) }"
                  type="button"
                  :title="'Find other images with this ' + key"
                  @click="searchField(key, item)"
                >{{ formatOne(item) }}</button>
              </template>
              <span v-else>{{ formatVal(val) }}</span>
            </dd>
          </template>
        </dl>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, nextTick, onMounted, ref } from 'vue'
import { canSearchField, fieldEntries, fileSrc, getDoc, getHealth, refineIqr, scalar, search, similar, valueList } from './api.js'
import { addFilter, filterLabel, isActiveFilter, looksLikeFieldQuery, removeFilter } from './filters.js'
import { inTray, loadTray, removeFromTray, saveTray, toggleTray } from './tray.js'

export default {
  name: 'App',
  setup() {
    const q = ref('*')
    const filters = ref([])
    const addingFilter = ref(false)
    const newField = ref('')
    const newValue = ref('')
    const newFieldEl = ref(null)
    const docs = ref([])
    const numFound = ref(0)
    const loading = ref(false)
    const error = ref('')
    const open = ref(null)
    const tray = ref(loadTray())
    const health = ref(null)
    const similarTo = ref('')
    const similarSpace = ref('clip')
    const iqrPos = ref([])
    const iqrNeg = ref([])
    const iqrActive = ref(false)
    const refining = ref(false)

    const canSimilar = computed(() => Boolean(health.value && health.value.capabilities && health.value.capabilities.similar))
    const canIqr = computed(() => Boolean(health.value && health.value.capabilities && health.value.capabilities.iqr))
    const canFgbg = computed(() => Boolean(health.value && health.value.capabilities && health.value.capabilities.fgbg))
    const canMeta = computed(() => Boolean(health.value && health.value.capabilities && health.value.capabilities.meta))

    function canFg(doc) {
      if (!canFgbg.value || !doc) {
        return false
      }
      return doc.fg_indexed !== false
    }

    function canBg(doc) {
      if (!canFgbg.value || !doc) {
        return false
      }
      return doc.bg_indexed !== false
    }

    function fgTitle(doc) {
      if (!canFgbg.value) {
        return 'Build the fg/bg index first'
      }
      if (doc && doc.fg_indexed === false) {
        return 'This image is not in the fg index yet'
      }
      return 'Foreground CLIP neighbors'
    }

    function bgTitle(doc) {
      if (!canFgbg.value) {
        return 'Build the fg/bg index first'
      }
      if (doc && doc.bg_indexed === false) {
        return 'This image is not in the bg index yet'
      }
      return 'Background CLIP neighbors'
    }
    const similarLabel = computed(() => {
      if (similarSpace.value === 'fg') {
        return 'Similar FG'
      }
      if (similarSpace.value === 'bg') {
        return 'Similar BG'
      }
      if (similarSpace.value === 'keys') {
        return 'Metadata keys like'
      }
      if (similarSpace.value === 'vals') {
        return 'Metadata values like'
      }
      return 'Similar to'
    })

    const statusLine = computed(() => {
      if (loading.value && refining.value) {
        return 'Refining…'
      }
      if (loading.value && !docs.value.length) {
        return similarTo.value ? 'Finding similar…' : 'Searching…'
      }
      const count = numFound.value + ' image' + (numFound.value === 1 ? '' : 's')
      if (iqrActive.value) {
        return 'IQR ranked — ' + count
      }
      if (similarTo.value) {
        const kind = similarSpace.value === 'fg' ? 'FG similar to '
        : similarSpace.value === 'bg' ? 'BG similar to '
          : similarSpace.value === 'keys' ? 'Metadata keys like '
            : similarSpace.value === 'vals' ? 'Metadata values like '
              : 'Similar to '
        return kind + basename(similarTo.value) + ' — ' + count
      }
      return count
    })

    function scoreLine(doc) {
      const text = scalar(doc.ocr_text) || basename(doc.id)
      if (doc.meta_score != null && doc.meta_score !== '') {
        return Number(doc.meta_score).toFixed(3) + ' · ' + text
      }
      if (doc.iqr_score != null && doc.iqr_score !== '') {
        return Number(doc.iqr_score).toFixed(3) + ' · ' + text
      }
      if (doc.clip_score == null || doc.clip_score === '') {
        return text
      }
      return Number(doc.clip_score).toFixed(3) + ' · ' + text
    }

    function isPos(id) {
      return iqrPos.value.indexOf(id) !== -1
    }

    function isNeg(id) {
      return iqrNeg.value.indexOf(id) !== -1
    }

    function markPos(id) {
      iqrNeg.value = iqrNeg.value.filter((item) => item !== id)
      if (isPos(id)) {
        iqrPos.value = iqrPos.value.filter((item) => item !== id)
      } else {
        iqrPos.value = iqrPos.value.concat([id])
      }
    }

    function markNeg(id) {
      iqrPos.value = iqrPos.value.filter((item) => item !== id)
      if (isNeg(id)) {
        iqrNeg.value = iqrNeg.value.filter((item) => item !== id)
      } else {
        iqrNeg.value = iqrNeg.value.concat([id])
      }
    }

    function basename(id) {
      const parts = String(id || '').split('/')
      return parts[parts.length - 1] || id
    }

    function formatOne(val) {
      return val == null ? '' : String(val)
    }

    function formatVal(val) {
      if (Array.isArray(val)) {
        return val.join(', ')
      }
      if (val && typeof val === 'object') {
        return JSON.stringify(val)
      }
      return formatOne(val)
    }

    const fieldHints = computed(() => {
      const names = {}
      docs.value.forEach((doc) => {
        Object.keys(doc || {}).forEach((key) => {
          if (canSearchField(key)) {
            names[key] = true
          }
        })
      })
      return Object.keys(names).sort()
    })

    function searchField(field, value) {
      const next = addFilter(filters.value, field, value)
      if (!next.length) {
        return
      }
      filters.value = next
      if (looksLikeFieldQuery(q.value)) {
        q.value = '*'
      }
      open.value = null
      runSearch(0)
    }

    function dropFilter(index) {
      filters.value = removeFilter(filters.value, index)
      runSearch(0)
    }

    async function startAddFilter() {
      addingFilter.value = true
      newField.value = ''
      newValue.value = ''
      await nextTick()
      if (newFieldEl.value) {
        newFieldEl.value.focus()
      }
    }

    function cancelAddFilter() {
      addingFilter.value = false
      newField.value = ''
      newValue.value = ''
    }

    function submitNewFilter() {
      const next = addFilter(filters.value, newField.value.trim(), newValue.value.trim())
      if (next.length === filters.value.length) {
        cancelAddFilter()
        return
      }
      filters.value = next
      cancelAddFilter()
      runSearch(0)
    }

    function saved(id) {
      return inTray(tray.value, id)
    }

    function toggle(doc) {
      tray.value = toggleTray(tray.value, doc)
      saveTray(tray.value)
    }

    function dropSaved(row) {
      tray.value = removeFromTray(tray.value, row && row.id)
      saveTray(tray.value)
    }

    async function runSearch(start) {
      loading.value = true
      error.value = ''
      similarTo.value = ''
      similarSpace.value = 'clip'
      iqrActive.value = false
      if (!start) {
        docs.value = []
      }
      try {
        const body = await search(q.value, start || 0, 24, filters.value)
        numFound.value = body.numFound || 0
        docs.value = start ? docs.value.concat(body.docs || []) : (body.docs || [])
      } catch (e) {
        error.value = e.message || String(e)
      } finally {
        loading.value = false
      }
    }

    function onSearchBox() {
      if (q.value && q.value.trim() !== '') {
        return
      }
      q.value = '*'
      similarTo.value = ''
      similarSpace.value = 'clip'
      iqrActive.value = false
      runSearch(0)
    }

    function clearSimilar() {
      similarTo.value = ''
      similarSpace.value = 'clip'
      q.value = '*'
      runSearch(0)
    }

    async function runIqr() {
      if (!canIqr.value || !iqrPos.value.length || !iqrNeg.value.length) {
        return
      }
      loading.value = true
      refining.value = true
      error.value = ''
      open.value = null
      try {
        const body = await refineIqr(iqrPos.value, iqrNeg.value, 48)
        similarTo.value = ''
        iqrActive.value = true
        numFound.value = body.numFound || 0
        docs.value = body.docs || []
      } catch (e) {
        error.value = e.message || String(e)
      } finally {
        refining.value = false
        loading.value = false
      }
    }

    function clearIqr() {
      iqrPos.value = []
      iqrNeg.value = []
      if (iqrActive.value) {
        runSearch(0)
      }
    }

    async function runSimilar(doc, space, n) {
      const mode = space || 'clip'
      if (!doc || !doc.id) {
        return
      }
      if (mode === 'clip' && !canSimilar.value) {
        return
      }
      if (mode === 'fg' && !canFg(doc)) {
        return
      }
      if (mode === 'bg' && !canBg(doc)) {
        return
      }
      if ((mode === 'keys' || mode === 'vals') && !canMeta.value) {
        return
      }
      loading.value = true
      error.value = ''
      open.value = null
      iqrActive.value = false
      try {
        const body = await similar(doc.id, n || 24, mode)
        similarTo.value = doc.id
        similarSpace.value = mode
        numFound.value = body.numFound || 0
        docs.value = body.docs || []
      } catch (e) {
        error.value = e.message || String(e)
      } finally {
        loading.value = false
      }
    }

    async function loadMore() {
      if (loading.value || docs.value.length >= numFound.value) {
        return
      }
      if (iqrActive.value) {
        loading.value = true
        refining.value = true
        error.value = ''
        try {
          const body = await refineIqr(iqrPos.value, iqrNeg.value, docs.value.length + 24)
          numFound.value = body.numFound || 0
          docs.value = body.docs || []
        } catch (e) {
          error.value = e.message || String(e)
        } finally {
          refining.value = false
          loading.value = false
        }
        return
      }
      if (similarTo.value) {
        await runSimilar({ id: similarTo.value, fg_indexed: true, bg_indexed: true }, similarSpace.value, docs.value.length + 24)
        return
      }
      await runSearch(docs.value.length)
    }

    async function openDoc(id) {
      try {
        const body = await getDoc(id)
        open.value = (body && body.doc) || docs.value.find((d) => d.id === id) || { id }
      } catch (e) {
        error.value = e.message || String(e)
      }
    }

    onMounted(async () => {
      try {
        health.value = await getHealth()
      } catch (e) {
        error.value = e.message || String(e)
      }
      await runSearch(0)
    })

    return {
      q, filters, addingFilter, newField, newValue, newFieldEl, fieldHints, docs, numFound, loading, error, open, tray, health, similarTo, similarSpace, iqrPos, iqrNeg, iqrActive, refining,
      statusLine, canSimilar, canIqr, canFgbg, canMeta, canFg, canBg, fgTitle, bgTitle, similarLabel, isPos, isNeg, markPos, markNeg, runIqr, clearIqr,
      basename, scoreLine, formatVal, formatOne, searchField, dropFilter, startAddFilter, cancelAddFilter, submitNewFilter, filterLabel, isActiveFilter, canSearchField, valueList, saved, toggle, dropSaved, runSearch, onSearchBox, loadMore, runSimilar, clearSimilar, openDoc, fileSrc, fieldEntries, scalar
    }
  }
}
</script>
