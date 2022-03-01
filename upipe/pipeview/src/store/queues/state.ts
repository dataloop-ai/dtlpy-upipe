
import { Queue } from 'src/models/Queue'

export interface QueuesStateInterface {
  queues: Queue[]
}

function state (): QueuesStateInterface {
  return {
    queues: []
  }
}

export default state
