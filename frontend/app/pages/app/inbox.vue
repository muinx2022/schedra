<script setup lang="ts">
definePageMeta({ middleware: "auth" })

type ThreadListItem = {
  id: string
  account_id: string
  account_name: string
  platform: string
  triage_status: string
  message_count: number
  last_message_at: string | null
  external_object_id: string
  related_post_id: string | null
}

type ThreadMessage = {
  id: string
  external_id: string
  parent_external_id: string
  parent_message: string | null
  author_name: string
  author_external_id: string
  body_text: string
  direction: string
  published_at: string
  metadata: Record<string, any>
}

type ThreadDetail = {
  id: string
  account_id: string
  account_name: string
  platform: string
  triage_status: string
  last_message_at: string | null
  last_synced_at: string | null
  external_object_id: string
  related_post_id: string | null
  messages: ThreadMessage[]
}

type AccountOption = {
  id: string
  display_name: string
  provider_code: string
  channel_code?: string
}

const route = useRoute()
const router = useRouter()
const sidebarAccounts = useNuxtData<AccountOption[]>("sidebar-accounts")

const statusOptions = ["all", "new", "reviewing", "resolved", "ignored"] as const
const syncPending = ref(false)
const syncMessage = ref("")
const triagePending = ref<string | null>(null)

const selectedStatus = computed(() => {
  const value = route.query.status
  return typeof value === "string" && statusOptions.includes(value as typeof statusOptions[number])
    ? value
    : "all"
})

const selectedPlatform = computed(() => {
  const value = route.query.platform
  return typeof value === "string" ? value : "all"
})

const selectedAccountId = computed(() => {
  const value = route.query.account
  return typeof value === "string" ? value : ""
})

const selectedThreadId = computed(() => {
  const value = route.query.thread
  return typeof value === "string" ? value : ""
})

const threadListPath = computed(() => {
  const params = new URLSearchParams()
  if (selectedStatus.value !== "all") params.set("status", selectedStatus.value)
  if (selectedPlatform.value !== "all") params.set("platform", selectedPlatform.value)
  if (selectedAccountId.value) params.set("account", selectedAccountId.value)
  const query = params.toString()
  return query ? `/inbox/threads/?${query}` : "/inbox/threads/"
})

const { data: threads, pending, error, refresh: refreshThreads } = useAsyncData(
  "inbox-threads",
  () => apiFetch<ThreadListItem[]>(threadListPath.value),
  {
    default: () => [],
    watch: [threadListPath],
    server: false,
  }
)

const detailPath = computed(() => selectedThreadId.value ? `/inbox/threads/${selectedThreadId.value}/` : "")

const { data: threadDetail, refresh: refreshThreadDetail } = useAsyncData(
  "inbox-thread-detail",
  () => selectedThreadId.value ? apiFetch<ThreadDetail>(detailPath.value) : Promise.resolve(null),
  {
    default: () => null,
    watch: [detailPath],
    server: false,
  }
)

const accountOptions = computed(() =>
  (sidebarAccounts.data.value || []).map((item) => ({
    id: item.id,
    label: item.display_name,
    platform: platformName(item.channel_code || item.provider_code),
  }))
)

const platformOptions = computed(() => {
  const set = new Set<string>()
  for (const item of sidebarAccounts.data.value || []) {
    set.add(item.channel_code || item.provider_code)
  }
  for (const item of threads.value) {
    set.add(item.platform)
  }
  return ["all", ...[...set].filter(Boolean)]
})

const detailMessages = computed(() => {
  const messages = threadDetail.value?.messages || []
  const byId = new Map(messages.map((item) => [item.id, item]))
  const externalToId = new Map(messages.map((item) => [item.external_id, item.id]))
  return messages.map((message) => {
    let depth = 0
    let currentParentId = message.parent_message || externalToId.get(message.parent_external_id) || null
    const visited = new Set<string>()
    while (currentParentId && !visited.has(currentParentId) && depth < 4) {
      visited.add(currentParentId)
      const parent = byId.get(currentParentId)
      if (!parent) break
      depth += 1
      currentParentId = parent.parent_message || externalToId.get(parent.parent_external_id) || null
    }
    return { ...message, depth }
  })
})

