<script setup lang="ts">
definePageMeta({ middleware: "auth" })
const localePath = useLocalePath()
const intlLocale = useIntlLocale()
const { t } = useI18n()

type InteractionCapabilities = {
  inbox_comments: boolean
  reply_comments: boolean
}

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
  interaction_capabilities: InteractionCapabilities
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
  interaction_capabilities: InteractionCapabilities
  messages: ThreadMessage[]
}

type AccountOption = {
  id: string
  display_name: string
  provider_code: string
  channel_code?: string
  interaction_capabilities?: InteractionCapabilities
}

const route = useRoute()
const router = useRouter()
const sidebarAccounts = useNuxtData<AccountOption[]>("sidebar-accounts")

const statusOptions = ["all", "new", "reviewing", "resolved", "ignored"] as const
const syncPending = ref(false)
const syncMessage = ref("")
const triagePending = ref<string | null>(null)
const replyPending = ref(false)
const replyError = ref("")
const replyBody = ref("")
const replyTargetId = ref("")

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

const supportedSidebarAccounts = computed(() =>
  (sidebarAccounts.data.value || []).filter((item) => item.interaction_capabilities?.inbox_comments)
)

const accountOptions = computed(() =>
  supportedSidebarAccounts.value.map((item) => ({
    id: item.id,
    label: item.display_name,
    platform: platformName(item.channel_code || item.provider_code),
  }))
)

const hasInteractiveAccounts = computed(() => supportedSidebarAccounts.value.length > 0)

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

