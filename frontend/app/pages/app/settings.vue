<script setup lang="ts">
definePageMeta({ middleware: "auth" })

type SocialConnection = {
  id: string
  status: string
  expires_at: string | null
  scopes: string[]
  metadata: Record<string, any>
  created_at: string
  updated_at: string
  provider?: {
    id: string
    code: string
    name: string
  }
}

type SocialAccount = {
  id: string
  display_name: string
  external_id: string
  provider_code: string
  provider_name: string
  channel_code: string
  channel_name: string
  account_type: string
  timezone: string
  status: string
  queue_slots?: QueueSlot[]
  created_at: string
}

type QueueSlot = {
  id?: string
  weekday: number
  local_time: string
  is_active: boolean
  position: number
}

type OAuthPage = {
  external_id: string
  display_name: string
  account_type: string
  timezone: string
  metadata: Record<string, any>
}

type ProviderCode = "facebook" | "instagram" | "linkedin" | "tiktok" | "youtube" | "pinterest"
type Step = "idle" | "authorizing" | "selecting"
type ProviderOption = {
  code: string
  label: string
  subtitle: string
  accent: string
  icon: string
  available: boolean
}

const session = useSessionState()
const route = useRoute()
const router = useRouter()
const { preference: themePreference, options: themeOptions, setPreference } = useThemePreference()

const callbackBaseUrl = ref(
  typeof window !== "undefined" ? `${window.location.origin}/app/settings` : "/app/settings"
)
const step = ref<Step>("idle")
const flowProvider = ref<ProviderCode | null>(null)
const availableAccounts = ref<OAuthPage[]>([])
const connecting = ref<string | null>(null)
const disconnecting = ref<string | null>(null)
const pendingDisconnectAccount = ref<SocialAccount | null>(null)
const callbackLock = ref("")
const providerModalOpen = ref(false)
const expandedQueueAccountId = ref<string | null>(null)
const platformFilter = computed(() => (route.query.platform as string) || "all")
const currentPage = computed(() => Math.max(1, parseInt((route.query.page as string) || "1", 10)))
const PAGE_SIZE = 20

function setFilter(platform: string) {
  router.replace({ query: { ...route.query, platform: platform === "all" ? undefined : platform, page: undefined } })
}

function setPage(page: number) {
  router.replace({ query: { ...route.query, page: page <= 1 ? undefined : String(page) } })
}
const savingQueueAccountId = ref<string | null>(null)
const draggingQueueSlot = ref<{ accountId: string; index: number } | null>(null)
const queueSlotDrafts = ref<Record<string, QueueSlot[]>>({})
const error = ref("")

const weekdayOptions = [
  { value: 0, label: "Mon" },
  { value: 1, label: "Tue" },
  { value: 2, label: "Wed" },
  { value: 3, label: "Thu" },
  { value: 4, label: "Fri" },
  { value: 5, label: "Sat" },
  { value: 6, label: "Sun" },
]

onMounted(() => {
  callbackBaseUrl.value = `${window.location.origin}/app/settings`
})

const { data: connections, refresh: refreshConnections } = useAsyncData(
  "settings-connections",
  () => apiFetch<SocialConnection[]>("/connections/"),
  { lazy: true, default: () => [] }
)

const { data: accounts, refresh: refreshAccounts } = useAsyncData(
  "settings-accounts",
  () => apiFetch<SocialAccount[]>("/accounts/"),
  { lazy: true, default: () => [] }
)

