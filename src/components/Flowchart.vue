<script setup lang="ts">
import { ref } from 'vue'
import { VueFlow, useVueFlow, ConnectionMode, type Node, type Edge } from '@vue-flow/core'

// panel state
const showPanel = ref(false)
const selectedNodeId = ref<string | null>(null)

// params per node
const closestPointParams = ref({ distanceThreshold: '10cm' })
const isolatedVertexParams = ref([
  { name: 'Grass', index: 0 },
  { name: 'Tree', index: 0 },
])

// Base colors
const baseNodeBg = '#ffffff'
const baseNodeFg = '#213547'
const okBg = '#22c55e' // green
const okFg = '#ffffff'

// Define the pipeline nodes
const nodes = ref<Node[]>([
  { id: '1', type: 'input', label: 'CollectInstances', position: { x: 80, y: 120 }, style: { background: baseNodeBg, color: baseNodeFg } },
  { id: '2', label: 'ValidateClosestPoint', position: { x: 340, y: 120 }, style: { background: baseNodeBg, color: baseNodeFg } },
  { id: '3', label: 'ValidateIsolatedVertex', position: { x: 660, y: 120 }, style: { background: baseNodeBg, color: baseNodeFg } },
  { id: '4', type: 'output', label: 'ExtractFBXSimple', position: { x: 980, y: 120 }, style: { background: baseNodeBg, color: baseNodeFg } },
])

// Start with no edges; user will connect manually
const edges = ref<Edge[]>([])

const isRunning = ref(false)
const runId = ref(0)
const esRef = ref<EventSource | null>(null)
const runLogs = ref<string[]>([])

const { addEdges, toObject } = useVueFlow()

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

function buildAdjacency() {
  const adj: Record<string, string[]> = {}
  const indeg: Record<string, number> = {}
  for (const n of nodes.value) { adj[n.id] = []; indeg[n.id] = 0 }
  for (const e of edges.value) {
    (adj[e.source] ||= []).push(e.target)
    indeg[e.target] = (indeg[e.target] ?? 0) + 1
    if (!(e.source in indeg)) indeg[e.source] = indeg[e.source] ?? 0
  }
  return { adj, indeg }
}

function computeChainOrder(): string[] {
  const { adj, indeg } = buildAdjacency()
  const start = Object.keys(indeg).find((k) => (indeg[k] ?? 0) === 0)
  const order: string[] = []
  const seen = new Set<string>()
  let cur = start
  while (cur && !seen.has(cur)) {
    order.push(cur)
    seen.add(cur)
    const outs = adj[cur] || []
    cur = outs[0]
  }
  return order
}

