
import { Queue } from 'src/models/Queue'
import { MutationTree } from 'vuex'
import { QueuesStateInterface } from './state'

const mutation: MutationTree<QueuesStateInterface> = {
  setQueues (state: QueuesStateInterface, queues:Queue[]) {
    state.queues = queues
  }
}

export default mutation