const facebookConnection = computed(() =>
  connections.value.find((item) => ["facebook", "meta"].includes(item.provider?.code || "")) || null
)
const instagramConnection = computed(() =>
  connections.value.find((item) => item.provider?.code === "instagram")
)
const facebookPagesCount = computed(() =>
  accounts.value.filter((item) => item.channel_code === "facebook").length
)
const instagramAccountsCount = computed(() =>
  accounts.value.filter((item) => item.channel_code === "instagram").length
)
const facebookConnectedIds = computed(() =>
  new Set(accounts.value.filter((item) => item.channel_code === "facebook").map((item) => item.external_id))
)
const instagramConnectedIds = computed(() =>
  new Set(accounts.value.filter((item) => item.channel_code === "instagram").map((item) => item.external_id))
)
const userName = computed(() =>
  [session.value.user?.first_name, session.value.user?.last_name].filter(Boolean).join(" ") || "Workspace user"
)
const workspaceName = computed(() => session.value.user?.workspace?.name || "Default workspace")
const workspaceTimezone = computed(() => session.value.user?.workspace?.timezone || "Asia/Saigon")
const flowProviderLabel = computed(() => {
  const labels: Record<string, string> = { instagram: "Instagram", facebook: "Facebook", linkedin: "LinkedIn", tiktok: "TikTok", youtube: "YouTube", pinterest: "Pinterest" }
  return labels[flowProvider.value || ""] || flowProvider.value || "Channel"
})
const linkedinConnectedIds = computed(() =>
  new Set(accounts.value.filter((a) => a.provider_code === "linkedin").map((a) => a.external_id))
)
const tiktokConnectedIds = computed(() =>
  new Set(accounts.value.filter((a) => a.provider_code === "tiktok").map((a) => a.external_id))
)
const youtubeConnectedIds = computed(() =>
  new Set(accounts.value.filter((a) => a.provider_code === "youtube").map((a) => a.external_id))
)
const pinterestConnectedIds = computed(() =>
  new Set(accounts.value.filter((a) => a.provider_code === "pinterest").map((a) => a.external_id))
)
const flowConnectedIds = computed(() => {
  if (flowProvider.value === "instagram") return instagramConnectedIds.value
  if (flowProvider.value === "linkedin") return linkedinConnectedIds.value
  if (flowProvider.value === "tiktok") return tiktokConnectedIds.value
  if (flowProvider.value === "youtube") return youtubeConnectedIds.value
  if (flowProvider.value === "pinterest") return pinterestConnectedIds.value
  return facebookConnectedIds.value
})
const providerOptions = computed<ProviderOption[]>(() => [
  { code: "instagram", label: "Instagram", subtitle: "Business or Creator", accent: "#e1306c", icon: "ig", available: true },
  { code: "threads", label: "Threads", subtitle: "Profile", accent: "#111111", icon: "@", available: false },
  { code: "linkedin", label: "LinkedIn", subtitle: "Page or Profile", accent: "#0a66c2", icon: "in", available: true },
  { code: "facebook", label: "Facebook", subtitle: "Page or Group", accent: "#1877f2", icon: "f", available: true },
  { code: "bluesky", label: "Bluesky", subtitle: "Profile", accent: "#1185fe", icon: "b", available: false },
  { code: "youtube", label: "YouTube", subtitle: "Channel", accent: "#ff0000", icon: "▶", available: true },
  { code: "tiktok", label: "TikTok", subtitle: "Creator Profile", accent: "#111111", icon: "tt", available: false },
  { code: "mastodon", label: "Mastodon", subtitle: "Profile", accent: "#6364ff", icon: "m", available: false },
  { code: "pinterest", label: "Pinterest", subtitle: "Board", accent: "#e60023", icon: "p", available: true },
])

function storedOAuthProvider() {
  if (typeof window === "undefined") return null
  const provider = window.sessionStorage.getItem("social_oauth_provider")
  const valid: ProviderCode[] = ["facebook", "instagram", "linkedin", "tiktok", "youtube", "pinterest"]
  return valid.includes(provider as ProviderCode) ? provider as ProviderCode : null
}

function storedOAuthState() {
  if (typeof window === "undefined") return ""
  return window.sessionStorage.getItem("social_oauth_state") || ""
}

function persistOAuthContext(providerCode: ProviderCode, state: string) {
  if (typeof window === "undefined") return
  window.sessionStorage.setItem("social_oauth_provider", providerCode)
  window.sessionStorage.setItem("social_oauth_state", state)
}

function clearOAuthContext() {
  if (typeof window === "undefined") return
  window.sessionStorage.removeItem("social_oauth_provider")
  window.sessionStorage.removeItem("social_oauth_state")
}

function providerFromConnections(state: string) {
  if (!state) return null
  const matched = connections.value.find((item) => item.metadata?.oauth_state === state)
  const code = matched?.provider?.code
  const validProviders: ProviderCode[] = ["facebook", "instagram", "linkedin", "tiktok", "youtube", "pinterest"]
  return validProviders.includes(code as ProviderCode) ? code as ProviderCode : null
}

watch(
  () => [route.query.code, route.query.provider, route.params.provider, route.query.state, connections.value.length],
  async ([codeValue, providerQueryValue, providerParamValue, stateValue]) => {
    const validProviders: ProviderCode[] = ["facebook", "instagram", "linkedin", "tiktok", "youtube", "pinterest"]
    const routeProvider =
      (validProviders.includes(providerQueryValue as ProviderCode) ? providerQueryValue as ProviderCode : null)
      || (validProviders.includes(providerParamValue as ProviderCode) ? providerParamValue as ProviderCode : null)
    const resolvedProvider =
      routeProvider
      || (typeof stateValue === "string" ? providerFromConnections(stateValue) : null)
      || storedOAuthProvider()
    if (typeof codeValue === "string" && codeValue && resolvedProvider) {
      const lockKey = `${resolvedProvider}:${codeValue}`
      if (callbackLock.value === lockKey) {
        return
      }
      callbackLock.value = lockKey
      await router.replace({ query: {} })
      await handleCallback(resolvedProvider, codeValue)
    }
  },
  { immediate: true }
)

const connectedAccounts = computed(() => {
  const facebook = accounts.value.filter((item) => item.channel_code === "facebook")
  const instagram = accounts.value.filter((item) => item.channel_code === "instagram")
  const linkedin = accounts.value.filter((item) => item.channel_code === "linkedin" || item.provider_code === "linkedin")
  const tiktok = accounts.value.filter((item) => item.channel_code === "tiktok" || item.provider_code === "tiktok")
  const youtube = accounts.value.filter((item) => item.channel_code === "youtube" || item.provider_code === "youtube")
  const pinterest = accounts.value.filter((item) => item.channel_code === "pinterest" || item.provider_code === "pinterest")
  return [...facebook, ...instagram, ...linkedin, ...tiktok, ...youtube, ...pinterest]
})

