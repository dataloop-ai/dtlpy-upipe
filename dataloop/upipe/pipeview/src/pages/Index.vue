<template>
<div>
    <!-- <div class="row">
        <div class="col-4">
            Pipe {{pipe.pipeDef.name}} : {{statusLine}}
        </div>
        <div class="col">
            <q-icon v-if="pipe&&pipe.connected" name="fas fa-network-wired"/>
            <q-icon v-else name="fas fa-exclamation-circle"/>
        </div>
    </div> -->
    <div v-if="serverAvailable">
        <div>
            <q-btn @click="refresh" color="white" text-color="black" icon="refresh" label="Refresh" />
            <q-btn @click="selectPipe('')" color="white" text-color="black" label="Clear" />
        </div>
        <div class="row justify-left">

            <div class="q-pa-md bg-grey-10 text-white">
                <q-list dark bordered separator style="max-width: 318px">
                    <q-item  @click="selectNode(node.id)" v-for="node in nodes" :key="node.id" clickable v-ripple>
                        <q-item-section v-if="selectedNodeId==node.id" avatar>
                            <q-icon v-if="activeNode&&activeNode.connected" name="fas fa-network-wired" />
                            <q-icon v-else name="fas fa-exclamation-circle" />
                        </q-item-section>
                        <q-item-section border="white">{{node.name}}</q-item-section>
                    </q-item>
                </q-list>
            </div>
            <div class="q-pa-md bg-grey-10 text-white">
                <q-list dark bordered separator style="max-width: 318px">
                    <q-item @click="selectPipe(pipe.id)" v-for="pipe in pipes" :key="pipe.id" clickable v-ripple>
                        <q-item-section v-if="selectedPipeId==pipe.id" avatar>
                            <q-icon v-if="activeNode&&activeNode.connected" name="fas fa-network-wired" />
                            <q-icon v-else name="fas fa-exclamation-circle" />
                        </q-item-section>
                        <q-item-section >{{pipe.name}}</q-item-section>
                    </q-item>
                </q-list>
            </div>
            <!-- <example-component title="Example component" active :todos="todos" :meta="meta"></example-component> -->
        </div>
        <div class="row justify-left">

                <node-view v-if="selectedNodeId!=''" :nodeId='selectedNodeId' :pipeId='selectedPipeId'/>
            <!-- </div>
            <div class="col">
                <pipe-view v-if="selectedPipeId!=''" :pipeId='selectedPipeId' />
            </div> -->
        </div>
    </div>
    <div v-else>
        Server not found
        <q-btn @click="checkServer" color="white" text-color="black" icon="refresh" label="retry" />
    </div>
</div>
</template>

<script lang="ts">
import {
    Todo,
    Meta
} from 'components/models'
import PipeView from 'components/PipeView.vue'
import NodeView from 'components/NodeView.vue'
import {
    Pipe
} from 'src/models/Pipe'
import {
    defineComponent,
    ref
} from 'vue'
// import { APINode } from 'src/models/defs/UpipeEntities'
// import { APIResponse } from 'src/models/defs/UpipeEntities'

enum ViewId {
    NA = 'na',
    NODE_VIEW = 'node_view',
    PIPE_VIEW = 'pipe_view'
}
export default defineComponent({
    name: 'PageIndex',
    components: {
        // eslint-disable-next-line vue/no-unused-components
        PipeView,
        NodeView
    },
    methods: {
        async refresh () {
            // const res = await this.$api.get('view/nodes')
            // const nodes:APINode[] = res.data as APINode[]
            this.$store.dispatch('nodes/fetchNodes')
            this.$store.dispatch('pipes/fetchPipes')
            this.$store.dispatch('queues/fetchQueues')
            // return nodes
        },
        async checkServer () {
            this.$store.dispatch('pipes/fetchPipes').then(() => {
                    this.serverAvailable = true
                })
                .catch(() => {
                    this.serverAvailable = false
                })
                .finally(async () => {
                    if (this.serverAvailable) await this.refresh()
                    if (this.nodes.length > 0 && !this.selectedNodeId) {
                        this.selectedNodeId = this.nodes[0].id
                    }
                })
        },
        selectPipe (pipeId: string): void {
            this.selectedPipeId = pipeId
            this.viewId = ViewId.PIPE_VIEW
            if (this.activePipe && !this.activePipe.connected) {
                this.activePipe.connect()
            }
        },
        selectNode (nodeId: string): void {
            this.selectedNodeId = nodeId
            this.viewId = ViewId.NODE_VIEW
            if (this.activeNode && !this.activeNode.connected) {
                this.activeNode.connect()
            }
        }
    },
    computed: {
        nodes () {
            return this.$store.state.nodes.nodes
        },
        pipes () {
            return this.$store.state.pipes.pipes
        },
        activePipe (): Pipe {
            return this.$store.getters['pipes/byId'](this.selectedPipeId)
        },
        activeNode (): Pipe {
            return this.$store.getters['nodes/byId'](this.selectedNodeId)
        }
    },
    data () {
        return {
            selectedPipeId: '',
            selectedNodeId: '',
            serverAvailable: false,
            viewId: ViewId.NA
        }
    },
    mounted () {
        this.checkServer()
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
