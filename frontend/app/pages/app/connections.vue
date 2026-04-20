<script setup lang="ts">
definePageMeta({ middleware: "auth" })

const route = useRoute()

await navigateTo({
  path: "/app/settings",
  query: route.query,
}, { replace: true })
</script>

<template>
  <div />
</template>
