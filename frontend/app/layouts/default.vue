<script setup lang="ts">
const session = useSessionState()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const localePath = useLocalePath()
const switchLocalePath = useSwitchLocalePath()
const { locale } = useI18n()
const { preference: themePreference, options: themeOptions, setPreference } = useThemePreference()
const channelsDrawerOpen = ref(false)
const languageMenuOpen = ref(false)
const expandedChannelId = ref("")

const localePrefixRE = /^\/(en|vi)(?=\/|$)/
const pathNoLocale = computed(() => {
  const stripped = route.path.replace(localePrefixRE, "")
  return stripped.length ? stripped : "/"
})

const isApp = computed(() => pathNoLocale.value.startsWith("/app"))
const isIdeasRoute = computed(() => pathNoLocale.value === "/app/ideas")
const isCampaignsRoute = computed(() => pathNoLocale.value.startsWith("/app/campaigns"))
const isPostsRoute = computed(() => pathNoLocale.value === "/app/posts")
const isCalendarRoute = computed(() => pathNoLocale.value === "/app/calendar")
const isAnalyticsRoute = computed(() => pathNoLocale.value === "/app/analytics")
const isInboxRoute = computed(() => pathNoLocale.value === "/app/inbox")
const isMediaRoute = computed(() => pathNoLocale.value === "/app/media")
const isSettingsRoute = computed(() => pathNoLocale.value === "/app/settings")
const hasActiveChannelFilter = computed(() => typeof route.query.account === "string" && !!route.query.account)

const navItems = computed(() => [
  { to: "/app/ideas", labelKey: "nav.ideas", icon: "ideas", active: isIdeasRoute.value },
  { to: "/app/campaigns", labelKey: "nav.campaigns", icon: "campaigns", active: isCampaignsRoute.value },
  { to: "/app/posts", labelKey: "nav.publish", icon: "publish", active: isPostsRoute.value && !hasActiveChannelFilter.value },
  { to: "/app/calendar", labelKey: "nav.calendar", icon: "calendar", active: isCalendarRoute.value },
  { to: "/app/analytics", labelKey: "nav.analytics", icon: "analytics", active: isAnalyticsRoute.value },
  { to: "/app/media", labelKey: "nav.media", icon: "media", active: isMediaRoute.value },
  { to: "/app/settings", labelKey: "nav.settings", icon: "settings", active: isSettingsRoute.value },
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
    await navigateTo(localePath("/login"))
  }
}

function openAppNavItem(to: string) {
  if (to === "/app/posts") {
    router.push(localePath("/app/posts"))
    return
  }
  router.push(localePath(to))
}

function toggleChannelGroup(accountId: string) {
  expandedChannelId.value = expandedChannelId.value === accountId ? "" : accountId
}

function isChannelViewActive(accountId: string, view: "publish" | "community") {
  if (String(route.query.account || "") !== String(accountId)) return false
  if (view === "publish") return pathNoLocale.value === "/app/posts"
  return pathNoLocale.value === "/app/inbox"
}

function openChannelView(accountId: string, view: "publish" | "community") {
  const path = view === "publish" ? "/app/posts" : "/app/inbox"
  router.push({ path: localePath(path), query: { account: String(accountId) } })
}

function accountPlatformClass(account: any): string {
  const providerCode = String(account?.provider_code || account?.channel_code || "").toLowerCase()
  if (["facebook", "instagram", "linkedin", "tiktok", "youtube", "pinterest"].includes(providerCode)) {
    return providerCode
  }
  if (account?.account_type === "instagram_business") return "instagram"
  if (account?.account_type === "tiktok_creator") return "tiktok"
  if (account?.account_type === "youtube_channel") return "youtube"
  if (account?.account_type === "personal") return "linkedin"
  if (account?.account_type === "pinterest_board") return "pinterest"
  return "facebook"
}

function accountDescriptor(account: any): string {
  if (account?.account_type === "instagram_business") return "Instagram Business"
  if (account?.account_type === "tiktok_creator") return "TikTok Creator"
  if (account?.account_type === "youtube_channel") return "YouTube Channel"
  if (account?.account_type === "personal") return "LinkedIn Profile"
  if (account?.account_type === "organization") return "LinkedIn Page"
  if (account?.account_type === "pinterest_board") return "Pinterest Board"
  return "Facebook Page"
}

watch(() => route.fullPath, () => {
  channelsDrawerOpen.value = false
  languageMenuOpen.value = false
  const accountId = String(route.query.account || "")
  expandedChannelId.value = accountId || expandedChannelId.value
})
</script>

