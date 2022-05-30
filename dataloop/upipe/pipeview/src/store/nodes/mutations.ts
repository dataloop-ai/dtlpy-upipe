
import { APINode } from 'src/models/defs/UpipeEntities'
import { MutationTree } from 'vuex'
import { NodesStateInterface } from './state'

const mutation: MutationTree<NodesStateInterface> = {
  setNodes (state: NodesStateInterface, nodes:APINode[]) {
    state.nodes = nodes
  }
}

export default mutation
