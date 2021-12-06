import { ActionTree, ActionContext } from 'vuex'
import { StateInterface } from '../index'
import { NodesStateInterface } from './state'
import { api } from 'boot/axios'
import { APINode } from 'src/models/defs/UpipeEntities'
const actions: ActionTree<NodesStateInterface, StateInterface> = {
  async fetchNodes (context:ActionContext<NodesStateInterface, StateInterface>) {
    const res = await api.get('view/nodes')
    const resData = res.data
    const nodes:APINode[] = resData.data as APINode[]
    context.commit('setNodes', nodes)
  }
}

export default actions
