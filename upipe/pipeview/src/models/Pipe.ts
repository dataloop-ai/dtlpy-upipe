/* eslint-disable @typescript-eslint/no-this-alias */
import { APIPipe, APIProcessor, UPipeMessage, UPipeMessageType, PipeExecutionStatus, APIPipeStatusMessage, APIPipeControlMessage, PipeActionType, UPipeEntityType } from './defs/UpipeEntities'
import { pipeWsEndpoint } from 'src/boot/axios'
import { Processor } from './processor'
export class Pipe {
    pipeDef: APIPipe
    processors:Processor[] = []
    connected = false
    error = false
    socket: WebSocket | null = null
    fakePid = Math.floor(Math.random() * 10) + Math.pow(2, 30);// TODO, take from server
    status:PipeExecutionStatus = -1
    constructor (pipeDef: APIPipe) {
        this.pipeDef = pipeDef
        if (this.pipeDef.processors) {
            this.processors = Object.values(this.pipeDef.processors).map(p => new Processor(p))
        } 
    }

    getProcessor (processorId:string) {
        return this.processors.find(p => p.id === processorId)
    }

    onMessage (m:UPipeMessage) {
        if (m.type === UPipeMessageType.PIPE_STATUS) {
            this.status = (m as APIPipeStatusMessage).status
        }
    }
   
    disconnect () {
        if (this.socket) { this.socket.close() }
    }

    connect () {
        // Create WebSocket connection.
        const wsUrl = pipeWsEndpoint(this.pipeDef.id)
        this.socket = new WebSocket(wsUrl)

        // Connection opened
        this.socket.addEventListener('open', () => {
            console.log(`${this.pipeDef.id} connected`)
            this.connected = true
        })
        // Connection close
        this.socket.addEventListener('close', () => {
            console.log(`${this.pipeDef.id} connection closed`)
            this.connected = false
        })
        // Connection error
        this.socket.addEventListener('error', () => {
            console.log(`${this.pipeDef.id} connection error`)
            this.error = false
        })
        
        // Listen for messages
        this.socket.addEventListener('message', (event:MessageEvent) => {
            const msg = JSON.parse(event.data) as UPipeMessage
            this.onMessage(msg)
            console.log('Message from server ', event.data)
        })
    }

    get running () {
        return this.status === PipeExecutionStatus.RUNNING
    }

    get paused () {
        return this.status === PipeExecutionStatus.PAUSED
    }

    run () {
        this.sendAction(PipeActionType.START)
    }

    pause () {
        this.sendAction(PipeActionType.PAUSE)
    }

    restart () {
        this.sendAction(PipeActionType.RESTART)
    }

    sendAction (action:PipeActionType) {
        const msg = {} as APIPipeControlMessage
        msg.dest = this.pipeDef.id
        msg.sender = this.pipeDef.id
        msg.type = UPipeMessageType.PIPE_CONTROL
        msg.action = action
        msg.dest = this.pipeDef.id
        msg.scope = UPipeEntityType.PIPELINE
        msg.pipe_name = this.pipeDef.id
        this.socket?.send(JSON.stringify(msg))
    }

    get id () {
        return this.pipeDef.id
    }

    get name () {
        return this.pipeDef.name
    }

    get entryProcs () {
        const procs: APIProcessor[] = []
        for (const pipeId in this.pipeDef.processors) {
            let feedingQFound = false
            for (const queueId in this.pipeDef.queues) {
                if (this.pipeDef.queues[queueId].to_p === pipeId) {
                    feedingQFound = true
                    break
                }
            }
            if (feedingQFound) { continue }
            procs.push(this.pipeDef.processors[pipeId])
        }
        return procs
    }

    get treeData () {
        const treeData = {
            id: this.pipeDef.id,
            value: 10,
            type: this.pipeDef.type,
            level: 'red',
            children: [] as any[]
        }
        /* const entryProcs = this.entryProcs
        for (const proc of entryProcs) {
            treeData.children.push({
                name: proc.id,
                value: 15,
                type: 'grey',
                level: 'red'
            })
        } */
        const self = this 
        function scan (node: any) {
            for (const queueId in self.pipeDef.queues) {
                const q = self.pipeDef.queues[queueId]
                if (q.from_p === node.id) {
                    if (!node.children) { node.children = [] }
                    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
                    // @ts-ignore
                    const child = self.pipeDef.processors[q.to_p]
                    const child_ = {
                        id: child.id,
                        value: 15,
                        type: child.type,
                        level: 'red'
                    }
                    node.children.push(child_)
                    // eslint-disable-next-line @typescript-eslint/no-unused-vars
                    scan(child_)
                }
            }
        }
        scan(treeData)
        return treeData
    }
}
