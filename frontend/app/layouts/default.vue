<script setup lang="ts">
const session = useSessionState()
const route = useRoute()
const router = useRouter()
const { preference: themePreference, options: themeOptions, setPreference } = useThemePreference()
const channelsDrawerOpen = ref(false)

const isApp = computed(() => route.path.startsWith("/app"))
const isIdeasRoute = computed(() => route.path === "/app/ideas")
const isCampaignsRoute = computed(() => route.path.startsWith("/app/campaigns"))
const isPostsRoute = computed(() => route.path === "/app/posts")
const isCalendarRoute = computed(() => route.path === "/app/calendar")
const isAnalyticsRoute = computed(() => route.path === "/app/analytics")
const isInboxRoute = computed(() => route.path === "/app/inbox")
const isMediaRoute = computed(() => route.path === "/app/media")
const isSettingsRoute = computed(() => route.path === "/app/settings")
const hasActiveChannelFilter = computed(() => typeof route.query.account === "string" && !!route.query.account)

const navItems = computed(() => [
  { to: "/app/ideas", label: "Ideas", icon: "ideas", active: isIdeasRoute.value },
  { to: "/app/campaigns", label: "Campaigns", icon: "campaigns", active: isCampaignsRoute.value },
  { to: "/app/posts", label: "Publish", icon: "publish", active: isPostsRoute.value && !hasActiveChannelFilter.value },
  { to: "/app/calendar", label: "Calendar", icon: "calendar", active: isCalendarRoute.value },
  { to: "/app/analytics", label: "Analytics", icon: "analytics", active: isAnalyticsRoute.value },
  { to: "/app/inbox", label: "Inbox", icon: "inbox", active: isInboxRoute.value },
  { to: "/app/media", label: "Media", icon: "media", active: isMediaRoute.value },
  { to: "/app/settings", label: "Settings", icon: "settings", active: isSettingsRoute.value },
])

const { data: accounts } = useAsyncData(
  "sidebar-accounts",
  () => apiFetch<any[]>("/accounts/"),
  { lazy: true, default: () => [], server: false }
)

async function logoutUser() {
  try {
    await apiFetch("/auth/logout/", { method: "POST", body: {} })
  } catch {
    // Reset local session even if the backend session has already expired.
  } finally {
    session.value = { authenticated: false, hydrated: true }
    await navigateTo("/login")
  }
}

function openAppNavItem(to: string) {
  if (to === "/app/posts") {
    router.push("/app/posts")
    return
  }
  router.push(to)
}

function platformColor(code: string) {
  if (code === "facebook") return "#1877f2"
  if (code === "instagram") return "#e1306c"
  if (code === "twitter" || code === "x") return "#000"
  if (code === "linkedin") return "#0077b5"
  if (code === "tiktok") return "#010101"
  return "#6b766f"
}

function platformLabel(code: string) {
  if (code === "facebook") return "f"
  if (code === "instagram") return "ig"
  if (code === "twitter" || code === "x") return "x"
  if (code === "linkedin") return "in"
  if (code === "tiktok") return "tt"
  return code[0]?.toUpperCase() ?? "?"
}

function platformName(code: string) {
  const names: Record<string, string> = {
    facebook: "Facebook",
    instagram: "Instagram",
    tiktok: "TikTok",
    linkedin: "LinkedIn",
    youtube: "YouTube",
    pinterest: "Pinterest",
  }
  return names[code] ?? code
}

const groupedAccounts = computed(() => {
  const groups: Record<string, any[]> = {}
  for (const acc of accounts.value ?? []) {
    const key = (acc.channel_code || acc.provider_code) as string
    if (!groups[key]) groups[key] = []
    groups[key].push(acc)
  }
  return groups
})

watch(() => route.fullPath, () => {
  channelsDrawerOpen.value = false
})
</script>

