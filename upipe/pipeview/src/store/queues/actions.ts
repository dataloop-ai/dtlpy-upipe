import { ActionTree, ActionContext } from 'vuex'
import { StateInterface } from '../index'
import { QueuesStateInterface } from './state'
import { api } from 'boot/axios'
import { Queue } from 'src/models/Queue'

import { APIQueue } from 'src/models/defs/UpipeEntities'
const actions: ActionTree<QueuesStateInterface, StateInterface> = {
  async fetchQueues (context:ActionContext<QueuesStateInterface, StateInterface>) {
    const res = await api.get('view/queues')
    const resData = res.data
    
    const queues:Queue[] = (resData.data as APIQueue[]).map(q => new Queue(q))
    context.commit('setQueues', queues)
  }
}

export default actions
