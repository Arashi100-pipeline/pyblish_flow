<script setup lang="ts">
import { ref } from 'vue'
import { VueFlow, type Node, type Edge } from '@vue-flow/core'

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

// Connect them in order
const edges = ref<Edge[]>([
  { id: 'e1-2', source: '1', target: '2', animated: false, type: 'smoothstep' },
  { id: 'e2-3', source: '2', target: '3', animated: false, type: 'smoothstep' },
  { id: 'e3-4', source: '3', target: '4', animated: false, type: 'smoothstep' },
])

const isRunning = ref(false)
const runId = ref(0)

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

async function runPipeline() {
  if (isRunning.value) return
  const myRun = ++runId.value
  isRunning.value = true

  // Reset nodes and stop all edge animations
  nodes.value = nodes.value.map((n) => ({
    ...n,
    style: { ...(n.style || {}), background: baseNodeBg, color: baseNodeFg },
  }))
  edges.value = edges.value.map((e) => ({ ...e, animated: false }))

  // hide panel while running
  showPanel.value = false

  // Sequentially: mark node green, then animate only the edge to next node
  const order = ['1', '2', '3', '4']
  for (let i = 0; i < order.length; i++) {
    await sleep(1000)
    if (runId.value !== myRun) return

    const id = order[i]
    // mark current node as completed (green)
    nodes.value = nodes.value.map((n) =>
      n.id === id
        ? { ...n, style: { ...(n.style || {}), background: okBg, color: okFg } }
        : n,
    )

    // animate only the edge from current to next
    if (i < order.length - 1) {
      const nextId = order[i + 1]
      edges.value = edges.value.map((e) => ({
        ...e,
        animated: e.source === id && e.target === nextId,
      }))
    } else {
      // last node done: stop all edge animations
      edges.value = edges.value.map((e) => ({ ...e, animated: false }))
    }
  }

  if (runId.value === myRun) {
    isRunning.value = false
  }
}

function resetPipeline() {
  // cancel any running pipeline and reset visuals
  runId.value++
  isRunning.value = false
  nodes.value = nodes.value.map((n) => ({
    ...n,
    style: { ...(n.style || {}), background: baseNodeBg, color: baseNodeFg },
  }))
  edges.value = edges.value.map((e) => ({ ...e, animated: false }))
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
    />

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
</style>
