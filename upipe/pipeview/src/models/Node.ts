/* eslint-disable @typescript-eslint/no-this-alias */
import { UPipeMessage, APINode, UPipeMessageType, APINodeUsageMessage } from './defs/UpipeEntities'
import { nodeWsEndpoint } from 'src/boot/axios'
import { Processor } from './processor'
import { WebsocketHandler } from './WebsocketHandler'
import EventEmitter from 'events'
export enum NodeStatus {
    INIT = 1,
    AVAILABLE = 2,
    CONNECTED = 3
}

export enum NodeEvents {
    onStatusUpdated = 'on_status_updated'
}

export class ComputeNode extends EventEmitter {
    status: NodeStatus
    nodeDef: APINode
    processors:Processor[] = []
    error : ErrorEvent | null = null
    socketHandler: WebsocketHandler | null = null
    fakePid = Math.floor(Math.random() * 10) + Math.pow(2, 30);// TODO, take from server
    constructor (nodeDef: APINode) {
        super()
        this.status = NodeStatus.INIT
        this.nodeDef = nodeDef
    }

    onMessage (m:UPipeMessage) {
        if (m.type === UPipeMessageType.NODE_STATUS) {
            this.emit(NodeEvents.onStatusUpdated, (m as APINodeUsageMessage).stats)
        }
    }
   
    disconnect () {
        if (this.socketHandler) { this.socketHandler.disconnect() }
    }

    connect () {
        // Create WebSocket connection.
        const wsUrl = nodeWsEndpoint(this.nodeDef.id)
        this.socketHandler = new WebsocketHandler(this.nodeDef.id, wsUrl)
        this.socketHandler.connect()
        // Connection opened
        this.socketHandler.on('connected_changed', (connected:boolean) => {
            if (connected) {
                console.log(`${this.nodeDef.id} connected`)
                this.status = NodeStatus.CONNECTED
            } else {
                console.log(`${this.nodeDef.id} connection closed`)
                this.status = NodeStatus.AVAILABLE
            }
        })
        // Connection error
        this.socketHandler.on('error', (_err:ErrorEvent) => {
            this.error = _err
        })
        // Connection messages
        this.socketHandler.on('on_message', (msg:UPipeMessage) => {
            this.onMessage(msg)
        })
    }

    get id () {
        return this.nodeDef.id
    }

    get name () {
        return this.nodeDef.name
    }

    public get connected () {
        return this.status === NodeStatus.CONNECTED
    }
}
