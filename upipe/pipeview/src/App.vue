<template>
  <router-view />
</template>
<script lang="ts">
import { defineComponent } from 'vue'

import store from 'src/store'

// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
window.store = store

export default defineComponent({
  name: 'App'
})
</script>
