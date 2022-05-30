
import { Pipe } from 'src/models/Pipe'
import { MutationTree } from 'vuex'
import { PipesStateInterface } from './state'

const mutation: MutationTree<PipesStateInterface> = {
  setPipes (state: PipesStateInterface, pipes:Pipe[]) {
    state.pipes = pipes
  }
}

export default mutation
