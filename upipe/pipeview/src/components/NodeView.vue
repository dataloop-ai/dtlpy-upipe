<template>
<div v-if="node">
    <div v-if="node.nodeDef" class="row">
        Node {{node.nodeDef.name}} : {{statusLine}}
        <!-- <div  class="col-4">
            Pipe {{node.nodeDef.name}} : {{statusLine}}
        </div>
        <div class="col">
            <q-icon v-if="node.connected" name="fas fa-network-wired"/>
            <q-icon v-else name="fas fa-exclamation-circle"/>
        </div> -->
    </div>
    <div v-else class="row">
        Error loading pipe
    </div>
    <div class="row" v-if="node.nodeDef">
         <div class="col-4">
            <resource-list :nodeId="nodeId"/>
         </div>
         <div class="col">
             <div class="row">
                <queues-list :nodeId="nodeId"/>
            </div>
            <div class="row">
                <pipe-view v-if="pipeId!=''" :pipeId='pipeId' />
            </div>
         </div>
    </div>
</div>
</template>

<script lang="ts">
import {
    defineComponent
} from 'vue'

import ResourceList from 'components/ResourceList.vue'
import QueuesList from 'components/QueuesList.vue'
import PipeView from 'components/PipeView.vue'
import {
    ComputeNode, NodeStatus
} from 'src/models/Node'

export default defineComponent({
    name: 'NodeViewComponent',
    props: {
        nodeId: {
            type: String
        },
        pipeId: {
            type: String
        }
    },
     components: {
        ResourceList,
        QueuesList,
        PipeView
    },
    methods: {

    },
    data: function () {
        return {
            a: null
        }
    },
    watch: {
        node: function (newNode:ComputeNode|undefined, oldNode:ComputeNode|undefined) {
            oldNode?.disconnect()
            newNode?.connect()
        }
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
        return {}
    }/*,
    mounted () {
    },
    beforeUnmount () {
    } */
})
</script>
