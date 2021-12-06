<template>
<div>
    <div>
        <q-btn @click="hi" color="white" text-color="black" label="Fetch" />
        <q-btn @click="selectPipe('')" color="white" text-color="black" label="Clear" />
    </div>
    <div class="row justify-left">

        <div class="q-pa-md bg-grey-10 text-white">
            <q-list dark bordered separator style="max-width: 318px">
                <q-item v-for="node in nodes" :key="node.id" clickable v-ripple>
                    <q-item-section>{{node.name}}</q-item-section>
                </q-item>
            </q-list>
        </div>
        <div class="q-pa-md bg-grey-10 text-white">
            <q-list dark bordered separator style="max-width: 318px">
                <q-item v-for="pipe in pipes" :key="pipe.id" clickable v-ripple>
                    <q-item-section @click="selectPipe(pipe.id)">{{pipe.name}}</q-item-section>
                </q-item>
            </q-list>
        </div>
        <div>
            <pipe-view :pipeId='selectedPipeId' />
        </div>
        <!-- <example-component title="Example component" active :todos="todos" :meta="meta"></example-component> -->
    </div>
</div>
</template>

<script lang="ts">
import {
    Todo,
    Meta
} from 'components/models'
import PipeView from 'components/PipeView.vue'
import {
    defineComponent,
    ref
} from 'vue'
// import { APINode } from 'src/models/defs/UpipeEntities'
// import { APIResponse } from 'src/models/defs/UpipeEntities'

export default defineComponent({
    name: 'PageIndex',
    components: {
        PipeView
    },
    methods: {
        async hi () {
            // const res = await this.$api.get('view/nodes')
            // const nodes:APINode[] = res.data as APINode[]
            this.$store.dispatch('nodes/fetchNodes')
            this.$store.dispatch('pipes/fetchPipes')
            // return nodes
        },
        selectPipe (pipeId: string) {
            this.selectedPipeId = pipeId
        }
    },
    computed: {
        nodes () {
            return this.$store.state.nodes.nodes
        },
        pipes () {
            return this.$store.state.pipes.pipes
        }
    },
    data () {
        return {
            selectedPipeId: ''
        }
    },
    setup () {
        const todos = ref < Todo[] >([{
                id: 1,
                content: 'ct1'
            },
            {
                id: 2,
                content: 'ct2'
            },
            {
                id: 3,
                content: 'ct3'
            },
            {
                id: 4,
                content: 'ct4'
            },
            {
                id: 5,
                content: 'ct5'
            }
        ])
        const meta = ref < Meta >({
            totalCount: 1200
        })
        return {
            todos,
            meta
        }
    }
})
</script>
