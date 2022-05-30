/* eslint-disable camelcase */
/* eslint-disable @typescript-eslint/no-this-alias */
import { APIProcessor, UPipeMessage, UPipeMessageType, PipeExecutionStatus, APIPipeStatusMessage, ProcessorPerformanceStats, ProcessPerformanceStats } from './defs/UpipeEntities'
import { procWsEndpoint } from 'src/boot/axios'

export class ProcessorStats implements ProcessorPerformanceStats {
    instances_stats?: ProcessPerformanceStats[] | undefined;
    pipe_id?: string | undefined;
    processor_id!: string;
    constructor (stats: ProcessorPerformanceStats) {
        Object.assign(this, stats)
    }

    get dfps_in () {
        if (!this.instances_stats) { return 0 }
        return this.instances_stats?.reduce((prev, current) => prev + current.dfps_in.value!, 0)
    }

    get dfps_out () {
        if (!this.instances_stats) { return 0 }
        return this.instances_stats?.reduce((prev, current) => prev + current.dfps_out.value!, 0)
    }

    get processed_counter () {
        if (!this.instances_stats) { return 0 }
        return this.instances_stats?.reduce((prev, current) => prev + current.processed_counter.value!, 0)
    }

    get received_counter () {
        if (!this.instances_stats) { return 0 }
        return this.instances_stats?.reduce((prev, current) => prev + current.received_counter.value!, 0)
    }
}

export class Processor {
    procDef: APIProcessor
    socket: WebSocket | null = null
    fakePid = Math.floor(Math.random() * 10) + Math.pow(2, 30);// TODO, take from server
    status:PipeExecutionStatus = PipeExecutionStatus.INIT
    lastStats:ProcessorStats | null = null
    constructor (procDef: APIProcessor) {
        this.procDef = procDef
    }

    get intancesCount () {
        return 0
    }

    onMessage (m:UPipeMessage) {
        if (m.type === UPipeMessageType.PIPE_STATUS) {
            this.status = (m as APIPipeStatusMessage).status
        }
    }
    
    connect () {
        // Create WebSocket connection.
        const wsUrl = procWsEndpoint(this.procDef.id)
        this.socket = new WebSocket(wsUrl)

        // Connection opened
        this.socket.addEventListener('open', () => {
            console.log(`${this.procDef.id} connected`)
        })

        // Listen for messages
        this.socket.addEventListener('message', (event:MessageEvent) => {
            const msg = JSON.parse(event.data) as UPipeMessage
            this.onMessage(msg)
            console.log('Message from server ', event.data)
        })
    }

    get stats () {
        return this.lastStats
    }

    updateStats (value:ProcessorPerformanceStats | null) {
        if (value) { this.lastStats = new ProcessorStats(value) }
    }

    get id () {
        return this.procDef.id
    }

    get name () {
        return this.procDef.name
    }
}