const platformOptions = computed(() => {
  const set = new Set<string>()
  for (const item of supportedSidebarAccounts.value) {
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

const selectedReplyTarget = computed(() =>
  detailMessages.value.find((message) => message.id === replyTargetId.value) || null
)

const canReplyToThread = computed(() => !!threadDetail.value?.interaction_capabilities?.reply_comments)

const queueSummary = computed(() => {
  const items = threads.value
  return {
    active: items.length,
    newCount: items.filter((item) => item.triage_status === "new").length,
    reviewingCount: items.filter((item) => item.triage_status === "reviewing").length,
    resolvedCount: items.filter((item) => item.triage_status === "resolved").length,
    replyEnabledCount: items.filter((item) => item.interaction_capabilities?.reply_comments).length,
  }
})

const scopeLabel = computed(() => {
  const parts = [selectedPlatform.value === "all" ? "All platforms" : platformName(selectedPlatform.value)]
  if (selectedAccountId.value) {
    const account = accountOptions.value.find((item) => item.id === selectedAccountId.value)
    if (account) parts.push(account.label)
  } else {
    parts.push("All channels")
  }
  return parts.join(" - ")
})

const selectedThreadPosition = computed(() => {
  const index = threads.value.findIndex((item) => item.id === selectedThreadId.value)
  return index >= 0 ? index + 1 : 0
})

const inboundMessageCount = computed(() =>
  detailMessages.value.filter((message) => message.direction === "inbound").length
)

const outboundMessageCount = computed(() =>
  detailMessages.value.filter((message) => message.direction === "outbound").length
)

const replyTargetPreview = computed(() =>
  truncateText(selectedReplyTarget.value?.body_text || "No text content.", 180)
)

watch(
  [supportedSidebarAccounts, platformOptions],
  ([accounts, platforms]) => {
    const accountIds = new Set(accounts.map((item) => item.id))
    const validPlatforms = new Set(platforms)
    const patch: Record<string, string | undefined> = {}
    if (selectedAccountId.value && !accountIds.has(selectedAccountId.value)) {
      patch.account = undefined
      patch.thread = undefined
    }
    if (selectedPlatform.value !== "all" && !validPlatforms.has(selectedPlatform.value)) {
      patch.platform = undefined
      patch.thread = undefined
    }
    if (Object.keys(patch).length) {
      updateQuery(patch)
    }
  },
  { immediate: true }
)

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

watch(
  () => threadDetail.value?.id,
  () => {
    replyTargetId.value = ""
    replyBody.value = ""
    replyError.value = ""
  }
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
  if (!value) return t("inbox.time.no_activity")
  return new Date(value).toLocaleString(intlLocale.value, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function relativeTime(value?: string | null) {
  if (!value) return t("inbox.time.no_activity")
  const diff = Date.now() - new Date(value).getTime()
  const minutes = Math.max(0, Math.floor(diff / 60000))
  if (minutes < 1) return t("inbox.time.just_now")
  if (minutes < 60) return t("inbox.time.minutes_ago", { count: minutes })
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return t("inbox.time.hours_ago", { count: hours })
  const days = Math.floor(hours / 24)
  return t("inbox.time.days_ago", { count: days })
}

function platformName(code?: string) {
  const names: Record<string, string> = {
    facebook: "Facebook",
    instagram: "Instagram",
    linkedin: "LinkedIn",
    tiktok: "TikTok",
    youtube: "YouTube",
    pinterest: "Pinterest",
  }
  return names[code || ""] ?? code ?? t("inbox.filters.platform_fallback")
}

function triageLabel(status: string) {
  const labels: Record<string, string> = {
    new: t("inbox.triage.new"),
    reviewing: t("inbox.triage.reviewing"),
    resolved: t("inbox.triage.resolved"),
    ignored: t("inbox.triage.ignored"),
  }
  return labels[status] ?? status
}

function triageTone(status: string) {
  const tones: Record<string, string> = {
    new: "danger",
    reviewing: "amber",
    resolved: "success",
    ignored: "muted",
  }
  return tones[status] ?? "muted"
}

function directionLabel(direction: string) {
  return direction === "outbound" ? t("inbox.direction.reply") : t("inbox.direction.comment")
}

function platformClass(code?: string) {
  const value = (code || "").toLowerCase()
  return ["facebook", "instagram", "linkedin", "tiktok", "youtube", "pinterest"].includes(value)
    ? value
    : "generic"
}

function truncateText(value: string, max = 120) {
  const normalized = value.replace(/\s+/g, " ").trim()
  if (normalized.length <= max) return normalized
  return `${normalized.slice(0, max - 3)}...`
}

function compactExternalId(value?: string | null) {
  if (!value) return t("common.not_available")
  if (value.length <= 18) return value
  return `${value.slice(0, 8)}...${value.slice(-6)}`
}

function startReply(message: ThreadMessage) {
  if (message.direction !== "inbound") return
  replyTargetId.value = message.id
  replyError.value = ""
}

function cancelReply() {
  replyTargetId.value = ""
  replyBody.value = ""
  replyError.value = ""
}

async function queueSync() {
  if (!hasInteractiveAccounts.value) return
  syncPending.value = true
  syncMessage.value = ""
  try {
    await apiFetch("/inbox/sync/", {
      method: "POST",
      body: selectedAccountId.value ? { account: selectedAccountId.value } : {},
    })
    syncMessage.value = t("inbox.sync.queued")
    await refreshThreads()
    if (selectedThreadId.value) await refreshThreadDetail()
  } catch (syncError) {
    syncMessage.value = extractApiError(syncError, t("inbox.sync.queue_failed"))
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
    syncMessage.value = extractApiError(triageError, t("inbox.triage.update_failed"))
  } finally {
    triagePending.value = null
  }
}

async function sendReply() {
  if (!threadDetail.value || !replyTargetId.value || !replyBody.value.trim()) return
  replyPending.value = true
  replyError.value = ""
  try {
    const updated = await apiFetch<ThreadDetail>(`/inbox/threads/${threadDetail.value.id}/reply/`, {
      method: "POST",
      body: {
        parent_message_id: replyTargetId.value,
        body_text: replyBody.value.trim(),
      },
    })
    threadDetail.value = updated
    replyBody.value = ""
    replyTargetId.value = ""
    await refreshThreads()
  } catch (replyRequestError) {
    replyError.value = extractApiError(replyRequestError, t("inbox.errors.send_reply_failed"))
  } finally {
    replyPending.value = false
  }
}
</script>

<template>
  <div class="inbox-page">
    <section class="inbox-shell">
      <header class="mb-1 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div class="space-y-1">
          <p class="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--brand)]">{{ t("inbox.kicker") }}</p>
          <h1 class="m-0 text-3xl font-semibold tracking-tight text-[var(--ink)] md:text-4xl">{{ t("inbox.title") }}</h1>
          <p class="max-w-3xl text-sm leading-6 text-[var(--muted)]">
            {{ t("inbox.subtitle") }}
          </p>
        </div>

        <div class="inbox-header-actions">
          <button class="sync-button" type="button" :disabled="syncPending || !hasInteractiveAccounts" @click="queueSync">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M20 12a8 8 0 0 0-14.74-4H8m-4 0V4m0 4h4m-4 4a8 8 0 0 0 14.74 4H16m4 0v4m0-4h-4"
                fill="none"
                stroke="currentColor"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.8"
              />
            </svg>
            {{ syncPending ? t("inbox.queueing") : t("inbox.refresh") }}
          </button>
        </div>
      </header>

      <section class="inbox-overview-card">
        <div class="inbox-overview">
          <div class="overview-metric overview-metric-primary">
            <span>{{ t("inbox.overview.current_queue") }}</span>
            <strong>{{ queueSummary.active }}</strong>
            <p>{{ scopeLabel }}</p>
          </div>
          <div class="overview-metric" data-tone="danger">
            <span>{{ t("inbox.overview.new") }}</span>
            <strong>{{ queueSummary.newCount }}</strong>
            <p>{{ t("inbox.overview.needs_first_review") }}</p>
          </div>
          <div class="overview-metric" data-tone="amber">
            <span>{{ t("inbox.overview.reviewing") }}</span>
            <strong>{{ queueSummary.reviewingCount }}</strong>
            <p>{{ t("inbox.overview.in_active_triage") }}</p>
          </div>
          <div class="overview-metric" data-tone="success">
            <span>{{ t("inbox.overview.resolved") }}</span>
            <strong>{{ queueSummary.resolvedCount }}</strong>
            <p>{{ t("inbox.overview.closed_in_view") }}</p>
          </div>
          <div class="overview-metric">
            <span>{{ t("inbox.overview.reply_enabled") }}</span>
            <strong>{{ queueSummary.replyEnabledCount }}</strong>
            <p>{{ t("inbox.overview.channels_connected", { count: supportedSidebarAccounts.length }) }}</p>
          </div>
        </div>
      </section>

      <p v-if="error" class="inbox-error">{{ extractApiError(error, t("inbox.errors.load_failed")) }}</p>
      <p v-if="syncMessage" class="inbox-note global-note">{{ syncMessage }}</p>

      <div v-if="!hasInteractiveAccounts" class="empty-state large-empty-state">
        <strong>{{ t("inbox.empty.no_interactive_title") }}</strong>
        <p>{{ t("inbox.empty.no_interactive_body") }}</p>
        <NuxtLink class="post-link settings-link" :to="localePath('/app/settings')">{{ t("nav.settings") }}</NuxtLink>
      </div>

      <template v-else>
        <section class="inbox-toolbar">
          <div class="status-segments" role="tablist" aria-label="Thread status">
            <button
              v-for="option in statusOptions"
              :key="option"
              type="button"
              class="status-segment"
              :class="{ active: selectedStatus === option }"
              @click="setStatus(option)"
            >
              {{ option === "all" ? t("common.all") : triageLabel(option) }}
            </button>
          </div>

          <div class="inbox-filters">
            <label class="filter-field">
              <span>{{ t("inbox.filters.platform") }}</span>
              <select :value="selectedPlatform" @change="setPlatform(($event.target as HTMLSelectElement).value)">
                <option v-for="option in platformOptions" :key="option" :value="option">
                  {{ platformName(option) }}
                </option>
              </select>
            </label>

            <label class="filter-field">
              <span>{{ t("inbox.filters.channel") }}</span>
              <select :value="selectedAccountId" @change="setAccount(($event.target as HTMLSelectElement).value)">
                <option value="">{{ t("inbox.filters.all_channels") }}</option>
                <option v-for="option in accountOptions" :key="option.id" :value="option.id">
                  {{ option.label }} - {{ option.platform }}
                </option>
              </select>
            </label>
          </div>
        </section>

        <section class="inbox-layout">
          <aside class="inbox-list-card">
            <div class="panel-head list-head">
              <div>
                <p class="section-label">{{ t("inbox.list.queue") }}</p>
                <h2>{{ t("inbox.list.conversations_count", { count: threads.length }) }}</h2>
              </div>
              <p class="panel-caption">{{ scopeLabel }}</p>
            </div>

            <div v-if="pending" class="empty-state">{{ t("inbox.list.loading") }}</div>
            <div v-else-if="!threads.length" class="empty-state">
              {{ t("inbox.list.empty") }}
            </div>
            <div v-else class="thread-list">
              <button
                v-for="(thread, index) in threads"
                :key="thread.id"
                class="thread-row"
                :class="{ active: thread.id === selectedThreadId }"
                type="button"
                @click="openThread(thread.id)"
              >
                <div class="thread-row-top">
                  <div class="thread-row-main">
                    <div class="thread-badge" :data-platform="platformClass(thread.platform)">
                      <PlatformIcon :platform="platformClass(thread.platform)" :size="16" />
                    </div>
                    <div class="thread-copy">
                      <strong>{{ thread.account_name }}</strong>
                      <p>{{ platformName(thread.platform) }} - {{ thread.message_count }} messages</p>
                    </div>
                  </div>
                  <span class="thread-order">#{{ index + 1 }}</span>
                </div>

                <div class="thread-row-meta">
                  <span class="thread-status-pill" :data-tone="triageTone(thread.triage_status)">
                    {{ triageLabel(thread.triage_status) }}
                  </span>
                  <div class="thread-meta-group">
                    <span class="thread-time">{{ relativeTime(thread.last_message_at) }}</span>
                    <span v-if="thread.interaction_capabilities.reply_comments" class="thread-meta-pill">Reply enabled</span>
                  </div>
                </div>
              </button>
            </div>
          </aside>

          <article class="inbox-detail-card">
            <div v-if="!threadDetail" class="empty-state">
              Select a thread to review synced comments.
            </div>
            <template v-else>
              <div class="detail-hero">
                <div class="detail-title-row">
                  <div class="detail-thread-avatar" :data-platform="platformClass(threadDetail.platform)">
                    <PlatformIcon :platform="platformClass(threadDetail.platform)" :size="18" />
                  </div>

                  <div class="detail-title-copy">
                    <p class="section-label">
                      Thread {{ selectedThreadPosition ? `#${selectedThreadPosition}` : "" }}
                    </p>
                    <h2>{{ threadDetail.account_name }}</h2>
                    <p class="detail-meta">
                      {{ platformName(threadDetail.platform) }} - synced {{ formatDateTime(threadDetail.last_synced_at) }}
                    </p>
                  </div>
                </div>

                <div class="detail-actions">
                  <NuxtLink
                    v-if="threadDetail.related_post_id"
                    class="post-link"
                    :to="`/app/posts?post=${threadDetail.related_post_id}`"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path
                        d="M14 5h5v5m0-5-8 8m-4 6H5a2 2 0 0 1-2-2v-2m16 4v-5m-9 8H9"
                        fill="none"
                        stroke="currentColor"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="1.8"
                      />
                    </svg>
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
                  <span>Timeline</span>
                  <strong>{{ detailMessages.length }} events</strong>
                </div>
                <div class="summary-pill">
                  <span>Mix</span>
                  <strong>{{ inboundMessageCount }} inbound / {{ outboundMessageCount }} outbound</strong>
                </div>
                <div class="summary-pill">
                  <span>Provider object</span>
                  <strong :title="threadDetail.external_object_id">{{ compactExternalId(threadDetail.external_object_id) }}</strong>
                </div>
              </div>

              <section class="conversation-section">
                <div class="panel-head conversation-head">
                  <div>
                    <p class="section-label">Timeline</p>
                    <h3>Messages in thread order</h3>
                  </div>
                  <p class="panel-caption">Last message {{ formatDateTime(threadDetail.last_message_at) }}</p>
                </div>

                <div v-if="!detailMessages.length" class="empty-state">
                  This thread has no synced comments yet.
                </div>
                <div v-else class="message-list">
                  <article
                    v-for="message in detailMessages"
                    :key="message.id"
                    class="message-card"
                    :class="{ selected: replyTargetId === message.id }"
                    :data-direction="message.direction"
                    :style="{ '--depth': message.depth }"
                  >
                    <div class="message-rail">
                      <span class="message-rail-dot" />
                    </div>

                    <div class="message-surface">
                      <div class="message-head">
                        <div class="message-head-main">
                          <strong>{{ message.author_name }}</strong>
                          <span class="message-direction">{{ directionLabel(message.direction) }}</span>
                        </div>
                        <div class="message-head-actions">
                          <small>{{ formatDateTime(message.published_at) }}</small>
                          <button
                            v-if="message.direction === 'inbound' && canReplyToThread"
                            class="message-action"
                            type="button"
                            @click="startReply(message)"
                          >
                            <svg viewBox="0 0 24 24" aria-hidden="true">
                              <path
                                d="M10 9 5 12l5 3M5 12h8a6 6 0 0 1 6 6"
                                fill="none"
                                stroke="currentColor"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="1.8"
                              />
                            </svg>
                            Reply
                          </button>
                        </div>
                      </div>

                      <p>{{ message.body_text || "No text content." }}</p>
                    </div>
                  </article>
                </div>
              </section>

              <section class="reply-composer" :class="{ disabled: !canReplyToThread }">
                <div class="reply-composer-head">
                  <div>
                    <p class="section-label">Reply composer</p>
                    <strong>
                      {{ selectedReplyTarget ? `Replying to ${selectedReplyTarget.author_name}` : "Select a comment above" }}
                    </strong>
                  </div>
                  <button
                    v-if="selectedReplyTarget"
                    class="message-action clear-action"
                    type="button"
                    :disabled="replyPending"
                    @click="cancelReply"
                  >
                    Clear
                  </button>
                </div>

                <div v-if="selectedReplyTarget" class="reply-target">
                  <span>Selected comment</span>
                  <p>{{ replyTargetPreview }}</p>
                </div>

                <p v-if="replyError" class="inbox-error reply-error">{{ replyError }}</p>
                <p v-if="!canReplyToThread" class="inbox-note">
                  Replies are not available for this channel.
                </p>

                <textarea
                  v-model="replyBody"
                  class="reply-input"
                  :disabled="replyPending || !canReplyToThread"
                  placeholder="Write a reply"
                  rows="4"
                />

                <div class="reply-actions">
                  <span class="reply-hint">
                    {{
                      selectedReplyTarget
                        ? "Your reply will be posted directly to the selected comment."
                        : "Choose an inbound comment in the thread before sending."
                    }}
                  </span>

                  <button
                    class="sync-button primary-action"
                    type="button"
                    :disabled="replyPending || !selectedReplyTarget || !replyBody.trim() || !canReplyToThread"
                    @click="sendReply"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path
                        d="M4 12h13m0 0-5-5m5 5-5 5"
                        fill="none"
                        stroke="currentColor"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="1.8"
                      />
                    </svg>
                    {{ replyPending ? "Sending..." : "Send reply" }}
                  </button>
                </div>
              </section>
            </template>
          </article>
        </section>
      </template>
    </section>
  </div>
</template>

<style scoped>
.inbox-page {
  min-height: 100%;
  padding: 28px;
  background:
    linear-gradient(180deg, rgba(127, 162, 147, 0.08), rgba(127, 162, 147, 0) 180px),
    var(--page-gradient);
}

.inbox-shell {
  max-width: 1320px;
  margin: 0 auto;
  display: grid;
  gap: 20px;
}

.inbox-overview-card,
.inbox-toolbar,
.inbox-list-card,
.inbox-detail-card {
  border: 1px solid var(--line-soft);
  border-radius: 20px;
  background: var(--panel);
  box-shadow: var(--shadow-panel);
}

.inbox-header-copy,
.panel-head,
.filter-field,
.detail-actions,
.reply-composer,
.reply-composer-head {
  display: grid;
  gap: 8px;
}

.inbox-overview-card {
  padding: 24px;
}

.inbox-overview {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.overview-metric {
  min-width: 0;
  padding-left: 16px;
  border-left: 1px solid var(--line);
  display: grid;
  gap: 6px;
}

.overview-metric:first-child {
  padding-left: 0;
  border-left: 0;
}

.overview-metric span,
.summary-pill span {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.overview-metric strong {
  color: var(--ink);
  font-size: 28px;
  line-height: 1;
}

.overview-metric p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.45;
}

.overview-metric[data-tone="danger"] strong {
  color: #a02e22;
}

.overview-metric[data-tone="amber"] strong {
  color: #ad5c16;
}

.overview-metric[data-tone="success"] strong {
  color: var(--brand-fill);
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
.panel-caption,
.filter-field span,
.empty-state,
.message-head small,
.reply-hint,
.message-direction {
  color: var(--muted);
}

.global-note {
  margin-top: -8px;
}

.sync-button,
.post-link,
.message-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--surface-muted);
  color: var(--ink);
  font-weight: 700;
}

.sync-button svg,
.post-link svg,
.message-action svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.sync-button:disabled,
.message-action:disabled {
  opacity: 0.65;
  cursor: wait;
}

.primary-action {
  background: linear-gradient(180deg, var(--action-fill-start) 0%, var(--action-fill-end) 100%);
  border-color: var(--action-border);
  color: var(--action-ink);
}

.inbox-error {
  margin: 0;
  color: #a02e22;
}

.inbox-note,
.reply-error {
  margin: 0;
}

.inbox-toolbar {
  padding: 18px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.status-segments {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-segment {
  min-height: 38px;
  padding: 0 16px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface-muted);
  color: var(--muted);
  font-weight: 700;
  transition: border-color 0.14s ease, background 0.14s ease, color 0.14s ease, transform 0.14s ease;
}

.status-segment:hover {
  transform: translateY(-1px);
  border-color: var(--brand-outline);
  color: var(--ink);
}

.status-segment.active {
  border-color: rgba(90, 121, 107, 0.4);
  background: rgba(127, 162, 147, 0.14);
  color: var(--ink);
}

.inbox-filters {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 14px;
}

.filter-field {
  min-width: 190px;
}

.filter-field select,
.reply-input {
  width: 100%;
  min-height: 40px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: var(--input-bg);
  color: var(--ink);
}

.reply-input {
  min-height: 110px;
  padding: 12px;
  resize: vertical;
  font: inherit;
}

.inbox-layout {
  display: grid;
  grid-template-columns: minmax(320px, 0.92fr) minmax(0, 1.48fr);
  gap: 18px;
  align-items: start;
}

.inbox-list-card,
.inbox-detail-card {
  padding: 22px;
}

.thread-list,
.message-list {
  display: grid;
  gap: 12px;
}

.list-head,
.conversation-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-caption {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  text-align: right;
}

.thread-row {
  width: 100%;
  padding: 14px 15px;
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02)), var(--surface-muted);
  color: var(--ink);
  display: grid;
  gap: 12px;
  text-align: left;
  transition: border-color 0.14s ease, box-shadow 0.14s ease, transform 0.14s ease, background 0.14s ease;
}

.thread-row:hover {
  transform: translateY(-1px);
  border-color: rgba(90, 121, 107, 0.22);
  box-shadow: var(--shadow-soft);
}

.thread-row.active {
  border-color: rgba(90, 121, 107, 0.48);
  background: linear-gradient(180deg, rgba(127, 162, 147, 0.12), rgba(127, 162, 147, 0.04)), var(--surface-muted);
  box-shadow: var(--shadow-soft);
}

.thread-row-top,
.thread-row-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.thread-row-top {
  justify-content: space-between;
  gap: 16px;
}

.thread-order {
  flex-shrink: 0;
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
}

.thread-copy {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.thread-copy strong,
.message-head strong,
.summary-pill strong,
.reply-composer strong {
  color: var(--ink);
}

.thread-copy strong {
  display: block;
  font-size: 14px;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.thread-copy p {
  margin: 0;
  font-size: 12px;
  line-height: 1.35;
}

.thread-badge {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: #516177;
  color: #ffffff;
  flex-shrink: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18);
}

.thread-badge[data-platform="facebook"],
.detail-thread-avatar[data-platform="facebook"] {
  background: #1877f2;
}

.thread-badge[data-platform="instagram"],
.detail-thread-avatar[data-platform="instagram"] {
  background: #e1306c;
}

.thread-badge[data-platform="linkedin"],
.detail-thread-avatar[data-platform="linkedin"] {
  background: #0a66c2;
}

.thread-badge[data-platform="tiktok"],
.detail-thread-avatar[data-platform="tiktok"] {
  background: #111111;
}

.thread-badge[data-platform="youtube"],
.detail-thread-avatar[data-platform="youtube"] {
  background: #ff0000;
}

.thread-badge[data-platform="pinterest"],
.detail-thread-avatar[data-platform="pinterest"] {
  background: #e60023;
}

.thread-row-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.thread-meta-group {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.thread-status-pill,
.thread-count {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.thread-status-pill {
  padding: 0 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.thread-status-pill[data-tone="success"] {
  background: rgba(127, 162, 147, 0.18);
  color: var(--brand-strong);
}

.thread-status-pill[data-tone="amber"] {
  background: rgba(230, 126, 34, 0.14);
  color: #ad5c16;
}

.thread-status-pill[data-tone="danger"] {
  background: rgba(160, 46, 34, 0.12);
  color: #a02e22;
}

.thread-status-pill[data-tone="muted"] {
  background: rgba(107, 118, 111, 0.14);
  color: #58625c;
}

.thread-time,
.thread-meta-pill {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}

.thread-meta-pill {
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(31, 75, 57, 0.08);
  color: var(--brand-fill);
}

.empty-state {
  padding: 18px;
  border-radius: 18px;
  border: 1px dashed rgba(19, 38, 27, 0.12);
  background: var(--surface-muted);
}

.large-empty-state {
  display: grid;
  gap: 10px;
}

.settings-link {
  width: fit-content;
}

.detail-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.detail-title-row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
}

.detail-thread-avatar {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #ffffff;
  flex-shrink: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18);
}

.detail-title-copy {
  min-width: 0;
  display: grid;
  gap: 6px;
}

.detail-title-copy h2,
.conversation-head h3 {
  margin: 0;
  color: var(--ink);
}

.detail-summary {
  margin: 18px 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-pill {
  padding: 14px;
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.02)), var(--surface-muted);
  display: grid;
  gap: 6px;
}

.summary-pill strong {
  line-height: 1.4;
}

.conversation-section {
  display: grid;
  gap: 14px;
}

.message-card {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 12px;
  margin-left: calc(var(--depth, 0) * 20px);
}

.message-rail {
  position: relative;
  display: flex;
  justify-content: center;
}

.message-rail::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: -12px;
  width: 1px;
  background: var(--line);
}

.message-list .message-card:last-child .message-rail::before {
  bottom: 18px;
}

.message-rail-dot {
  position: relative;
  z-index: 1;
  width: 10px;
  height: 10px;
  margin-top: 20px;
  border-radius: 50%;
  background: var(--brand-fill);
  box-shadow: 0 0 0 4px var(--panel);
}

.message-surface {
  padding: 16px;
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  background: var(--surface-muted);
}

.message-card.selected .message-surface {
  border-color: rgba(90, 121, 107, 0.42);
  box-shadow: var(--shadow-soft);
}

.message-card[data-direction="outbound"] .message-surface {
  background: rgba(127, 162, 147, 0.12);
  border-color: rgba(90, 121, 107, 0.28);
}

.message-card[data-direction="outbound"] .message-rail-dot {
  background: var(--brand);
}

.message-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.message-head-main,
.message-head-actions {
  display: grid;
  gap: 4px;
}

.message-head-actions {
  justify-items: end;
  text-align: right;
}

.message-direction {
  font-size: 12px;
  font-weight: 700;
}

.message-action {
  min-height: 32px;
  padding: 0 12px;
  font-size: 12px;
  background: var(--panel);
}

.clear-action {
  width: fit-content;
}

.message-surface p {
  margin: 0;
  color: var(--ink);
  line-height: 1.55;
}

.reply-composer {
  margin-top: 18px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  background: var(--surface-muted);
}

.reply-target {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(90, 121, 107, 0.18);
  background: rgba(127, 162, 147, 0.1);
  display: grid;
  gap: 6px;
}

.reply-target span {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.reply-target p {
  margin: 0;
  color: var(--ink);
  line-height: 1.55;
}

.reply-composer.disabled {
  opacity: 0.84;
}

.reply-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.reply-hint {
  font-size: 13px;
  line-height: 1.5;
}

.compact-field {
  min-width: 180px;
}

@media (max-width: 1180px) {
  .inbox-layout,
  .detail-summary,
  .inbox-overview {
    grid-template-columns: 1fr;
  }

  .overview-metric {
    padding-left: 0;
    padding-top: 14px;
    border-left: 0;
    border-top: 1px solid var(--line);
  }

  .overview-metric:first-child {
    padding-top: 0;
    border-top: 0;
  }
}

@media (max-width: 1040px) {
  .inbox-toolbar,
  .detail-hero,
  .list-head,
  .conversation-head {
    flex-direction: column;
    align-items: stretch;
  }

  .inbox-filters {
    justify-content: stretch;
  }

  .filter-field {
    flex: 1 1 220px;
  }

  .detail-actions {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .inbox-page {
    padding: 20px;
  }

  .reply-actions,
  .message-head,
  .thread-row-top,
  .thread-row-meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .inbox-header-actions {
    width: 100%;
  }

  .message-head-actions {
    justify-items: start;
    text-align: left;
  }

  .thread-meta-group {
    justify-content: flex-start;
  }

  .status-segments {
    width: 100%;
    overflow-x: auto;
    flex-wrap: nowrap;
    padding-bottom: 2px;
  }

  .status-segment {
    flex: 0 0 auto;
  }

  .inbox-overview-card,
  .inbox-toolbar,
  .inbox-list-card,
  .inbox-detail-card {
    padding: 18px;
  }

  .message-card {
    margin-left: calc(var(--depth, 0) * 12px);
  }

  .detail-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .detail-summary {
    grid-template-columns: 1fr;
  }

  .detail-title-row {
    width: 100%;
  }

  .detail-title-copy,
  .detail-title-copy h2 {
    min-width: 0;
  }

  .detail-title-copy h2 {
    overflow-wrap: anywhere;
  }
}
</style>