<template>
  <div :class="['shell', isApp ? 'shell-app' : 'shell-public']">
    <aside v-if="isApp" class="sidebar">
      <NuxtLink to="/app" class="brand sidebar-brand">Social Man</NuxtLink>

      <nav class="sidebar-nav">
        <NuxtLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          :class="{ 'nav-link-active': item.active }"
          @click.prevent="openAppNavItem(item.to)"
        >
          <AppNavIcon :name="item.icon" class="nav-icon" /> {{ item.label }}
        </NuxtLink>
      </nav>

      <div class="sidebar-channels">
        <div class="sidebar-channels-header">
          <span class="sidebar-section-label">Channels</span>
          <NuxtLink to="/app/settings" class="sidebar-channels-add" title="Add channel">+</NuxtLink>
        </div>
        <div v-if="!accounts?.length" class="sidebar-channels-empty">
          <NuxtLink to="/app/settings" class="sidebar-connect-btn">+ Connect a channel</NuxtLink>
        </div>
        <template v-for="(groupAccs, platform) in groupedAccounts" :key="platform">
          <div class="sidebar-group-header">
            <span class="sidebar-group-label">{{ platformName(String(platform)) }}</span>
            <span class="sidebar-group-count">{{ groupAccs.length }}</span>
          </div>
          <button
            v-for="acc in groupAccs.slice(0, 10)"
            :key="acc.id"
            class="sidebar-channel-item"
            :class="{ active: route.query.account == acc.id }"
            @click="router.push({ path: '/app/posts', query: { account: String(acc.id) } })"
          >
            <div class="sidebar-channel-avatar-wrap">
              <div class="sidebar-channel-avatar">{{ acc.display_name[0] }}</div>
              <div
                class="sidebar-channel-platform"
                :style="{ background: platformColor(acc.channel_code || acc.provider_code) }"
              >{{ platformLabel(acc.channel_code || acc.provider_code) }}</div>
            </div>
            <span class="sidebar-channel-name">{{ acc.display_name }}</span>
          </button>
          <NuxtLink
            v-if="groupAccs.length > 10"
            :to="`/app/settings?platform=${String(platform)}`"
            class="sidebar-show-all"
          >
            Show all ({{ groupAccs.length }})
          </NuxtLink>
        </template>
      </div>

      <div class="sidebar-footer">
        <ClientOnly>
          <div class="stack">
            <span class="muted" style="font-size:12px">{{ session.user?.workspace?.name }}</span>
            <button class="btn secondary" style="font-size:13px;padding:7px 14px" type="button" @click="logoutUser">Log out</button>
          </div>
        </ClientOnly>
      </div>
    </aside>

    <template v-if="isApp">
      <div class="mobile-app-bar">
        <NuxtLink to="/app" class="mobile-brand">Social Man</NuxtLink>
        <button class="mobile-channel-button" type="button" @click="channelsDrawerOpen = true">Channels</button>
      </div>

      <nav class="mobile-bottom-nav" aria-label="App navigation">
        <button
          v-for="item in navItems"
          :key="item.to"
          type="button"
          :class="{ active: item.active }"
          @click="openAppNavItem(item.to)"
        >
          <AppNavIcon :name="item.icon" />
          {{ item.label }}
        </button>
      </nav>

      <Teleport to="body">
        <div v-if="channelsDrawerOpen" class="mobile-drawer-overlay" @click.self="channelsDrawerOpen = false">
          <aside class="mobile-drawer">
            <div class="mobile-drawer-head">
              <div>
                <strong>Channels</strong>
                <span>{{ accounts?.length || 0 }} connected</span>
              </div>
              <button type="button" class="drawer-close" @click="channelsDrawerOpen = false">x</button>
            </div>

            <div v-if="!accounts?.length" class="sidebar-channels-empty">
              <NuxtLink to="/app/settings" class="sidebar-connect-btn">+ Connect a channel</NuxtLink>
            </div>
            <template v-for="(groupAccs, platform) in groupedAccounts" :key="platform">
              <div class="sidebar-group-header">
                <span class="sidebar-group-label">{{ platformName(String(platform)) }}</span>
                <span class="sidebar-group-count">{{ groupAccs.length }}</span>
              </div>
              <button
                v-for="acc in groupAccs"
                :key="acc.id"
                class="sidebar-channel-item"
                :class="{ active: route.query.account == acc.id }"
                @click="router.push({ path: '/app/posts', query: { account: String(acc.id) } })"
              >
                <div class="sidebar-channel-avatar-wrap">
                  <div class="sidebar-channel-avatar">{{ acc.display_name[0] }}</div>
                  <div
                    class="sidebar-channel-platform"
                    :style="{ background: platformColor(acc.channel_code || acc.provider_code) }"
                  >{{ platformLabel(acc.channel_code || acc.provider_code) }}</div>
                </div>
                <span class="sidebar-channel-name">{{ acc.display_name }}</span>
              </button>
            </template>
          </aside>
        </div>
      </Teleport>
    </template>

    <header v-else class="topbar">
      <NuxtLink to="/" class="brand">Social Man</NuxtLink>
      <nav class="nav">
        <NuxtLink to="/">Home</NuxtLink>
        <NuxtLink
          v-for="option in themeOptions"
          :key="option"
          to="#"
          class="theme-link"
          :class="{ active: themePreference === option }"
          @click.prevent="setPreference(option)"
        >
          {{ option }}
        </NuxtLink>
        <ClientOnly>
          <NuxtLink v-if="!session.authenticated" to="/login">Login</NuxtLink>
          <NuxtLink v-else to="/app">Workspace</NuxtLink>
        </ClientOnly>
      </nav>
    </header>

    <main :class="isApp ? 'app-main' : ''">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.sidebar-brand {
  color: var(--ink) !important;
  font-size: 17px !important;
  font-weight: 800;
  letter-spacing: -0.01em;
}

.sidebar-channels {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--line-soft);
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  overflow-y: auto;
}

.sidebar-channels-header,
.sidebar-group-header,
.mobile-drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-channels-header {
  padding: 0 12px 8px;
}

