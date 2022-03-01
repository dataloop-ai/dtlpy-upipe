import { store } from 'quasar/wrappers'
import { InjectionKey } from 'vue'
import {
  createStore,
  Store as VuexStore,
  useStore as vuexUseStore
} from 'vuex'

import nodes from './nodes'
import { NodesStateInterface } from './nodes/state'

import pipes from './pipes'
import { PipesStateInterface } from './pipes/state'

import queues from './queues'
import { QueuesStateInterface } from './queues/state'

/*
 * If not building with SSR mode, you can
 * directly export the Store instantiation;
 *
 * The function below can be async too; either use
 * async/await or return a Promise which resolves
 * with the Store instance.
 */

export interface StateInterface {
  // Define your own store structure, using submodules if needed
  // example: ExampleStateInterface;
  // Declared as unknown to avoid linting issue. Best to strongly type as per the line above.
  nodes: NodesStateInterface
  pipes: PipesStateInterface
  queues: QueuesStateInterface
}

// provide typings for `this.$store`
declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $store: VuexStore<StateInterface>
  }
}

// provide typings for `useStore` helper
export const storeKey: InjectionKey<VuexStore<StateInterface>> = Symbol('vuex-key')

export default store(function (/* { ssrContext } */) {
  const Store = createStore<StateInterface>({
    modules: {
      nodes,
      pipes,
      queues
    },
    // enable strict mode (adds overhead!)
    // for dev mode and --debug builds only
    strict: false// !!process.env.DEBUGGING
  })
  
  return Store
})

export function useStore () {
  return vuexUseStore(storeKey)
}
