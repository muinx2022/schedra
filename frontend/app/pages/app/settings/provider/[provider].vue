<script setup lang="ts">
definePageMeta({ middleware: "auth" })

import SettingsPage from "../../settings.vue"
</script>

<template>
  <SettingsPage />
</template>