<template>
  <div :class="['shell', isApp ? 'shell-app' : 'shell-public']">
    <aside v-if="isApp" class="sidebar">
      <NuxtLink :to="localePath('/app')" class="brand sidebar-brand">
        <span class="brand-icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.12"/>
            <circle cx="7" cy="12" r="2.2" fill="currentColor"/>
            <circle cx="17" cy="7" r="2.2" fill="currentColor"/>
            <circle cx="17" cy="17" r="2.2" fill="currentColor"/>
            <line x1="9" y1="11" x2="15" y2="8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            <line x1="9" y1="13" x2="15" y2="16" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          </svg>
        </span>
        Schedra
      </NuxtLink>

      <nav class="sidebar-nav">
        <NuxtLink
          v-for="item in navItems"
          :key="item.to"
          :to="localePath(item.to)"
          :class="{ 'nav-link-active': item.active }"
          @click.prevent="openAppNavItem(item.to)"
        >
          <AppNavIcon :name="item.icon" class="nav-icon" /> {{ t(item.labelKey) }}
        </NuxtLink>
      </nav>

      <div class="sidebar-channels">
        <div class="sidebar-channels-header">
          <span class="sidebar-section-label">{{ t("common.channels") }}</span>
          <NuxtLink :to="localePath('/app/settings')" class="sidebar-channels-add" :title="t('nav.settings')">+</NuxtLink>
        </div>
        <div v-if="!accounts?.length" class="sidebar-channels-empty">
          <NuxtLink :to="localePath('/app/settings')" class="sidebar-connect-btn">+ {{ t("common.connect_channel") }}</NuxtLink>
        </div>
        <div
          v-for="acc in accounts"
          :key="acc.id"
          class="sidebar-channel-group"
          :class="{ active: route.query.account == acc.id, expanded: expandedChannelId === String(acc.id) }"
        >
          <button class="sidebar-channel-item" @click="toggleChannelGroup(String(acc.id))">
            <div class="sidebar-channel-provider" :class="`is-${accountPlatformClass(acc)}`">
              <PlatformIcon :platform="accountPlatformClass(acc)" :size="17" />
            </div>
            <span class="sidebar-channel-copy">
              <span class="sidebar-channel-name">{{ acc.display_name }}</span>
              <span class="sidebar-channel-meta">{{ accountDescriptor(acc) }}</span>
            </span>
            <span class="sidebar-channel-caret">{{ expandedChannelId === String(acc.id) ? "−" : "+" }}</span>
          </button>

          <div v-if="expandedChannelId === String(acc.id)" class="sidebar-channel-links">
            <button
              class="sidebar-channel-link"
              :class="{ active: isChannelViewActive(String(acc.id), 'publish') }"
              @click="openChannelView(String(acc.id), 'publish')"
            >
              <AppNavIcon name="publish" :size="14" />
              <span>{{ t("nav.publish") }}</span>
            </button>
            <button
              class="sidebar-channel-link"
              :class="{ active: isChannelViewActive(String(acc.id), 'community') }"
              @click="openChannelView(String(acc.id), 'community')"
            >
              <AppNavIcon name="inbox" :size="14" />
              <span>Community</span>
            </button>
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
        <ClientOnly>
          <div class="stack" style="gap:10px">
            <div class="lang-switch">
              <button class="btn secondary lang-btn" type="button" @click="languageMenuOpen = !languageMenuOpen">
                {{ locale === "vi" ? "VI" : "EN" }}
              </button>
              <div v-if="languageMenuOpen" class="lang-menu">
                <NuxtLink class="lang-item" :to="switchLocalePath('en')">English</NuxtLink>
                <NuxtLink class="lang-item" :to="switchLocalePath('vi')">Tiếng Việt</NuxtLink>
              </div>
            </div>
            <span class="muted" style="font-size:12px">{{ session.user?.workspace?.name }}</span>
            <button class="btn secondary" style="font-size:13px;padding:7px 14px" type="button" @click="logoutUser">{{ t("common.log_out") }}</button>
          </div>
        </ClientOnly>
      </div>
    </aside>

    <template v-if="isApp">
      <div class="mobile-app-bar">
        <NuxtLink :to="localePath('/app')" class="mobile-brand">
          <span class="brand-icon" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.12"/>
              <circle cx="7" cy="12" r="2.2" fill="currentColor"/>
              <circle cx="17" cy="7" r="2.2" fill="currentColor"/>
              <circle cx="17" cy="17" r="2.2" fill="currentColor"/>
              <line x1="9" y1="11" x2="15" y2="8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              <line x1="9" y1="13" x2="15" y2="16" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
          </span>
          Schedra
        </NuxtLink>
        <div style="display:flex;gap:8px;align-items:center">
          <NuxtLink class="mobile-channel-button" :to="switchLocalePath(locale === 'vi' ? 'en' : 'vi')" title="Switch language">
            {{ locale === "vi" ? "EN" : "VI" }}
          </NuxtLink>
          <button class="mobile-channel-button" type="button" @click="channelsDrawerOpen = true">{{ t("common.channels") }}</button>
        </div>
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
          {{ t(item.labelKey) }}
        </button>
      </nav>

      <Teleport to="body">
        <div v-if="channelsDrawerOpen" class="mobile-drawer-overlay" @click.self="channelsDrawerOpen = false">
          <aside class="mobile-drawer">
            <div class="mobile-drawer-head">
              <div>
                <strong>{{ t("common.channels") }}</strong>
                <span>{{ t("common.connected_count", { count: accounts?.length || 0 }) }}</span>
              </div>
              <button type="button" class="drawer-close" @click="channelsDrawerOpen = false">x</button>
            </div>

            <div v-if="!accounts?.length" class="sidebar-channels-empty">
              <NuxtLink :to="localePath('/app/settings')" class="sidebar-connect-btn">+ {{ t("common.connect_channel") }}</NuxtLink>
            </div>
            <div
              v-for="acc in accounts"
              :key="acc.id"
              class="sidebar-channel-group"
              :class="{ active: route.query.account == acc.id, expanded: expandedChannelId === String(acc.id) }"
            >
              <button class="sidebar-channel-item" @click="toggleChannelGroup(String(acc.id))">
                <div class="sidebar-channel-provider" :class="`is-${accountPlatformClass(acc)}`">
                  <PlatformIcon :platform="accountPlatformClass(acc)" :size="17" />
                </div>
                <span class="sidebar-channel-copy">
                  <span class="sidebar-channel-name">{{ acc.display_name }}</span>
                  <span class="sidebar-channel-meta">{{ accountDescriptor(acc) }}</span>
                </span>
                <span class="sidebar-channel-caret">{{ expandedChannelId === String(acc.id) ? "−" : "+" }}</span>
              </button>

              <div v-if="expandedChannelId === String(acc.id)" class="sidebar-channel-links">
                <button
                  class="sidebar-channel-link"
                  :class="{ active: isChannelViewActive(String(acc.id), 'publish') }"
                  @click="openChannelView(String(acc.id), 'publish')"
                >
                  <AppNavIcon name="publish" :size="14" />
                  <span>{{ t("nav.publish") }}</span>
                </button>
                <button
                  class="sidebar-channel-link"
                  :class="{ active: isChannelViewActive(String(acc.id), 'community') }"
                  @click="openChannelView(String(acc.id), 'community')"
                >
                  <AppNavIcon name="inbox" :size="14" />
                  <span>Community</span>
                </button>
              </div>
            </div>
          </aside>
        </div>
      </Teleport>
    </template>

    <header v-else class="topbar topbar-marketing">
      <NuxtLink :to="localePath('/')" class="brand">
        <span class="brand-icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.12"/>
            <circle cx="7" cy="12" r="2.2" fill="currentColor"/>
            <circle cx="17" cy="7" r="2.2" fill="currentColor"/>
            <circle cx="17" cy="17" r="2.2" fill="currentColor"/>
            <line x1="9" y1="11" x2="15" y2="8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            <line x1="9" y1="13" x2="15" y2="16" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          </svg>
        </span>
        Schedra
      </NuxtLink>
      <nav class="nav nav-marketing" aria-label="Marketing">
        <NuxtLink :to="localePath('/') + '#buf-features'">{{ t("marketing.features") }}</NuxtLink>
        <NuxtLink :to="localePath('/') + '#buf-channels'">{{ t("marketing.channels") }}</NuxtLink>
        <NuxtLink :to="localePath('/') + '#buf-pricing'">{{ t("marketing.pricing") }}</NuxtLink>
      </nav>
      <div class="topbar-marketing-right">
        <div class="lang-switch">
          <button class="btn secondary lang-btn" type="button" @click="languageMenuOpen = !languageMenuOpen">
            {{ locale === "vi" ? "VI" : "EN" }}
          </button>
          <div v-if="languageMenuOpen" class="lang-menu">
            <NuxtLink class="lang-item" :to="switchLocalePath('en')">English</NuxtLink>
            <NuxtLink class="lang-item" :to="switchLocalePath('vi')">Tiếng Việt</NuxtLink>
          </div>
        </div>
        <div class="theme-switcher" role="group" aria-label="Theme">
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
        </div>
        <ClientOnly>
          <template v-if="!session.authenticated">
            <NuxtLink class="btn secondary topbar-btn-ghost" :to="localePath('/login')">{{ t("common.log_in") }}</NuxtLink>
            <NuxtLink class="btn topbar-btn-primary" :to="localePath('/register')">{{ t("marketing.get_started_free") }}</NuxtLink>
          </template>
          <template v-else>
            <NuxtLink class="btn secondary topbar-btn-ghost" :to="localePath('/app')">{{ t("common.workspace") }}</NuxtLink>
            <NuxtLink class="btn topbar-btn-primary" :to="localePath('/app/posts')">{{ t("marketing.open_publishing") }}</NuxtLink>
          </template>
        </ClientOnly>
      </div>
    </header>

    <main :class="isApp ? 'app-main' : ''">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.brand-icon {
  display: inline-flex;
  align-items: center;
  color: var(--brand-fill);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

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
.mobile-drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-channels-header {
  padding: 0 12px 8px;
}

.sidebar-section-label {
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

.sidebar-channel-group {
  display: grid;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 14px;
}

.sidebar-channel-group.active {
  background: rgba(127, 162, 147, 0.08);
}

.sidebar-channel-group.expanded {
  background: rgba(127, 162, 147, 0.08);
}

.sidebar-channel-links {
  display: grid;
  gap: 4px;
  padding-left: 40px;
}

.sidebar-channel-caret {
  flex-shrink: 0;
  color: var(--muted);
  font-size: 16px;
  line-height: 1;
}

.sidebar-channel-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

.sidebar-channel-link:hover,
.sidebar-channel-link.active {
  color: var(--ink);
  background: var(--surface-muted);
  border-color: var(--line-soft);
}

.sidebar-channel-provider {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  color: white;
}

.sidebar-channel-provider.is-facebook {
  background: #1877f2;
}

.sidebar-channel-provider.is-instagram {
  background: #e1306c;
}

.sidebar-channel-provider.is-linkedin {
  background: #0a66c2;
}

.sidebar-channel-provider.is-youtube {
  background: #ff0000;
}

.sidebar-channel-provider.is-tiktok {
  background: #111111;
}

.sidebar-channel-provider.is-pinterest {
  background: #e60023;
}

.sidebar-channel-copy {
  flex: 1;
  min-width: 0;
  display: grid;
}

.sidebar-channel-name {
  overflow: hidden;
  color: var(--ink);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-channel-meta {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.2;
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

.lang-switch {
  position: relative;
}

.lang-btn {
  padding: 6px 10px !important;
  min-height: 32px;
  font-size: 12px;
  font-weight: 900;
}

.lang-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 140px;
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: 14px;
  box-shadow: var(--shadow-strong);
  padding: 6px;
  z-index: 90;
}

.lang-item {
  display: flex;
  padding: 9px 10px;
  border-radius: 12px;
  text-decoration: none;
  color: var(--ink);
  font-weight: 700;
  font-size: 13px;
}

.lang-item:hover {
  background: var(--surface-muted);
}

.mobile-app-bar,
.mobile-bottom-nav,
.mobile-drawer-overlay {
  display: none;
}

.topbar-marketing {
  flex-wrap: wrap;
}

.topbar-marketing .brand {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.nav-marketing {
  flex: 1;
  justify-content: center;
  gap: 28px;
  font-size: 15px;
  font-weight: 600;
}

.nav-marketing a {
  color: var(--muted);
  text-decoration: none;
  transition: color 0.12s;
}

.nav-marketing a:hover,
.nav-marketing a.router-link-active {
  color: var(--ink);
}

.topbar-marketing-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.theme-switcher {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-right: 4px;
}

.theme-switcher .theme-link {
  font-size: 12px;
  padding: 4px 7px;
}

.topbar-btn-ghost {
  padding: 8px 16px !important;
  font-size: 14px !important;
}

.topbar-btn-primary {
  padding: 8px 18px !important;
  font-size: 14px !important;
  border-color: var(--brand-fill) !important;
  background: var(--brand-fill) !important;
  color: #fff !important;
  box-shadow: 0 6px 20px rgba(31, 75, 57, 0.25);
}

.topbar-btn-primary:hover:not(:disabled) {
  background: var(--brand-fill-hover) !important;
  border-color: var(--brand-fill-hover) !important;
  transform: translateY(-1px);
}

@media (max-width: 1040px) {
  .nav-marketing {
    order: 3;
    width: 100%;
    justify-content: center;
    border-top: 1px solid var(--line-soft);
    margin-top: 4px;
    padding-top: 12px;
  }
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
