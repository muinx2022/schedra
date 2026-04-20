<script setup lang="ts">
useHead({
  script: [
    {
      innerHTML: `
try {
  var theme = localStorage.getItem("social-man-theme") || "system";
  document.documentElement.dataset.themePreference = theme;
  if (theme === "dark" || theme === "light") {
    document.documentElement.dataset.theme = theme;
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
} catch (_) {}
      `,
      tagPosition: "head",
    },
  ],
})
</script>

<template>
  <div>
    <NuxtRouteAnnouncer />
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>
