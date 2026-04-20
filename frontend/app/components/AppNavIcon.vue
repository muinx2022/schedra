<script setup lang="ts">
defineProps<{ name: string; size?: number }>()
</script>

<template>
  <svg
    :width="size ?? 18"
    :height="size ?? 18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <!-- ideas: lightbulb -->
    <template v-if="name === 'ideas'">
      <path d="M15 14c.2-1 .7-1.7 1.5-2.5C17.5 10.5 18 9.2 18 8a6 6 0 0 0-12 0c0 1.2.5 2.5 1.5 3.5.8.8 1.3 1.5 1.5 2.5" />
      <path d="M9 18h6M10 22h4" />
    </template>

    <!-- campaigns: flag -->
    <template v-else-if="name === 'campaigns'">
      <path d="M5 21V4" />
      <path d="M5 5h11l-2.5 3L16 11H5" />
    </template>

    <!-- publish: send / paper plane -->
    <template v-else-if="name === 'publish'">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </template>

    <!-- calendar: compact grid -->
    <template v-else-if="name === 'calendar'">
      <rect x="4" y="5" width="16" height="15" rx="3" />
      <line x1="8" y1="3" x2="8" y2="7" />
      <line x1="16" y1="3" x2="16" y2="7" />
      <line x1="4" y1="10" x2="20" y2="10" />
      <line x1="8" y1="14" x2="8" y2="14" />
      <line x1="12" y1="14" x2="12" y2="14" />
      <line x1="16" y1="14" x2="16" y2="14" />
    </template>

    <!-- analytics: trend chart -->
    <template v-else-if="name === 'analytics'">
      <path d="M4 19V5" />
      <path d="M4 19h16" />
      <path d="M7 14l4-4 3 2 4-5" />
      <path d="M18 7h-3" />
    </template>

    <!-- inbox: chat bubble -->
    <template v-else-if="name === 'inbox'">
      <path d="M21 15a3 3 0 0 1-3 3H8l-5 4V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3z" />
      <path d="M8 9h8" />
      <path d="M8 13h5" />
    </template>

    <!-- media: stacked photo -->
    <template v-else-if="name === 'media'">
      <path d="M7 7h11a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z" />
      <path d="M9 5h8" />
      <circle cx="10" cy="11" r="1.25" />
      <path d="M7 17l4-4 3 2 2-2 2 4" />
    </template>

    <!-- settings: sliders -->
    <template v-else-if="name === 'settings'">
      <line x1="5" y1="7" x2="19" y2="7" />
      <line x1="5" y1="12" x2="19" y2="12" />
      <line x1="5" y1="17" x2="19" y2="17" />
      <circle cx="9" cy="7" r="1.5" />
      <circle cx="15" cy="12" r="1.5" />
      <circle cx="11" cy="17" r="1.5" />
    </template>
  </svg>
</template>
