/* eslint-disable @typescript-eslint/no-this-alias */
import { UPipeMessage } from './defs/UpipeEntities'
import EventEmitter from 'events'

export class WebsocketHandler extends EventEmitter {
    id: string
    wsUrl: string
    private isConnected = false
    lastError : ErrorEvent | null = null 
    socket: WebSocket | null = null
    fakePid = Math.floor(Math.random() * 10) + Math.pow(2, 30);// TODO, take from server
    constructor (id:string, wsUrl:string) {
        super()
        this.id = id
        this.wsUrl = wsUrl
    }

    onMessages (messages:UPipeMessage[]) {
        for (const m of messages) {
            this.emit('on_message', m)
        }
    }
   
    disconnect () {
        if (this.socket) { this.socket.close() }
    }

    connect () {
        // Create WebSocket connection.
        this.socket = new WebSocket(this.wsUrl)

        // Connection opened
        this.socket.addEventListener('open', () => {
            console.log(`${this.id} connected`)
            this.connected = true
        })
        // Connection close
        this.socket.addEventListener('close', () => {
            console.log(`${this.id} connection closed`)
            this.connected = false
        })
        // Connection error
        this.socket.addEventListener('error', (error:any) => {
            console.log(`${this.id} connection error: ${error.message}`)
            this.error = error
        })
        
        // Listen for messages
        this.socket.addEventListener('message', (event:MessageEvent) => {
            const msgs = JSON.parse(event.data) as UPipeMessage[]
            this.onMessages(msgs)
            // console.log('Message from node ', event.data)
        })
    }
    
    get connected () {
        return this.isConnected
    }
    
    set connected (connected:boolean) {
        this.isConnected = connected
        this.emit('connected_changed', connected)
    }

    get error () {
        return this.lastError
    }
    
    set error (error:ErrorEvent | null) {
        this.lastError = error
        this.emit('error', error)
    }     
}
