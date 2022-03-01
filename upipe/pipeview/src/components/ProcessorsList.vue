/* eslint-disable camelcase */
<template>
<div class="row">
    <q-table
      :title="`${pipe.pipeDef.name} processors`"
      :rows="processors"
      :columns="processorsColumns"
      row-key="name"
      dark
      color="amber"
    >
    <!-- eslint-disable -->
    <template v-slot:header="props">
        <q-tr :props="props">
          <q-th auto-width />
          <q-th
            v-for="col in props.cols"
            :key="col.name"
            :props="props"
          >
            {{ col.label }}
          </q-th>
        </q-tr>
      </template>

      <template v-slot:body="props">
        <q-tr :props="props">
          <q-td auto-width>
            <q-btn size="sm" color="accent" round dense @click="activeProcessorId=props.row.id" :icon="props.expand ? 'info' : 'add'" />
          </q-td>
          <q-td
            v-for="col in props.cols"
            :key="col.name"
            :props="props"
          >
            {{ col.value }}
          </q-td>
        </q-tr>
      </template>
      <!-- eslint-enable -->
    </q-table>  
  </div>
<div class="row" v-if="activeProcessor && instances.length > 0">
    <q-table
      :title="`${activeProcessor.name} intances`"
      :rows="instances"
      :columns="instancesColumns"
      row-key="name"
      dark
      color="amber"
    >
    <!-- eslint-disable -->
    <!-- <template v-slot:header="props">
        <q-tr :props="props">
          <q-th auto-width />
          <q-th
            v-for="col in props.cols"
            :key="col.name"
            :props="props"
          >
            {{ col.label }}
          </q-th>
        </q-tr>
      </template>

      <template v-slot:body="props">
        <q-tr :props="props">
          <q-td auto-width>
            <q-btn size="sm" color="accent" round dense @click="alert(props)" icon='info' />
          </q-td>
          <q-td
            v-for="col in props.cols"
            :key="col.name"
            :props="props"
          >
            {{ col.value }}
          </q-td>
        </q-tr>
      </template> -->
      <!-- eslint-enable -->
    </q-table>
  </div>
</template>

<script lang="ts">
import {
    defineComponent
} from 'vue'
/* dfps_in:           ThroughputPerformanceMetric;
    dfps_out:          ThroughputPerformanceMetric;
    pid:               number;
    processed_counter: PerformanceMetric;
    received_counter:  PerformanceMetric; */
// import {
//     UPipeEntityType,
//     PipeExecutionStatus
// } from 'src/models/defs/UpipeEntities'

const instancesColumns = [
  { name: 'pid', align: 'center', label: 'pid', field: 'pid', sortable: true },
  { name: 'dfps_in', align: 'center', label: 'DFPS in', field: 'dfps_in', format: (val) => `${val.value.toFixed(1)}`, sortable: true },
  { name: 'dfps_out', align: 'center', label: 'DFPS out', field: 'dfps_out', format: (val) => `${val.value.toFixed(1)}`, sortable: true },
  { name: 'recieved', align: 'center', label: 'received', field: 'processed_counter', format: (val) => `${val.value}`, sortable: true },
  { name: 'processed', align: 'center', label: 'procced', field: 'received_counter', format: (val) => `${val.value}`, sortable: true }
  
]

const processorsColumns = [
  { name: 'id', align: 'center', label: 'id', field: 'id', sortable: true },
  { name: 'name', align: 'center', label: 'Processor', field: 'name', sortable: true },
  { name: 'status', align: 'center', label: 'Status', field: 'status', sortable: true },
  { name: 'intancesCount', align: 'center', label: 'Instance count', field: 'stats', format: (val) => `${val?.instances_stats ? val.instances_stats.length : 0}`, sortable: true }
]

import {
    Pipe
} from 'src/models/Pipe'
import { Processor } from 'src/models/processor'
import { PerformanceMetric, ProcessPerformanceStats, ThroughputPerformanceMetric } from 'src/models/defs/UpipeEntities'

/* eslint-disable camelcase */
class Instance implements ProcessPerformanceStats {
  constructor (json:Partial<ProcessPerformanceStats> = {}) {
        Object.assign(this, json)
    }

    dfps_in!: ThroughputPerformanceMetric
    dfps_out!: ThroughputPerformanceMetric
    processed_counter!: PerformanceMetric
    received_counter!: PerformanceMetric
    pid!: number
}

export default defineComponent({
    name: 'ProcessorsListComponent',
    props: {
        pipeId: {
            type: String,
            required: true
        }
    },
    methods: {
        toggleRun () {
            this.pipe.run()
        }
    },
    data: function () {
        return {
            processorsColumns,
            instancesColumns,
            basicModal: false,
            activeProcessorId: null
        }
    },
    watch: {

    },
    computed: {
        pipe (): Pipe {
            return this.$store.getters['pipes/byId'](this.pipeId)
        },
        activeProcessor (): Processor | null {
            if (!this.pipe) { return null }
            if (!this.activeProcessorId) { return null }
            const processor = this.pipe.getProcessor(this.activeProcessorId)
            if (!processor) { return null }
            return processor
        },
        processors ():Processor [] {
            return this.pipe.processors
        },
        instances ():Instance [] {
            const processor = this.activeProcessor
            if (!processor) { return [] }
            if (!processor.stats?.instances_stats) { return [] }
            return processor.stats?.instances_stats?.map(s => new Instance(s))
        }
    },
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    setup (_props) {
        return {}
    }
})
</script>