const availablePlatforms = computed(() => {
  const codes = new Set(accounts.value.map((a) => (a.channel_code || a.provider_code) as string))
  return [...codes].filter(Boolean)
})

const filteredAccounts = computed(() =>
  platformFilter.value === "all"
    ? connectedAccounts.value
    : connectedAccounts.value.filter((a) => (a.channel_code || a.provider_code) === platformFilter.value)
)

const totalPages = computed(() => Math.max(1, Math.ceil(filteredAccounts.value.length / PAGE_SIZE)))

const pagedAccounts = computed(() => {
  const page = Math.min(currentPage.value, totalPages.value)
  return filteredAccounts.value.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
})

function platformName(code: string) {
  const names: Record<string, string> = {
    facebook: "Facebook", instagram: "Instagram", tiktok: "TikTok",
    linkedin: "LinkedIn", youtube: "YouTube", pinterest: "Pinterest",
  }
  return names[code] ?? code
}

watch(
  accounts,
  (value) => {
    const next: Record<string, QueueSlot[]> = {}
    for (const account of value) {
      next[account.id] = (account.queue_slots || []).map((slot) => ({
        id: slot.id,
        weekday: slot.weekday,
        local_time: String(slot.local_time || "").slice(0, 5),
        is_active: !!slot.is_active,
        position: slot.position ?? 0,
      }))
    }
    queueSlotDrafts.value = next
    if (expandedQueueAccountId.value && !next[expandedQueueAccountId.value]) {
      expandedQueueAccountId.value = null
    }
  },
  { immediate: true }
)

function activeQueueSlots(account: SocialAccount) {
  return account.queue_slots?.filter((slot) => slot.is_active).length || 0
}

function queueSlotsFor(accountId: string) {
  return queueSlotDrafts.value[accountId] || []
}

function queueSlotKey(slot: QueueSlot) {
  return `${slot.weekday}-${normalizeQueueTime(slot.local_time)}`
}

function toggleQueueEditor(accountId: string) {
  expandedQueueAccountId.value = expandedQueueAccountId.value === accountId ? null : accountId
}

function addQueueSlot(accountId: string) {
  const list = [...queueSlotsFor(accountId)]
  list.push({
    id: `new-${Date.now()}-${list.length}`,
    weekday: list[list.length - 1]?.weekday ?? 0,
    local_time: list[list.length - 1]?.local_time || "09:00",
    is_active: true,
    position: list.length,
  })
  queueSlotDrafts.value = { ...queueSlotDrafts.value, [accountId]: list }
}

function removeQueueSlot(accountId: string, index: number) {
  const list = queueSlotsFor(accountId)
    .filter((_, currentIndex) => currentIndex !== index)
    .map((slot, position) => ({ ...slot, position }))
  queueSlotDrafts.value = { ...queueSlotDrafts.value, [accountId]: list }
}

function normalizeQueueTime(value: string) {
  if (!value) return "09:00:00"
  return value.length === 5 ? `${value}:00` : value
}

function hasDuplicateQueueSlots(accountId: string) {
  const seen = new Set<string>()
  for (const slot of queueSlotsFor(accountId)) {
    const key = queueSlotKey(slot)
    if (seen.has(key)) return true
    seen.add(key)
  }
  return false
}

function queueSlotDuplicateAt(accountId: string, index: number) {
  const slots = queueSlotsFor(accountId)
  const slot = slots[index]
  if (!slot) return false
  const key = queueSlotKey(slot)
  return slots.filter((candidate) => queueSlotKey(candidate) === key).length > 1
}

function startQueueSlotDrag(accountId: string, index: number) {
  draggingQueueSlot.value = { accountId, index }
}

function moveQueueSlot(accountId: string, fromIndex: number, toIndex: number) {
  if (fromIndex === toIndex) return
  const list = [...queueSlotsFor(accountId)]
  const [moved] = list.splice(fromIndex, 1)
  list.splice(toIndex, 0, moved)
  queueSlotDrafts.value = {
    ...queueSlotDrafts.value,
    [accountId]: list.map((slot, position) => ({ ...slot, position })),
  }
}

function dropQueueSlot(accountId: string, toIndex: number) {
  const dragging = draggingQueueSlot.value
  if (!dragging || dragging.accountId !== accountId) return
  moveQueueSlot(accountId, dragging.index, toIndex)
  draggingQueueSlot.value = null
}

function endQueueSlotDrag() {
  draggingQueueSlot.value = null
}

