import { ActionTree, ActionContext } from 'vuex'
import { StateInterface } from '../index'
import { NodesStateInterface } from './state'
import { api } from 'boot/axios'
import { APINode } from 'src/models/defs/UpipeEntities'
import { ComputeNode } from 'src/models/Node'
const actions: ActionTree<NodesStateInterface, StateInterface> = {
  async fetchNodes (context:ActionContext<NodesStateInterface, StateInterface>) {
    const res = await api.get('view/nodes')
    const resData = res.data
    const nodes:ComputeNode[] = (resData.data as APINode[]).map(n => new ComputeNode(n))
    context.commit('setNodes', nodes)
  }
}

export default actions
