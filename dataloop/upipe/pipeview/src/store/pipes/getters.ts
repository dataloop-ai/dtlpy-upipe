import { GetterTree } from 'vuex'
import { StateInterface } from '../index'
import { PipesStateInterface } from './state'

const getters: GetterTree<PipesStateInterface, StateInterface> = {
  byId: (state) => (id: string) => {
    return state.pipes.find(pipe => pipe.id === id)
  }
}

export default getters