async function saveQueueSlots(account: SocialAccount) {
  savingQueueAccountId.value = account.id
  error.value = ""
  try {
    if (hasDuplicateQueueSlots(account.id)) {
      error.value = "Queue slots cannot share the same day and time."
      return
    }
    const draft = queueSlotsFor(account.id).map((slot, position) => ({
      ...slot,
      position,
      local_time: normalizeQueueTime(slot.local_time),
    }))
    const existingIds = new Set((account.queue_slots || []).map((slot) => slot.id).filter(Boolean))
    const retainedIds = new Set<string>()

    for (const slot of draft) {
      const payload = {
        weekday: Number(slot.weekday),
        local_time: slot.local_time,
        is_active: !!slot.is_active,
        position: slot.position,
      }
      if (slot.id && !String(slot.id).startsWith("new-")) {
        retainedIds.add(slot.id)
        await apiFetch(`/accounts/${account.id}/queue-slots/${slot.id}/`, {
          method: "PATCH",
          body: payload,
        })
      } else {
        await apiFetch(`/accounts/${account.id}/queue-slots/`, {
          method: "POST",
          body: payload,
        })
      }
    }

    for (const existingId of existingIds) {
      if (!retainedIds.has(existingId)) {
        await apiFetch(`/accounts/${account.id}/queue-slots/${existingId}/`, {
          method: "DELETE",
        })
      }
    }

    await refreshAccounts()
    await refreshNuxtData("sidebar-accounts")
  } catch (e: any) {
    error.value = extractApiError(e, "Failed to save queue slots")
  } finally {
    savingQueueAccountId.value = null
  }
}

function platformClass(accountType: string, providerCode?: string): string {
  if (providerCode && ["facebook", "instagram", "linkedin", "tiktok", "youtube", "pinterest"].includes(providerCode)) return providerCode
  if (accountType === "instagram_business") return "instagram"
  if (accountType === "tiktok_creator") return "tiktok"
  if (accountType === "youtube_channel") return "youtube"
  if (accountType === "personal") return "linkedin"
  if (accountType === "pinterest_board") return "pinterest"
  return "facebook"
}

