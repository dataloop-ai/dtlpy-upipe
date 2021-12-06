<template>
<div>
    Pipe {{pipe.pipeDef.name}} details
</div>
<div class="q-pa-md">
    <q-table
      :title="`${pipe.pipeDef.name} processors`"
      :rows="procs"
      :columns="columns"
      row-key="name"
      dark
      color="amber"
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
  { name: 'name', align: 'center', label: 'Processor', field: 'name', sortable: true },
  { name: 'status', align: 'center', label: 'Status', field: 'status', sortable: true },
  { name: 'intancesCount', align: 'center', label: 'Instances', field: 'intancesCount', sortable: true }
]

import {
    Pipe
} from 'src/models/Pipe'
import { Processor } from 'src/models/Processor'

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
            columns
        }
    },
    watch: {

    },
    computed: {
        pipe (): Pipe {
            return this.$store.getters['pipes/byId'](this.pipeId)
        },
        procs ():Processor [] {
            return this.pipe.processors
        }
    },
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    setup (_props) {
        return {}
    }
})
</script>
