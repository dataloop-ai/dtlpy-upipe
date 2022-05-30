
import { GetterTree } from 'vuex'
import { StateInterface } from '../index'
import { NodesStateInterface } from './state'

const getters: GetterTree<NodesStateInterface, StateInterface> = {
  byId: (state) => (id: string) => {
    return state.nodes.find(node => node.id === id)
  }
}

export default getters
