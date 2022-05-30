import { GetterTree } from 'vuex'
import { StateInterface } from '../index'
import { QueuesStateInterface } from './state'

const getters: GetterTree<QueuesStateInterface, StateInterface> = {
  byId: (state) => (id: string) => {
    return state.queues.find(queue => queue.id === id)
  },
  all: (state) => () => {
    return state.queues
  }
}

export default getters
