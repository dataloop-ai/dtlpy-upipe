
import { Pipe } from 'src/models/Pipe'

export interface PipesStateInterface {
  pipes: Pipe[]
}

function state (): PipesStateInterface {
  return {
    pipes: []
  }
}

export default state
