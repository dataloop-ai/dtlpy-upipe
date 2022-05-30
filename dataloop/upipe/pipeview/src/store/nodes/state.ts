import { APINode } from 'src/models/defs/UpipeEntities'

export interface NodesStateInterface {
  nodes: APINode[]
}

function state (): NodesStateInterface {
  return {
    nodes: []
  }
}

export default state