function formatDate(value?: string | null) {
  if (!value) return "Not available"
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function connectionStatusLabel(status?: string) {
  if (status === "connected") return "Connected"
  if (status === "pending") return "Pending"
  if (status === "expired") return "Needs reconnect"
  return status || "Unknown"
}

function statusTone(status?: string) {
  if (status === "connected") return "success"
  if (status === "pending") return "amber"
  if (status === "expired") return "danger"
  return "muted"
}

function callbackUrlFor(providerCode: ProviderCode) {
  const pathProviders: ProviderCode[] = ["instagram", "tiktok", "youtube", "pinterest"]
  if (pathProviders.includes(providerCode)) {
    return `${callbackBaseUrl.value}/provider/${providerCode}`
  }
  return `${callbackBaseUrl.value}?provider=${providerCode}`
}

async function startConnect(providerCode: ProviderCode) {
  error.value = ""
  flowProvider.value = providerCode
  providerModalOpen.value = false
  try {
    const payload = await apiFetch<{ authorize_url: string; state: string }>(
      `/connections/${providerCode}/start/`,
      { method: "POST", body: { redirect_uri: callbackUrlFor(providerCode) } }
    )
    persistOAuthContext(providerCode, payload.state)
    if (payload.authorize_url.includes("mock=true")) {
      await handleCallback(providerCode, "demo-code")
      return
    }
    window.location.href = payload.authorize_url
  } catch (e: any) {
    error.value = extractApiError(e, "Failed to start OAuth")
  }
}

async function handleCallback(providerCode: ProviderCode, code: string) {
  step.value = "authorizing"
  flowProvider.value = providerCode
  error.value = ""
  try {
    const result = await apiFetch<{ connection: SocialConnection; accounts: OAuthPage[] }>(
      `/connections/${providerCode}/callback/`,
      { method: "POST", body: { code, redirect_uri: callbackUrlFor(providerCode) } }
    )
    availableAccounts.value = result.accounts
    step.value = "selecting"
    await refreshConnections()
    clearOAuthContext()
  } catch (e: any) {
    error.value = extractApiError(e, "OAuth failed")
    step.value = "idle"
  } finally {
    callbackLock.value = ""
  }
}

async function connectAccount(account: OAuthPage) {
  if (!flowProvider.value) return
  connecting.value = account.external_id
  error.value = ""
  try {
    await apiFetch(`/connections/${flowProvider.value}/connect-account/`, {
      method: "POST",
      body: { external_id: account.external_id },
    })
    await refreshAccounts()
    await refreshNuxtData("sidebar-accounts")
    await refreshConnections()
    // Auto-close flow if all available accounts are now connected
    const allConnected = availableAccounts.value.every((a) => flowConnectedIds.value.has(a.external_id))
    if (allConnected) {
      setTimeout(() => resetFlow(), 600)
    }
  } catch (e: any) {
    error.value = extractApiError(e, "Failed to connect page")
  } finally {
    connecting.value = null
  }
}

function requestDisconnect(account: SocialAccount) {
  pendingDisconnectAccount.value = account
}

function cancelDisconnect() {
  pendingDisconnectAccount.value = null
}

async function confirmDisconnect() {
  const account = pendingDisconnectAccount.value
  if (!account) return
  disconnecting.value = account.id
  pendingDisconnectAccount.value = null
  error.value = ""
  try {
    await apiFetch(`/accounts/${account.id}/`, { method: "DELETE" })
    await refreshAccounts()
    await refreshNuxtData("sidebar-accounts")
  } catch (e: any) {
    error.value = extractApiError(e, "Failed to disconnect")
  } finally {
    disconnecting.value = null
  }
}

function resetFlow() {
  step.value = "idle"
  flowProvider.value = null
  availableAccounts.value = []
  error.value = ""
}

function openProviderModal() {
  providerModalOpen.value = true
}

function closeProviderModal() {
  providerModalOpen.value = false
}

async function selectProvider(option: ProviderOption) {
  if (!option.available) return
  await startConnect(option.code as ProviderCode)
}
</script>

<template>
  <div class="settings-page">
    <section class="settings-shell">
      <header class="channels-header">
        <div class="channels-heading">
          <p class="settings-kicker">Settings</p>
          <h1>Workspace settings</h1>
          <p class="settings-subtitle">
            Manage appearance, connected channels, and the publishing setup your workspace uses day to day.
          </p>
        </div>
        <button class="btn connect-trigger" @click="openProviderModal">Connect channel</button>
      </header>

      <section class="settings-card appearance-card">
        <div class="appearance-copy">
          <p class="section-label">Appearance</p>
          <h2>Theme</h2>
          <p>Choose how the workspace should render for this browser.</p>
        </div>

        <div class="theme-options" aria-label="Theme preference">
          <button
            v-for="option in themeOptions"
            :key="option"
            type="button"
            class="theme-option"
            :class="{ active: themePreference === option }"
            @click="setPreference(option)"
          >
            {{ option }}
          </button>
        </div>
      </section>

      <section class="settings-card channels-card">
<p v-if="error" class="settings-error">{{ error }}</p>

        <div v-if="step === 'authorizing'" class="flow-panel">
          <strong>Authorizing {{ flowProviderLabel }}</strong>
          <span>Waiting for OAuth callback and token exchange.</span>
        </div>

        <div v-else-if="step === 'selecting'" class="flow-stack">
          <div class="flow-panel">
            <strong>Select {{ flowProviderLabel }} channels</strong>
            <span>Only the accounts you connect here will show up in Publish and Calendar.</span>
          </div>

          <div v-if="!availableAccounts.length" class="flow-panel">
            <strong>No {{ flowProviderLabel }} channels found</strong>
            <span>
              {{
                flowProvider === "instagram"
                  ? "Make sure the Instagram account is Professional and the app has the required Instagram scopes."
                  : flowProvider === "linkedin"
                    ? "Make sure the LinkedIn account has granted the required permissions."
                    : "Make sure the login you used has access to at least one Facebook Page."
              }}
            </span>
          </div>

          <article v-for="account in availableAccounts" :key="account.external_id" class="channel-row selectable">
            <div class="channel-leading">
              <div class="channel-avatar" :class="platformClass(account.account_type)">
                <PlatformIcon :platform="platformClass(account.account_type)" :size="22" />
              </div>
              <div class="channel-copy">
                <strong>{{ account.display_name }}</strong>
                <span>{{
                  account.account_type === "instagram_business" ? "Instagram account"
                  : account.account_type === "tiktok_creator" ? "TikTok Creator"
                  : account.account_type === "youtube_channel" ? "YouTube channel"
                  : account.account_type === "personal" ? "LinkedIn profile"
                  : "Facebook Page"
                }}</span>
                <small>{{ account.timezone }} · {{ account.external_id }}</small>
              </div>
            </div>

            <button
              v-if="flowConnectedIds.has(account.external_id)"
              class="btn secondary"
              disabled
            >
              Connected
            </button>
            <button
              v-else
              class="btn"
              :disabled="connecting === account.external_id"
              @click="connectAccount(account)"
            >
              {{ connecting === account.external_id ? "Connecting..." : "Connect" }}
            </button>
          </article>

          <button class="btn secondary settings-inline-btn" @click="resetFlow">Done</button>

          <div v-if="connectedAccounts.length" class="flow-existing">
            <p class="flow-existing-label">Already connected</p>
            <article v-for="account in connectedAccounts" :key="account.id" class="channel-row">
              <div class="channel-leading">
                <div class="channel-avatar" :class="platformClass(account.account_type, account.provider_code)">
                  <PlatformIcon :platform="platformClass(account.account_type, account.provider_code)" :size="22" />
                </div>
                <div class="channel-copy">
                  <strong>{{ account.display_name }}</strong>
                  <span>{{ account.channel_name }}</span>
                </div>
              </div>
              <span class="connected-badge">Connected</span>
            </article>
          </div>
        </div>

        <div v-else class="channels-section">
          <div class="channels-section-header">
            <div>
              <h2>Connected channels</h2>
              <p>{{ filteredAccounts.length }} / {{ connectedAccounts.length }} channels active in this workspace</p>
            </div>
            <div class="channel-filter-pills">
              <button
                class="filter-pill"
                :class="{ active: platformFilter === 'all' }"
                @click="setFilter('all')"
              >All</button>
              <button
                v-for="code in availablePlatforms"
                :key="code"
                class="filter-pill"
                :class="{ active: platformFilter === code }"
                @click="setFilter(code)"
              >
                <PlatformIcon :platform="code" :size="12" />
                {{ platformName(code) }}
              </button>
            </div>
          </div>

          <div v-if="!accounts.length" class="empty-state compact">
            <strong>No connected channels yet</strong>
            <p>Connect Facebook or Instagram, then choose the channels you want available for publishing.</p>
          </div>

          <div v-else class="channels-list">
            <template v-for="account in pagedAccounts" :key="account.id">
              <article class="channel-row">
                <div class="channel-leading">
                  <div class="channel-avatar" :class="platformClass(account.account_type, account.provider_code)">
                    <PlatformIcon :platform="platformClass(account.account_type, account.provider_code)" :size="22" />
                  </div>
                  <div class="channel-copy">
                    <strong>{{ account.display_name }}</strong>
                    <span>{{ account.channel_name }}</span>
                    <small>{{ account.timezone }} · {{ activeQueueSlots(account) }} queue slots</small>
                  </div>
                </div>

                <div class="channel-trailing">
                  <span class="channel-date">{{ formatDate(account.created_at) }}</span>
                  <button class="row-link" @click="toggleQueueEditor(account.id)">
                    {{ expandedQueueAccountId === account.id ? "Hide queue" : "Queue slots" }}
                  </button>
                  <NuxtLink class="row-link" :to="`/app/posts?account=${account.id}`">Open</NuxtLink>
                  <button
                    class="row-link danger"
                    :disabled="disconnecting === account.id"
                    @click="requestDisconnect(account)"
                  >
                    {{ disconnecting === account.id ? "Disconnecting..." : "Disconnect" }}
                  </button>
                </div>
              </article>

              <div v-if="expandedQueueAccountId === account.id" class="queue-slot-editor">
                <div class="queue-slot-head">
                  <div>
                    <p class="section-label">Queue Schedule</p>
                    <strong>{{ account.display_name }}</strong>
                  </div>
                  <span class="queue-slot-note">Queue uses these active day and time slots for auto-scheduling.</span>
                </div>

                <div v-if="queueSlotsFor(account.id).length" class="queue-slot-list">
                  <div
                    v-for="(slot, index) in queueSlotsFor(account.id)"
                    :key="slot.id || index"
                    class="queue-slot-row"
                    :class="{ duplicate: queueSlotDuplicateAt(account.id, index) }"
                    draggable="true"
                    @dragstart="startQueueSlotDrag(account.id, index)"
                    @dragover.prevent
                    @drop.prevent="dropQueueSlot(account.id, index)"
                    @dragend="endQueueSlotDrag"
                  >
                    <button class="queue-slot-drag" type="button" title="Drag to reorder">⋮⋮</button>
                    <select v-model.number="slot.weekday" class="queue-slot-input">
                      <option v-for="option in weekdayOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                    </select>
                    <input v-model="slot.local_time" class="queue-slot-input" type="time" />
                    <label class="queue-slot-toggle">
                      <input v-model="slot.is_active" type="checkbox" />
                      <span>Active</span>
                    </label>
                    <button class="row-link danger" @click="removeQueueSlot(account.id, index)">Remove</button>
                  </div>
                </div>
                <div v-else class="empty-state compact">
                  <strong>No queue slots yet</strong>
                  <p>Add at least one active slot if you want this channel to use Queue.</p>
                </div>
                <p v-if="hasDuplicateQueueSlots(account.id)" class="settings-error">Queue slots cannot share the same day and time.</p>

                <div class="queue-slot-actions">
                  <button class="row-link" @click="addQueueSlot(account.id)">Add slot</button>
                  <button class="btn" :disabled="savingQueueAccountId === account.id" @click="saveQueueSlots(account)">
                    {{ savingQueueAccountId === account.id ? "Saving..." : "Save queue slots" }}
                  </button>
                </div>
              </div>
            </template>
          </div>

          <div v-if="totalPages > 1" class="channels-pagination">
            <button
              class="page-btn"
              :disabled="currentPage <= 1"
              @click="setPage(currentPage - 1)"
            >←</button>
            <button
              v-for="p in totalPages"
              :key="p"
              class="page-btn"
              :class="{ active: p === currentPage }"
              @click="setPage(p)"
            >{{ p }}</button>
            <button
              class="page-btn"
              :disabled="currentPage >= totalPages"
              @click="setPage(currentPage + 1)"
            >→</button>
          </div>
        </div>
      </section>
    </section>

    <div v-if="providerModalOpen" class="provider-modal-shell" @click.self="closeProviderModal">
      <div class="provider-modal">
        <button class="provider-modal-close" @click="closeProviderModal">×</button>
        <div class="provider-modal-head">
          <strong>Connect a New Channel</strong>
          <span>Choose the network you want to connect to this workspace.</span>
        </div>

        <div class="provider-modal-grid">
          <button
            v-for="option in providerOptions"
            :key="option.code"
            class="provider-option"
            :class="{ disabled: !option.available }"
            :disabled="!option.available"
            @click="selectProvider(option)"
          >
            <span class="provider-option-icon" :style="{ background: option.accent }">{{ option.icon }}</span>
            <strong>{{ option.label }}</strong>
            <span>{{ option.subtitle }}</span>
            <small>{{ option.available ? "Available now" : "Coming soon" }}</small>
          </button>
        </div>
      </div>
    </div>

    <div v-if="pendingDisconnectAccount" class="confirm-overlay" @click.self="cancelDisconnect">
      <div class="confirm-modal">
        <p class="confirm-kicker">Confirm disconnect</p>
        <h3>Disconnect {{ pendingDisconnectAccount.display_name }}?</h3>
        <p class="confirm-copy">
          This channel will be removed from your workspace. Any scheduled posts targeting it will not be published.
        </p>
        <div class="confirm-actions">
          <button class="btn secondary" @click="cancelDisconnect">Cancel</button>
          <button class="btn danger" @click="confirmDisconnect">Disconnect</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  padding: 28px;
}