watch(
  threads,
  (items) => {
    if (!items.length) {
      if (selectedThreadId.value) router.replace({ query: { ...route.query, thread: undefined } })
      return
    }
    if (!selectedThreadId.value || !items.some((item) => item.id === selectedThreadId.value)) {
      router.replace({ query: { ...route.query, thread: items[0].id } })
    }
  },
  { immediate: true }
)

function updateQuery(patch: Record<string, string | undefined>) {
  router.replace({ query: { ...route.query, ...patch } })
}

function setStatus(value: string) {
  updateQuery({ status: value === "all" ? undefined : value, thread: undefined })
}

function setPlatform(value: string) {
  updateQuery({ platform: value === "all" ? undefined : value, thread: undefined })
}

function setAccount(value: string) {
  updateQuery({ account: value || undefined, thread: undefined })
}

function openThread(threadId: string) {
  updateQuery({ thread: threadId })
}

function formatDateTime(value?: string | null) {
  if (!value) return "No activity yet"
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function relativeTime(value?: string | null) {
  if (!value) return "No activity yet"
  const diff = Date.now() - new Date(value).getTime()
  const minutes = Math.max(0, Math.floor(diff / 60000))
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function platformName(code?: string) {
  const names: Record<string, string> = {
    all: "All platforms",
    facebook: "Facebook",
    instagram: "Instagram",
    linkedin: "LinkedIn",
    tiktok: "TikTok",
    youtube: "YouTube",
    pinterest: "Pinterest",
  }
  return names[code || ""] ?? code ?? "Platform"
}

function triageLabel(status: string) {
  const labels: Record<string, string> = {
    new: "New",
    reviewing: "Reviewing",
    resolved: "Resolved",
    ignored: "Ignored",
  }
  return labels[status] ?? status
}

function providerBadge(code: string) {
  const labels: Record<string, string> = {
    facebook: "FB",
    instagram: "IG",
    linkedin: "LI",
    tiktok: "TT",
    youtube: "YT",
    pinterest: "PT",
  }
  return labels[code] ?? (code || "?").slice(0, 2).toUpperCase()
}

async function queueSync() {
  syncPending.value = true
  syncMessage.value = ""
  try {
    await apiFetch("/inbox/sync/", {
      method: "POST",
      body: selectedAccountId.value ? { account: selectedAccountId.value } : {},
    })
    syncMessage.value = "Inbox refresh queued. Background workers will pull new comments."
    await refreshThreads()
    if (selectedThreadId.value) await refreshThreadDetail()
  } catch (syncError) {
    syncMessage.value = extractApiError(syncError, "Could not queue inbox refresh.")
  } finally {
    syncPending.value = false
  }
}

async function updateTriageStatus(nextStatus: string) {
  if (!threadDetail.value) return
  triagePending.value = nextStatus
  try {
    const updated = await apiFetch<ThreadDetail>(`/inbox/threads/${threadDetail.value.id}/`, {
      method: "PATCH",
      body: { triage_status: nextStatus },
    })
    threadDetail.value = updated
    await refreshThreads()
  } catch (triageError) {
    syncMessage.value = extractApiError(triageError, "Could not update triage status.")
  } finally {
    triagePending.value = null
  }
}
</script>

<template>
  <div class="inbox-page">
    <section class="inbox-shell">
      <header class="inbox-header">
        <div class="inbox-header-copy">
          <p class="inbox-kicker">Inbox</p>
          <h1>Comment triage</h1>
          <p class="inbox-subtitle">
            Review synced comments from app-published content, filter by channel, and move threads through triage.
          </p>
        </div>

        <div class="inbox-header-actions">
          <button class="sync-button" type="button" :disabled="syncPending" @click="queueSync">
            {{ syncPending ? "Queueing..." : "Refresh inbox" }}
          </button>
        </div>
      </header>

      <p v-if="error" class="inbox-error">{{ extractApiError(error, "Could not load inbox.") }}</p>
      <p v-if="syncMessage" class="inbox-note">{{ syncMessage }}</p>

      <section class="inbox-filters">
        <label class="filter-field">
          <span>Status</span>
          <select :value="selectedStatus" @change="setStatus(($event.target as HTMLSelectElement).value)">
            <option v-for="option in statusOptions" :key="option" :value="option">
              {{ option === "all" ? "All statuses" : triageLabel(option) }}
            </option>
          </select>
        </label>

        <label class="filter-field">
          <span>Platform</span>
          <select :value="selectedPlatform" @change="setPlatform(($event.target as HTMLSelectElement).value)">
            <option v-for="option in platformOptions" :key="option" :value="option">
              {{ platformName(option) }}
            </option>
          </select>
        </label>

        <label class="filter-field">
          <span>Channel</span>
          <select :value="selectedAccountId" @change="setAccount(($event.target as HTMLSelectElement).value)">
            <option value="">All channels</option>
            <option v-for="option in accountOptions" :key="option.id" :value="option.id">
              {{ option.label }} - {{ option.platform }}
            </option>
          </select>
        </label>
      </section>

      <section class="inbox-layout">
        <aside class="inbox-list-card">
          <div class="panel-head">
            <div>
              <p class="section-label">Threads</p>
              <h2>{{ threads.length }} active</h2>
            </div>
          </div>

          <div v-if="pending" class="empty-state">Loading inbox...</div>
          <div v-else-if="!threads.length" class="empty-state">
            No synced comment threads match this filter yet.
          </div>
          <div v-else class="thread-list">
            <button
              v-for="thread in threads"
              :key="thread.id"
              class="thread-row"
              :class="{ active: thread.id === selectedThreadId }"
              type="button"
              @click="openThread(thread.id)"
            >
              <div class="thread-row-main">
                <div class="thread-badge">{{ providerBadge(thread.platform) }}</div>
                <div class="thread-copy">
                  <strong>{{ thread.account_name }}</strong>
                  <p>{{ thread.message_count }} messages - {{ triageLabel(thread.triage_status) }}</p>
                </div>
              </div>
              <small>{{ relativeTime(thread.last_message_at) }}</small>
            </button>
          </div>
        </aside>

        <article class="inbox-detail-card">
          <div v-if="!threadDetail" class="empty-state">
            Select a thread to review synced comments.
          </div>
          <template v-else>
            <div class="panel-head detail-head">
              <div>
                <p class="section-label">Thread</p>
                <h2>{{ threadDetail.account_name }}</h2>
                <p class="detail-meta">
                  {{ platformName(threadDetail.platform) }} - synced {{ formatDateTime(threadDetail.last_synced_at) }}
                </p>
              </div>

              <div class="detail-actions">
                <NuxtLink
                  v-if="threadDetail.related_post_id"
                  class="post-link"
                  :to="`/app/posts?post=${threadDetail.related_post_id}`"
                >
                  Open post
                </NuxtLink>

                <label class="filter-field compact-field">
                  <span>Triage</span>
                  <select
                    :value="threadDetail.triage_status"
                    :disabled="!!triagePending"
                    @change="updateTriageStatus(($event.target as HTMLSelectElement).value)"
                  >
                    <option value="new">New</option>
                    <option value="reviewing">Reviewing</option>
                    <option value="resolved">Resolved</option>
                    <option value="ignored">Ignored</option>
                  </select>
                </label>
              </div>
            </div>

            <div class="detail-summary">
              <div class="summary-pill">
                <span>Status</span>
                <strong>{{ triageLabel(threadDetail.triage_status) }}</strong>
              </div>
              <div class="summary-pill">
                <span>Last message</span>
                <strong>{{ formatDateTime(threadDetail.last_message_at) }}</strong>
              </div>
              <div class="summary-pill">
                <span>Provider object</span>
                <strong>{{ threadDetail.external_object_id }}</strong>
              </div>
            </div>

            <div v-if="!detailMessages.length" class="empty-state">
              This thread has no synced comments yet.
            </div>
            <div v-else class="message-list">
              <article
                v-for="message in detailMessages"
                :key="message.id"
                class="message-card"
                :style="{ marginLeft: `${message.depth * 20}px` }"
              >
                <div class="message-head">
                  <strong>{{ message.author_name }}</strong>
                  <small>{{ formatDateTime(message.published_at) }}</small>
                </div>
                <p>{{ message.body_text || "No text content." }}</p>
              </article>
            </div>
          </template>
        </article>
      </section>
    </section>
  </div>
</template>

<style scoped>
.inbox-page {
  padding: 28px;
}

.inbox-shell {
  max-width: 1240px;
  margin: 0 auto;
  display: grid;
  gap: 20px;
}

.inbox-header,
.inbox-list-card,
.inbox-detail-card {
  border: 1px solid var(--line-soft);
  border-radius: 20px;
  background: var(--panel);
  box-shadow: var(--shadow-panel);
}

.inbox-header {
  padding: 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.inbox-header-copy,
.panel-head,
.filter-field,
.detail-actions {
  display: grid;
  gap: 8px;
}

.inbox-kicker,
.section-label {
  margin: 0;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}

.inbox-header h1,
.panel-head h2 {
  margin: 0;
  color: var(--ink);
}

.inbox-subtitle,
.thread-copy p,
.detail-meta,
.inbox-note,
.filter-field span,
.empty-state,
.message-head small {
  color: var(--muted);
}

.sync-button,
.post-link {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--surface-muted);
  color: var(--ink);
  font-weight: 700;
}

.sync-button:disabled {
  opacity: 0.65;
  cursor: wait;
}

.inbox-error {
  margin: 0;
  color: #a02e22;
}

.inbox-note {
  margin: 0;
}

.inbox-filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.filter-field select {
  min-height: 40px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: var(--input-bg);
  color: var(--ink);
}

.inbox-layout {
  display: grid;
  grid-template-columns: minmax(320px, 0.95fr) minmax(0, 1.45fr);
  gap: 18px;
  align-items: start;
}

.inbox-list-card,
.inbox-detail-card {
  padding: 22px;
}

.detail-head {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
}

.thread-list,
.message-list {
  display: grid;
  gap: 12px;
}

.thread-row {
  width: 100%;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  background: var(--surface-muted);
  color: var(--ink);
  display: grid;
  gap: 10px;
  text-align: left;
}

.thread-row.active {
  border-color: rgba(90, 121, 107, 0.48);
  box-shadow: var(--shadow-soft);
}

.thread-row-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.thread-copy {
  min-width: 0;
}

.thread-copy strong,
.message-head strong,
.summary-pill strong {
  color: var(--ink);
}

.thread-badge {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: linear-gradient(180deg, #6f8c80, #7fa293);
  color: #fff8ec;
  font-size: 12px;
  font-weight: 900;
  flex-shrink: 0;
}

.empty-state {
  padding: 18px;
  border-radius: 18px;
  border: 1px dashed rgba(19, 38, 27, 0.12);
  background: var(--surface-muted);
}

.detail-summary {
  margin: 18px 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.summary-pill {
  padding: 14px;
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  background: var(--surface-muted);
  display: grid;
  gap: 6px;
}

.summary-pill span {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.message-card {
  padding: 16px;
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  background: var(--surface-muted);
}

.message-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.message-card p {
  margin: 0;
  color: var(--ink);
  line-height: 1.55;
}

.compact-field {
  min-width: 180px;
}

@media (max-width: 980px) {
  .inbox-filters,
  .inbox-layout,
  .detail-summary,
  .detail-head {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .inbox-page {
    padding: 20px;
  }

  .inbox-header {
    flex-direction: column;
  }
}
</style>
