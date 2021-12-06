import { GetterTree } from 'vuex'
import { StateInterface } from '../index'
import { NodesStateInterface } from './state'

const getters: GetterTree<NodesStateInterface, StateInterface> = {
  someAction (/* context */) {
    // your code
  }
}

export default getters