.settings-shell {
  max-width: 980px;
  margin: 0 auto;
  display: grid;
  gap: 20px;
}

.channels-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
}

.connect-trigger {
  min-width: 148px;
}

.appearance-card {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.channels-heading {
  display: grid;
  gap: 10px;
}

.settings-card {
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--panel);
  box-shadow: var(--shadow-panel);
}

.channels-card {
  padding: 24px;
  display: grid;
  gap: 20px;
}

.settings-kicker,
 .section-label {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}

.channels-header h1,
.appearance-copy h2,
.channels-section-header h2 {
  margin: 0;
  color: var(--ink);
  letter-spacing: -0.03em;
}

.channels-header h1 {
  font-size: 34px;
}

.settings-subtitle,
.appearance-copy p,
.flow-panel span,
.summary-badge span,
.channel-copy span,
.channel-copy small,
.channels-section-header p,
.empty-state p,
.channel-date {
  color: var(--muted);
}

.appearance-copy {
  display: grid;
  gap: 8px;
}

.theme-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.theme-option {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  text-transform: capitalize;
  cursor: pointer;
  box-shadow: var(--shadow-soft);
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease, box-shadow 0.14s ease, transform 0.14s ease;
}

.theme-option:hover {
  transform: translateY(-1px);
  border-color: var(--brand-outline);
  background: var(--surface-muted);
  box-shadow: var(--shadow-panel);
}

