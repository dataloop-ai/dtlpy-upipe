<template>
<div v-if="pipe">
    Pipe {{pipe.pipeDef.name}} : {{statusLine}}
    <q-btn-group push>
        <q-btn :disable="pipe.status==1" push label="Run" @click="toggleRun" :icon="running?'pause_circle':'play_circle'" />
        <q-btn push label="Second" icon="visibility" />
        <q-btn push label="Third" icon="update" />
    </q-btn-group>
    <processors-list :pipeId="pipeId"/>
</div>
<div id="pv">
</div>
</template>

<script lang="ts">
import {
    defineComponent
} from 'vue'

import * as d3 from 'd3'
import {
    UPipeEntityType,
    PipeExecutionStatus
} from 'src/models/defs/UpipeEntities'

import ProcessorsList from 'src/components/ProcessorsList.vue'
import {
    Pipe
} from 'src/models/Pipe'

function render (pipe: Pipe) {
    pipe.connect()
    const treeData = pipe.treeData
    // set the dimensions and margins of the diagram
    const margin = {
            top: 20,
            right: 90,
            bottom: 30,
            left: 90
        },
        width = 660 - margin.left - margin.right,
        height = 500 - margin.top - margin.bottom

    // declares a tree layout and assigns the size
    const treemap = d3.tree()
        .size([height, width])

    //  assigns the data to a hierarchy using parent-child relationships
    const nodesData = d3.hierarchy(treeData, (d: any) => d.children)

    // maps the node data to the tree layout
    const nodes = treemap(nodesData)

    // append the svg object to the body of the page
    // appends a 'group' element to 'svg'
    // moves the 'group' element to the top left margin
    const svg = d3.select('#pv').append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom),
        g = svg.append('g')
        .attr('transform',
            'translate(' + margin.left + ',' + margin.top + ')')

    // adds the links between the nodes
    g.selectAll('.link')
        .data(nodes.descendants().slice(1))
        .enter().append('path')
        .attr('class', 'link')
        .style('stroke', function (d: any) {
            return d.data.level
        })
        .attr('d', function (d: any) {
            return 'M' + d.y + ',' + d.x +
                'C' + (d.y + d.parent.y) / 2 + ',' + d.x +
                ' ' + (d.y + d.parent.y) / 2 + ',' + d.parent.x +
                ' ' + d.parent.y + ',' + d.parent.x
        })

    // adds each node as a group
    const node = g.selectAll('.node')
        .data(nodes.descendants())
        .enter().append('g')
        .attr('class', function (d) {
            return 'node' +
                (d.children ? ' node--internal' : ' node--leaf')
        })
        .attr('transform', function (d) {
            return 'translate(' + d.y + ',' + d.x + ')'
        })

    // adds symbols as nodes
    node.append('path')
        .style('stroke', function (d: any) {
            return d.data.type
        })
        .style('fill', function (d: any) {
            return d.data.level
        })
        .attr('d', d3.symbol()
            .size(function (d: any) {
                return d.data.value * 30
            })
            .type(function (d: any) {
                if (d.data.type >= UPipeEntityType.PIPELINE) {
                    return d3.symbolDiamond
                } else if (d.data.type >= UPipeEntityType.PROCESSOR) {
                    return d3.symbolCircle
                }
                return d3.symbolTriangle
            }))

    // adds the text to the node
    node.append('text')
        .attr('dy', '.35em')
        .attr('x', function (d: any) {
            return d.children
                ? (d.data.value + 4) * -1 : d.data.value + 4
        })
        .style('text-anchor', function (d) {
            return d.children ? 'end' : 'start'
        })
        .text(function (d: any) {
            let id: string = d.data.id
            if (id.length > 10) {
                id = id.substring(0, 10) + '...'
            }
            return id
        })
}

export default defineComponent({
    name: 'PipeViewComponent',
    props: {
        pipeId: {
            type: String
        }
    },
     components: {
        ProcessorsList
    },
    methods: {
        toggleRun () {
            if (this.pipe.running) {
                this.pipe.pause()
            } else {
                this.pipe.run()
            }
        }
    },
    data: function () {
        return {
            a: null
        }
    },
    watch: {
        pipeId: function () {
            render(this.pipe)
        }
    },
    computed: {
        pipe (): Pipe {
            return this.$store.getters['pipes/byId'](this.pipeId)
        },
        running (): boolean {
            if (!this.pipe) {
                return false
            }
            return this.pipe.status === PipeExecutionStatus.RUNNING
        },
        statusLine () {
            switch (this.pipe.status) {
                case PipeExecutionStatus.INIT:
                    return 'init'
                case PipeExecutionStatus.REGISTERED:
                    return 'registered'
                case PipeExecutionStatus.READY:
                    return 'ready'
                case PipeExecutionStatus.PAUSED:
                    return 'paused'
                case PipeExecutionStatus.RUNNING:
                    return 'running'
                case PipeExecutionStatus.COMPLETED:
                    return 'completed'
                default:
                    return 'NA'
            }
        }
    },
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    setup (_props) {
        return {}
    }
})
</script>
