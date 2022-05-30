import { ActionTree, ActionContext } from 'vuex'
import { StateInterface } from '../index'
import { PipesStateInterface } from './state'
import { api } from 'boot/axios'
import { Pipe } from 'src/models/Pipe'

import { APIPipe } from 'src/models/defs/UpipeEntities'
const actions: ActionTree<PipesStateInterface, StateInterface> = {
  async fetchPipes (context:ActionContext<PipesStateInterface, StateInterface>) {
    const res = await api.get('view/pipes')
    const resData = res.data
    
    const pipes:Pipe[] = (resData.data as APIPipe[]).map(p => new Pipe(p))
    context.commit('setPipes', pipes)
  }
}

export default actions