.theme-option.active {
  border-color: var(--action-border);
  background: linear-gradient(180deg, var(--action-fill-start) 0%, var(--action-fill-end) 100%);
  color: var(--action-ink);
}

.settings-subtitle {
  margin: 0;
  max-width: 620px;
  line-height: 1.6;
}

.summary-strip {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.summary-badge {
  min-width: 150px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid var(--line-soft);
  background: var(--surface-muted);
  display: grid;
  gap: 5px;
}

.summary-badge strong {
  color: var(--ink);
}

.flow-panel,
.channel-row {
  border: 1px solid var(--line-soft);
  border-radius: 16px;
  background: var(--surface);
}
.channel-leading,
.channel-trailing {
  display: flex;
  align-items: center;
  gap: 14px;
}
.channel-avatar {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: #1877f2;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.channel-avatar.instagram {
  background: linear-gradient(135deg, #f58529, #dd2a7b 58%, #515bd4);
}

.channel-avatar.linkedin {
  background: #0a66c2;
}

.channel-avatar.youtube {
  background: #ff0000;
}

.channel-avatar.pinterest {
  background: #e60023;
}

.channel-avatar.tiktok {
  background: #111111;
}

.settings-error {
  margin: 0;
  color: #a02e22;
  font-size: 14px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status-pill[data-tone="success"] {
  background: rgba(127, 162, 147, 0.18);
  color: var(--brand-strong);
}

.status-pill[data-tone="amber"] {
  background: rgba(230, 126, 34, 0.16);
  color: #ad5c16;
}

.status-pill[data-tone="danger"] {
  background: rgba(192, 57, 43, 0.14);
  color: #a02e22;
}

.status-pill[data-tone="muted"] {
  background: rgba(107, 118, 111, 0.16);
  color: #58625c;
}

.flow-panel {
  display: grid;
  gap: 6px;
  padding: 16px;
}

.flow-stack,
.channels-list {
  display: grid;
  gap: 12px;
}

.flow-existing {
  display: grid;
  gap: 8px;
  padding-top: 4px;
  border-top: 1px solid var(--line-soft);
}

.flow-existing-label {
  margin: 0;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
}

.connected-badge {
  font-size: 12px;
  font-weight: 600;
  color: var(--brand-strong);
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(127, 162, 147, 0.15);
}

.channels-section {
  display: grid;
  gap: 14px;
}

.channels-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.channels-section-header p {
  margin: 4px 0 0;
}

.channel-filter-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  padding-top: 4px;
}

.filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid var(--line);
  font-size: 12px;
  font-weight: 600;
  background: var(--surface);
  color: var(--muted);
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s, color 0.12s;
}

.filter-pill:hover {
  border-color: var(--brand-outline);
  background: var(--surface-muted);
}

.filter-pill.active {
  background: linear-gradient(180deg, var(--action-fill-start) 0%, var(--action-fill-end) 100%);
  color: var(--action-ink);
  border-color: var(--action-border);
}

.channels-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding-top: 4px;
}

.page-btn {
  min-width: 34px;
  height: 34px;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--muted);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s, color 0.12s;
}

.page-btn:hover:not(:disabled) {
  border-color: var(--brand-outline);
  background: var(--surface-muted);
}

.page-btn.active {
  background: linear-gradient(180deg, var(--action-fill-start) 0%, var(--action-fill-end) 100%);
  color: var(--action-ink);
  border-color: var(--action-border);
}

