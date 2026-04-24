<script setup lang="ts">
definePageMeta({ middleware: "auth" })

import SettingsPage from "~/components/settings/SettingsPage.vue"
</script>

<template>
  <SettingsPage />
</template>
