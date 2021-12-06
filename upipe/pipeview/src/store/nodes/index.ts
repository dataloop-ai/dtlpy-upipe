import { Module } from 'vuex'
import { StateInterface } from '../index'
import state, { NodesStateInterface } from './state'
import actions from './actions'
import getters from './getters'
import mutations from './mutations'

const nodesStore: Module<NodesStateInterface, StateInterface> = {
  namespaced: true,
  actions,
  getters,
  mutations,
  state
}

export default nodesStore