async function runPipeline() {
  if (isRunning.value) return
  const myRun = ++runId.value
  isRunning.value = true

  // Reset visuals and stop all edge animations
  nodes.value = nodes.value.map((n) => ({
    ...n,
    style: { ...(n.style || {}), background: baseNodeBg, color: baseNodeFg },
  }))
  edges.value = edges.value.map((e) => ({ ...e, animated: false }))

  // hide panel while running
  showPanel.value = false

  // close previous stream if any
  // clear previous run logs
  runLogs.value = []

  if (esRef.value) { esRef.value.close(); esRef.value = null }

  // Prepare payload from current flow
  const flow = toObject()
  const payload = {
    flow,
    params: {
      closestPointParams: closestPointParams.value,
      isolatedVertexParams: isolatedVertexParams.value,
    },
  }

  try {
    const resp = await fetch('http://localhost:8000/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const { jobId } = await resp.json()

    const es = new EventSource(`http://localhost:8000/runs/${jobId}/events`)
    esRef.value = es

    es.onopen = () => {
      console.log('[SSE] connected to job', jobId)
      // Do not push to runLogs here to keep YAML line as the first entry
    }

    es.addEventListener('log', (ev) => {
      try {
        const { line } = JSON.parse((ev as MessageEvent).data)
        console.log('[SSE log]', line)
        runLogs.value.push(line)
      } catch {}
    })

    es.addEventListener('stage', (ev) => {
      if (runId.value !== myRun) return
      try {
        const data = JSON.parse((ev as MessageEvent).data)
        const id = data.nodeId as string
        if (!id) return
        // mark node done
        nodes.value = nodes.value.map((n) =>
          n.id === id
            ? { ...n, style: { ...(n.style || {}), background: okBg, color: okFg } }
            : n,
        )
        // animate only the edge to next node (first outgoer)
        const { adj } = buildAdjacency()
        const nextId = (adj[id] || [])[0]
        if (nextId) {
          edges.value = edges.value.map((e) => ({
            ...e,
            animated: e.source === id && e.target === nextId,
          }))
        } else {
          edges.value = edges.value.map((e) => ({ ...e, animated: false }))
        }
        // also append a short stage log for visibility
        const status = data.status || 'done'
        runLogs.value.push(`[stage] ${id}: ${status}`)
      } catch {}
    })

    es.addEventListener('done', () => {
      if (runId.value !== myRun) return
      console.log('[SSE] done for job', jobId)
      runLogs.value.push(`[SSE] done for job ${jobId}`)
      isRunning.value = false
      edges.value = edges.value.map((e) => ({ ...e, animated: false }))
      es.close()
      esRef.value = null
    })

    es.onerror = (err) => {
      console.warn('[SSE] error', err)
      // browser will auto-reconnect by default
    }
  } catch (err) {
    // Fallback: local simulation following simple chain
    const order = computeChainOrder()
    for (let i = 0; i < order.length; i++) {
      await sleep(1000)
      if (runId.value !== myRun) return
      const id = order[i]
      nodes.value = nodes.value.map((n) =>
        n.id === id
          ? { ...n, style: { ...(n.style || {}), background: okBg, color: okFg } }
          : n,
      )
      if (i < order.length - 1) {
        const nextId = order[i + 1]
        edges.value = edges.value.map((e) => ({
          ...e,
          animated: e.source === id && e.target === nextId,
        }))
      } else {
        edges.value = edges.value.map((e) => ({ ...e, animated: false }))
      }
    }
    if (runId.value === myRun) isRunning.value = false
  }
}

function resetPipeline() {
  // cancel any running pipeline and reset visuals
  runId.value++
  isRunning.value = false
  if (esRef.value) { esRef.value.close(); esRef.value = null }
  nodes.value = nodes.value.map((n) => ({
    ...n,
    style: { ...(n.style || {}), background: baseNodeBg, color: baseNodeFg },
  }))
  edges.value = edges.value.map((e) => ({ ...e, animated: false }))
}

function clearLogs() {
  runLogs.value = []
}

function onNodeClick(e: any) {
  const id = e?.node?.id ?? e?.id ?? null
  selectedNodeId.value = id
  showPanel.value = id === '2' || id === '3'
}

function closePanel() {
  showPanel.value = false
  selectedNodeId.value = null
}

function onEdgeClick(payload: any) {
  const edge = payload?.edge as Edge | undefined
  const ev = payload?.event as MouseEvent | undefined
  if (!edge || !ev) return
  // Alt (Option on macOS) + click to delete this edge
  if (ev.altKey) {
    edges.value = edges.value.filter((e) => e.id !== edge.id)
  }
}




const onConnect = (params: any) => addEdges([params])
</script>

<template>
  <div class="flow-container">
    <div class="toolbar">
      <button @click="runPipeline" :disabled="isRunning">Run</button>
      <button @click="resetPipeline">Reset</button>
    </div>

    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      fit-view-on-init
      @node-click="onNodeClick"
      @edge-click="onEdgeClick"
      @connect="onConnect"
      :nodes-connectable="true"
      :connect-on-click="true"
      :connection-mode="ConnectionMode.Loose"
    />

    <div class="logs">
      <div class="logs-header">
        <span>Run Logs</span>
        <button @click="clearLogs" :disabled="!runLogs.length">Clear</button>
      </div>
      <div class="logs-body">
        <div v-for="(l,i) in runLogs" :key="i">{{ l }}</div>
      </div>
    </div>

    <div class="drawer" :class="{ open: showPanel }">
      <div class="drawer-header">
        <span v-if="selectedNodeId==='2'">ValidateClosestPoint</span>
        <span v-else-if="selectedNodeId==='3'">ValidateIsolatedVertex</span>
        <span v-else>Parameters</span>
        <button class="close" @click="closePanel">×</button>
      </div>

      <div class="drawer-body">
        <div v-if="selectedNodeId==='2'">
          <label style="display:block; margin-bottom:6px;">distance threshold</label>
          <input class="nodrag nowheel" v-model="closestPointParams.distanceThreshold" placeholder="e.g. 10cm" />
        </div>

        <div v-else-if="selectedNodeId==='3'">
          <table class="params">
            <thead>
              <tr><th>Type</th><th>Index</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in isolatedVertexParams" :key="row.name">
                <td>{{ row.name }}</td>
                <td><input class="nodrag nowheel" type="number" min="0" v-model.number="row.index" /></td>
              </tr>


            </tbody>
          </table>
        </div>

        <div v-else>
          <em>Select a configurable node</em>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.flow-container { position: relative; height: 100vh; width: 100%; border: 1px dashed #999; }
.toolbar { padding: 8px; display: flex; gap: 8px; align-items: center }
.drawer { position: fixed; top: 0; right: 0; height: 100vh; width: 340px; background: #fff; color: #213547; box-shadow: -2px 0 8px rgba(0,0,0,.12); transform: translateX(100%); transition: transform .25s ease; z-index: 50; padding: 12px; }
.drawer.open { transform: translateX(0); }
.drawer-header { display:flex; justify-content: space-between; align-items:center; font-weight:600; margin-bottom: 8px; }
.drawer-header .close { border: none; background: transparent; font-size: 20px; line-height: 1; cursor: pointer; }
.params input { width: 120px; }
.logs { position: fixed; right: 16px; bottom: 16px; width: 420px; padding: 8px; background: #0b1021; color: #c8d3f5; border-radius: 6px; max-height: 40vh; overflow: auto; z-index: 60; box-shadow: 0 4px 14px rgba(0,0,0,.25); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
.logs-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-weight: 600; }
.logs-body { white-space: pre-wrap; font-size: 12px; line-height: 1.4; }
</style>

