<template>
<div class="row">
    <q-table
      :title="`${node.nodeDef.name} hardware resources`"
      :rows="resources"
      :columns="columns"
      row-key="name"
      dark
      color="amber"
      :pagination="initialPagination"
    ></q-table>
  </div>
</template>

<script lang="ts">
import {
    defineComponent
} from 'vue'

// import {
//     UPipeEntityType,
//     PipeExecutionStatus
// } from 'src/models/defs/UpipeEntities'

const columns = [
  { name: 'name', align: 'center', label: 'Name', field: 'name', sortable: true },
  { name: 'type', align: 'center', label: 'Type', field: 'type', sortable: true },
  { name: 'size', align: 'center', label: 'Size', field: 'size', sortable: true },
  { name: 'usage', align: 'center', label: 'Usage', field: 'usage', sortable: true }
]

import {
    ComputeNode, NodeStatus, NodeEvents
} from 'src/models/Node'

import { APINodeResource, NodePerformanceStats, CPUPerformanceMetric, DiskPerformanceMetric } from 'src/models/defs/UpipeEntities'
import { Queue } from 'src/models/Queue'
import { Pipe } from 'src/models/Pipe'

class NodeResourceUsage implements APINodeResource {
    constructor (json:Partial<NodeResourceUsage> = {}) {
        Object.assign(this, json)
    }

  config?: { [key: string]: any }|undefined
  id!: string
  name!: string
  settings?: { [key: string]: any }|undefined
  size?: number|undefined
  type!: string
  usage=-1
}

export default defineComponent({
    name: 'ResourcesListComponent',
    props: {
        nodeId: {
            type: String
        }
    },
     components: {
    },
    methods: {
        onUsageStats (u:NodePerformanceStats) {
            const totalCpu = this.resources.find(r => r.id === 'total_cpu')
            if (totalCpu) {
                totalCpu.usage = u.cpu_total.value
            }
            const memUsage = this.resources.find(r => r.id === 'memory')
            if (memUsage) {
                memUsage.usage = u.memory.value!
            }
            if (Array.isArray(u.cores_usage)) {
                for (const c of u.cores_usage) {
                    const coreCpu = this.resources.find(r => r.id === (c as CPUPerformanceMetric).core_id)
                    if (coreCpu) {
                        coreCpu.usage = (c as CPUPerformanceMetric).value
                    }
                }
            }
            if (Array.isArray(u.disks_usage)) {
                for (const d of u.disks_usage) {
                    const diskUsage = this.resources.find(r => r.id === (d as DiskPerformanceMetric).id)
                    if (diskUsage) {
                        diskUsage.usage = (d as DiskPerformanceMetric).value!
                    }
                }
            }
            if (Array.isArray(u.queues_usage)) {
                for (const qStats of u.queues_usage) {
                    const queue:Queue = this.$store.getters['queues/byId'](qStats.q_id)
                    if (queue) {
                        queue.updateStats(qStats)
                    }
                }
            }
            if (Array.isArray(u.processors_usage)) {
                for (const pStats of u.processors_usage) {
                    const pipeId = pStats.pipe_id
                    if (!pipeId) {
                        console.error('Loading stats from non existing pipe')
                    }
                    const pipe:Pipe = this.$store.getters['pipes/byId'](pipeId)
                    if (pipe) {
                        const processor = pipe.getProcessor(pStats.processor_id)
                        if (processor) {
                            processor.updateStats(pStats)
                        }
                    }
                }
            }
        }

    },
    data: function () {
        return {
            columns,
            resources: [] as NodeResourceUsage[]
        }
    },
    watch: {
    },
    computed: {
        node (): ComputeNode {
            return this.$store.getters['nodes/byId'](this.nodeId)
        },
        statusLine () {
            switch (this.node.status) {
                case NodeStatus.INIT:
                    return 'Pending'
                case NodeStatus.AVAILABLE:
                    return 'ready'
                case NodeStatus.CONNECTED:
                    return 'connected'
                default:
                    return 'NA'
            }
        }
    },
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    setup (_props) {
        return {
            initialPagination: {
                    sortBy: 'desc',
                    descending: false,
                    rowsPerPage: 20
                    // rowsNumber: xx if getting data from a server
                } 
        }
    },
    mounted () {
        if (this.node?.nodeDef?.resources) {
            this.resources = this.node.nodeDef.resources?.map((r:APINodeResource) => new NodeResourceUsage(r))
        }
        this.node.on(NodeEvents.onStatusUpdated, this.onUsageStats)
    },
    beforeUnmount () {
        this.node.off(NodeEvents.onStatusUpdated, this.onUsageStats)
        }/*,
    beforeUnmount () {
    } */
})
</script>
