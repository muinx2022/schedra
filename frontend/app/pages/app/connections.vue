<script setup lang="ts">
definePageMeta({ middleware: "auth" })

const route = useRoute()
const localePath = useLocalePath()

await navigateTo({
  path: localePath("/app/settings"),
  query: route.query,
}, { replace: true })
</script>

<template>
  <div />
</template>