.page-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.channel-row {
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.channel-row.selectable {
  background: var(--surface);
}

.channel-copy {
  display: grid;
  gap: 3px;
}

.channel-copy strong,
.flow-panel strong {
  color: var(--ink);
}

.channel-date {
  font-size: 13px;
}

.row-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--control-bg);
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
  box-shadow: var(--shadow-soft);
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease, box-shadow 0.14s ease, transform 0.14s ease;
}

.row-link:hover {
  transform: translateY(-1px);
  border-color: var(--brand-outline);
  background: var(--control-bg-hover);
  box-shadow: var(--shadow-panel);
}

.row-link.danger {
  border-color: rgba(138, 39, 28, 0.28);
  background: rgba(160, 46, 34, 0.08);
  color: var(--danger-fill);
}

.queue-slot-editor {
  margin: -2px 0 4px;
  padding: 16px;
  border: 1px solid var(--line-soft);
  border-radius: 16px;
  background: var(--surface-muted);
  display: grid;
  gap: 14px;
}

.queue-slot-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.queue-slot-head strong,
.queue-slot-note {
  color: var(--ink);
}

.queue-slot-note {
  max-width: 340px;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.5;
}

.queue-slot-list {
  display: grid;
  gap: 10px;
}

.queue-slot-row {
  display: grid;
  grid-template-columns: 38px 110px 130px 90px auto;
  gap: 10px;
  align-items: center;
}

.queue-slot-row.duplicate {
  border: 1px solid rgba(160, 46, 34, 0.18);
  border-radius: 12px;
  padding: 8px;
  background: rgba(160, 46, 34, 0.04);
}

.queue-slot-drag {
  min-height: 38px;
  border-radius: 10px;
  border: 1px dashed var(--line);
  background: var(--control-bg);
  color: var(--muted);
  cursor: grab;
  font-size: 14px;
  letter-spacing: 1px;
}

.queue-slot-drag:active {
  cursor: grabbing;
}

.queue-slot-input {
  min-height: 38px;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--input-bg);
  color: var(--ink);
}

.queue-slot-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ink);
}

.queue-slot-actions {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.provider-modal-shell {
  position: fixed;
  inset: 0;
  background: rgba(29, 24, 18, 0.52);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 40;
}

.provider-modal {
  width: min(760px, 100%);
  max-height: min(80vh, 760px);
  overflow: auto;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 22px;
  box-shadow: var(--shadow-strong);
  padding: 24px;
  position: relative;
  display: grid;
  gap: 20px;
}

.provider-modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--control-bg);
  color: var(--ink);
  font-size: 20px;
  line-height: 1;
  box-shadow: var(--shadow-soft);
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease, box-shadow 0.14s ease, transform 0.14s ease;
}

.provider-modal-close:hover {
  transform: translateY(-1px);
  border-color: var(--brand-outline);
  background: var(--control-bg-hover);
  box-shadow: var(--shadow-panel);
}

.provider-modal-head {
  display: grid;
  gap: 6px;
  justify-items: center;
  text-align: center;
  padding-top: 12px;
}

.provider-modal-head strong {
  color: var(--ink);
  font-size: 22px;
  letter-spacing: -0.02em;
}

.provider-modal-head span,
.provider-option span,
.provider-option small {
  color: var(--muted);
}

.provider-modal-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.provider-option {
  border: 1px solid var(--line-soft);
  border-radius: 16px;
  background: var(--surface);
  min-height: 144px;
  padding: 18px 16px;
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 8px;
  text-align: center;
  transition:
    transform 0.14s ease,
    box-shadow 0.14s ease,
    border-color 0.14s ease;
}

.provider-option:hover:not(.disabled) {
  transform: translateY(-2px);
  border-color: var(--brand-outline);
  box-shadow: var(--shadow-panel);
}

.provider-option.disabled {
  opacity: 0.62;
}

.provider-option-icon {
  width: 36px;
  height: 36px;
  border-radius: 11px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 13px;
  text-transform: lowercase;
}

.provider-option strong {
  color: var(--ink);
}

.settings-inline-btn {
  width: fit-content;
}

.empty-state.compact {
  padding: 4px 0;
}

.empty-state {
  display: grid;
  gap: 8px;
}

@media (max-width: 960px) {
  .settings-page {
    padding: 20px;
  }

  .channels-header,
  .channel-row,
  .channel-trailing,
  .queue-slot-head,
  .queue-slot-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .provider-modal-grid {
    grid-template-columns: 1fr;
  }

  .queue-slot-row {
    grid-template-columns: 1fr;
  }
}

.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(16, 30, 25, 0.3);
  backdrop-filter: blur(6px);
}

.confirm-modal {
  width: min(460px, 100%);
  display: grid;
  gap: 14px;
  padding: 24px;
  border-radius: 24px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-strong);
}

.confirm-kicker {
  margin: 0;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}

.confirm-modal h3 {
  margin: 0;
  font-size: 22px;
  letter-spacing: -0.02em;
}

.confirm-copy {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--muted);
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn.danger {
  background: rgba(160, 46, 34, 0.1);
  color: #a02e22;
  border-color: rgba(160, 46, 34, 0.2);
}

.btn.danger:hover {
  background: rgba(160, 46, 34, 0.16);
}
</style>
