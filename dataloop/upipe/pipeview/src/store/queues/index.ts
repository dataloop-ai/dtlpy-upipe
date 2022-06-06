import { Module } from 'vuex'
import { StateInterface } from '../index'
import state, { QueuesStateInterface } from './state'
import actions from './actions'
import getters from './getters'
import mutations from './mutations'

const pipesStore: Module<QueuesStateInterface, StateInterface> = {
  namespaced: true,
  actions,
  getters,
  mutations,
  state
}

export default pipesStore