.sidebar-section-label,
.sidebar-group-header {
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.sidebar-channels-add {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--panel);
  color: var(--muted);
  font-size: 15px;
  display: grid;
  place-items: center;
  border: 1px solid var(--line);
  line-height: 1;
}

.sidebar-channels-add:hover {
  background: var(--surface-muted);
  color: var(--ink);
}

.sidebar-channels-empty {
  padding: 4px 12px;
}

.sidebar-connect-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--control-bg);
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
  box-shadow: var(--shadow-soft);
}

.sidebar-channel-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: none;
  color: var(--ink);
  text-align: left;
  cursor: pointer;
}

.sidebar-channel-item:hover,
.sidebar-channel-item.active {
  background: var(--surface-muted);
  border-color: var(--line-soft);
}

.sidebar-channel-avatar-wrap {
  position: relative;
  flex-shrink: 0;
  width: 30px;
  height: 30px;
}

.sidebar-channel-avatar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: var(--surface-muted);
  color: var(--ink);
  font-size: 13px;
  font-weight: 800;
  display: grid;
  place-items: center;
}

.sidebar-channel-platform {
  position: absolute;
  right: -4px;
  bottom: -3px;
  width: 14px;
  height: 14px;
  border: 1.5px solid var(--panel);
  border-radius: 50%;
  color: white;
  font-size: 7px;
  font-weight: 800;
  display: grid;
  place-items: center;
}

.sidebar-channel-name {
  flex: 1;
  overflow: hidden;
  color: var(--ink);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-group-header {
  padding: 8px 12px 2px;
  font-size: 10px;
}

.sidebar-group-count {
  opacity: 0.7;
}

.sidebar-show-all {
  display: block;
  padding: 4px 12px 8px;
  color: var(--muted);
  font-size: 11px;
}

.sidebar-show-all:hover {
  color: var(--ink);
}

.theme-link {
  border-radius: 999px;
  padding: 5px 8px;
  color: var(--muted);
  text-transform: capitalize;
}

.theme-link.active {
  background: var(--surface-muted);
  color: var(--ink);
}

.mobile-app-bar,
.mobile-bottom-nav,
.mobile-drawer-overlay {
  display: none;
}

@media (max-width: 900px) {
  .sidebar {
    display: none;
  }

  .mobile-app-bar {
    position: sticky;
    top: 0;
    z-index: 40;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--line);
    background: var(--topbar-bg);
    backdrop-filter: blur(12px);
  }

  .mobile-brand {
    font-size: 16px;
    font-weight: 900;
  }

  .mobile-channel-button,
  .drawer-close {
    min-height: 36px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--panel);
    color: var(--ink);
    padding: 0 12px;
    font-weight: 800;
  }

  .mobile-bottom-nav {
    position: fixed;
    left: max(10px, env(safe-area-inset-left));
    right: max(10px, env(safe-area-inset-right));
    bottom: max(10px, env(safe-area-inset-bottom));
    z-index: 50;
    display: grid;
    grid-template-columns: repeat(8, minmax(0, 1fr));
    gap: 4px;
    padding: 7px;
    border: 1px solid var(--line);
    border-radius: 18px;
    background: var(--bottom-nav-bg);
    box-shadow: var(--shadow-strong);
    backdrop-filter: blur(14px);
  }

  .mobile-bottom-nav button {
    min-width: 0;
    border: 0;
    border-radius: 13px;
    background: transparent;
    color: var(--muted);
    display: grid;
    place-items: center;
    gap: 2px;
    padding: 7px 2px 6px;
    font-size: 10px;
    font-weight: 800;
    cursor: pointer;
  }

  .mobile-bottom-nav button span {
    display: grid;
    place-items: center;
    width: 22px;
    height: 22px;
    border-radius: 8px;
    background: var(--surface-muted);
    color: inherit;
    font-size: 11px;
  }

  .mobile-bottom-nav button.active {
    color: var(--ink);
    background: var(--surface-muted);
  }

  .mobile-drawer-overlay {
    position: fixed;
    inset: 0;
    z-index: 80;
    display: flex;
    align-items: flex-end;
    background: var(--overlay);
    padding: 16px;
  }

  .mobile-drawer {
    width: 100%;
    max-height: min(78vh, 680px);
    overflow-y: auto;
    border: 1px solid var(--line);
    border-radius: 24px 24px 18px 18px;
    background: var(--panel);
    box-shadow: var(--shadow-strong);
    padding: 16px;
  }

  .mobile-drawer-head {
    gap: 12px;
    margin-bottom: 12px;
  }

  .mobile-drawer-head div {
    display: grid;
    gap: 2px;
  }

  .mobile-drawer-head span {
    color: var(--muted);
    font-size: 12px;
  }

  .topbar {
    padding: 14px 16px;
  }

  .topbar .nav {
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
    font-size: 13px;
  }
}
</style>
