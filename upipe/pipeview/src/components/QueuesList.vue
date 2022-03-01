/* eslint-disable camelcase */
<template>
<div class="row">
    <q-table
      :title="`Node queues`"
      :rows="queues"
      :columns="columns"
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
            <q-btn size="sm" color="accent" round dense @click="props.expand = !props.expand" :icon="props.expand ? 'remove' : 'add'" />
          </q-td>
          <q-td
            v-for="col in props.cols"
            :key="col.name"
            :props="props"
          >
            {{ col.value }}
          </q-td>
        </q-tr>
        <q-tr v-show="props.expand" :props="props">
          <q-td colspan="100%">
            <div class="text-left">This is expand slot for row above: {{ props.row.name }}.</div>
          </q-td>
        </q-tr>
      </template>
      <!-- eslint-enable -->
    </q-table>
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

/*
export interface QueuePerformanceStats {
    allocation_counter: PerformanceMetric;
    allocation_index:   PerformanceMetric;
    dfps_in:            ThroughputPerformanceMetric;
    dfps_out:           ThroughputPerformanceMetric;
    exe_counter:        PerformanceMetric;
    exe_index:          PerformanceMetric;
    free_space:         PerformanceMetric;
    pending_counter:    PerformanceMetric;
    q_id:               string;
    size:               PerformanceMetric;
} */

const columns = [
  { name: 'id', align: 'center', label: 'Q id', field: 'id', sortable: true },
  { name: 'from_p', align: 'center', label: 'Source', field: 'from_p', sortable: true },
  { name: 'to_p', align: 'center', label: 'Sink', field: 'to_p', sortable: true },
  { name: 'allocation_counter', align: 'center', label: 'Enqueues', field: 'stats', format: (val) => `${val.allocation_counter.value}`, sortable: true },
  { name: 'exe_counter', align: 'center', label: 'Dequeues', field: 'stats', format: (val) => `${val.exe_counter.value}`, sortable: true },
  { name: 'dfps_in', align: 'center', label: 'DFPS_IN', field: 'stats', format: (val) => `${val.dfps_in.value.toFixed(2)}`, sortable: true },
  { name: 'dfps_out', align: 'center', label: 'DFPS_OUT', field: 'stats', format: (val) => `${val.dfps_out.value.toFixed(2)}`, sortable: true },
  { name: 'allocation_index', align: 'center', label: 'Alloc index', field: 'stats', format: (val) => `${val.allocation_index.value}`, sortable: true },
  { name: 'exe_index', align: 'center', label: 'Exe index', field: 'stats', format: (val) => `${val.exe_index.value}`, sortable: true },
  { name: 'pending_counter', align: 'center', label: 'Pending', field: 'stats', format: (val) => `${val.pending_counter.value}`, sortable: true },
  { name: 'usage', align: 'center', label: 'Usage', field: 'stats', format: (val) => `${((val.size.value - val.free_space.value) / val.size.value).toFixed(1)}%`, sortable: true }
]
import { Queue } from 'src/models/Queue'

export default defineComponent({
    name: 'QueuesListComponent',
    props: {
    },
    methods: {
    },
    data: function () {
        return {
            columns
        }
    },
    watch: {

    },
    computed: {
        queues ():Queue [] {
            return this.$store.getters['queues/all']()
        }
    },
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    setup (_props) {
        return {}
    }
})
</script>
