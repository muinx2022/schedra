<script setup lang="ts">
definePageMeta({ middleware: "auth" })

const localePath = useLocalePath()
const intlLocale = useIntlLocale()

type InteractionCapabilities = {
  inbox_comments: boolean
  reply_comments: boolean
}

type CommunityMessage = {
  id: string
  external_id: string
  parent_external_id: string
  author_name: string
  author_external_id: string
  body_text: string
  direction: string
  published_at: string
  metadata: Record<string, any>
}

type CommunityItemApi = {
  external_object_id: string
  thread_id: string | null
  related_post_id: string | null
  account_id: string
  account_name: string
  platform: string
  title: string
  body_text: string
  snippet: string
  published_at: string | null
  last_activity_at: string | null
  permalink_url: string
  preview_image_url: string
  comment_count: number
  triage_status: string
  interaction_capabilities: InteractionCapabilities
}

type AccountOption = {
  id: string
  display_name: string
  provider_code: string
  channel_code?: string
  interaction_capabilities?: InteractionCapabilities
}

type CommunityItem = {
  externalObjectId: string
  threadId: string | null
  relatedPostId: string | null
  accountId: string
  accountName: string
  platform: string
  title: string
  bodyText: string
  snippet: string
  publishedAt: string | null
  commentCount: number
  permalinkUrl: string
  previewImageUrl: string
  lastActivityAt: string | null
  triageStatus: string
  interactionCapabilities: InteractionCapabilities
}

type CommunityDetail = CommunityItem & {
  messages: CommunityMessage[]
}

const route = useRoute()
const router = useRouter()
const sidebarAccounts = useNuxtData<AccountOption[]>("sidebar-accounts")

const syncPending = ref(false)
const syncMessage = ref("")
const triagePending = ref<string | null>(null)
const replyPending = ref(false)
const replyError = ref("")
const replyBody = ref("")
const replyTargetId = ref("")

const selectedAccountId = computed(() => {
  const value = route.query.account
  return typeof value === "string" ? value : ""
})

const selectedPostId = computed(() => {
  const value = route.query.post
  return typeof value === "string" ? value : ""
})

const supportedSidebarAccounts = computed(() =>
  (sidebarAccounts.data.value || []).filter((item) => item.interaction_capabilities?.inbox_comments)
)

const hasInteractiveAccounts = computed(() => supportedSidebarAccounts.value.length > 0)

const selectedAccount = computed(() =>
  supportedSidebarAccounts.value.find((item) => item.id === selectedAccountId.value) || null
)

const communityPostsPath = computed(() =>
  selectedAccountId.value ? `/inbox/community/${selectedAccountId.value}/posts/` : ""
)

const { data: communityItems, pending: communityPostsPending, error: communityPostsError, refresh: refreshCommunityPosts } = useAsyncData(
  "community-posts",
  () =>
    communityPostsPath.value
      ? apiFetch<CommunityItemApi[]>(communityPostsPath.value).then((items) => items.map(normalizeCommunityItem))
      : Promise.resolve([]),
  {
    default: () => [],
    watch: [communityPostsPath],
    server: false,
  }
)

const selectedCommunityItem = computed(() => {
  if (!communityItems.value.length) return null
  return communityItems.value.find((item) => item.externalObjectId === selectedPostId.value) || communityItems.value[0]
})

const communityDetailPath = computed(() => {
  if (!selectedAccountId.value || !selectedCommunityItem.value?.externalObjectId) return ""
  return `/inbox/community/${selectedAccountId.value}/posts/${encodeURIComponent(selectedCommunityItem.value.externalObjectId)}/`
})

const { data: communityDetail, pending: communityDetailPending, error: communityDetailError, refresh: refreshCommunityDetail } = useAsyncData(
  "community-post-detail",
  () =>
    communityDetailPath.value
      ? apiFetch<CommunityItemApi & { messages: CommunityMessage[] }>(communityDetailPath.value).then(normalizeCommunityDetail)
      : Promise.resolve(null),
  {
    default: () => null,
    watch: [communityDetailPath],
    server: false,
  }
)

const detailMessages = computed(() => {
  const messages = communityDetail.value?.messages || []
  const byId = new Map(messages.map((item) => [item.id, item]))
  const externalToId = new Map(messages.map((item) => [item.external_id, item.id]))
  return messages.map((message) => {
    let depth = 0
    let currentParentId = externalToId.get(message.parent_external_id) || null
    const visited = new Set<string>()
    while (currentParentId && !visited.has(currentParentId) && depth < 4) {
      visited.add(currentParentId)
      const parent = byId.get(currentParentId)
      if (!parent) break
      depth += 1
      currentParentId = externalToId.get(parent.parent_external_id) || null
    }
    return { ...message, depth }
  })
})

const selectedReplyTarget = computed(() =>
  detailMessages.value.find((message) => message.id === replyTargetId.value) || null
)

const canCommentOnPost = computed(() => !!selectedCommunityItem.value?.externalObjectId)

const canReplyToThread = computed(() =>
  !!communityDetail.value?.threadId && !!communityDetail.value?.interactionCapabilities?.reply_comments
)

const communitySummary = computed(() => ({
  totalPosts: communityItems.value.length,
  postsWithComments: communityItems.value.filter((item) => item.commentCount > 0).length,
  totalComments: communityItems.value.reduce((sum, item) => sum + item.commentCount, 0),
  unresolved: communityItems.value.filter((item) => ["new", "reviewing"].includes(item.triageStatus)).length,
}))

const detailPosition = computed(() => {
  const index = communityItems.value.findIndex((item) => item.externalObjectId === selectedCommunityItem.value?.externalObjectId)
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

const pagePending = computed(() => communityPostsPending.value)
const pageError = computed(() => communityPostsError.value || communityDetailError.value)

watch(
  supportedSidebarAccounts,
  (accounts) => {
    const accountIds = new Set(accounts.map((item) => item.id))
    if (selectedAccountId.value && !accountIds.has(selectedAccountId.value)) {
      updateQuery({ account: accounts[0]?.id, post: undefined })
      return
    }
    if (!selectedAccountId.value && accounts.length) {
      updateQuery({ account: accounts[0].id, post: undefined })
    }
  },
  { immediate: true }
)

watch(
  communityItems,
  (items) => {
    if (!items.length) {
      if (selectedPostId.value) updateQuery({ post: undefined })
      return
    }
    if (!selectedPostId.value || !items.some((item) => item.externalObjectId === selectedPostId.value)) {
      updateQuery({ post: items[0].externalObjectId })
    }
  },
  { immediate: true }
)

watch(
  () => communityDetail.value?.threadId,
  () => {
    replyTargetId.value = ""
    replyBody.value = ""
    replyError.value = ""
  }
)

function updateQuery(patch: Record<string, string | undefined>) {
  router.replace({ query: { ...route.query, ...patch } })
}

function openCommunityItem(itemId: string) {
  updateQuery({ post: itemId })
}

function formatDateTime(value?: string | null) {
  if (!value) return "No activity yet"
  return new Date(value).toLocaleString(intlLocale.value, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function relativeTime(value?: string | null) {
  if (!value) return "No activity"
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
    facebook: "Facebook",
    instagram: "Instagram",
    linkedin: "LinkedIn",
    tiktok: "TikTok",
    youtube: "YouTube",
    pinterest: "Pinterest",
  }
  return names[code || ""] ?? code ?? "Channel"
}

function triageLabel(status: string) {
  const labels: Record<string, string> = {
    new: "New",
    reviewing: "Reviewing",
    resolved: "Resolved",
    ignored: "Ignored",
    idle: "No thread",
  }
  return labels[status] ?? status
}

function triageTone(status: string) {
  const tones: Record<string, string> = {
    new: "danger",
    reviewing: "amber",
    resolved: "success",
    ignored: "muted",
    idle: "muted",
  }
  return tones[status] ?? "muted"
}

function directionLabel(direction: string) {
  return direction === "outbound" ? "Reply" : "Comment"
}

function platformClass(code?: string) {
  const value = (code || "").toLowerCase()
  return ["facebook", "instagram", "linkedin", "tiktok", "youtube", "pinterest"].includes(value)
    ? value
    : "generic"
}

function truncateText(value: string, max = 140) {
  const normalized = value.replace(/\s+/g, " ").trim()
  if (!normalized) return "No caption yet."
  if (normalized.length <= max) return normalized
  return `${normalized.slice(0, max - 3)}...`
}

function compactExternalId(value?: string | null) {
  if (!value) return "Not available"
  if (value.length <= 18) return value
  return `${value.slice(0, 8)}...${value.slice(-6)}`
}

function buildPostTitle(title?: string, bodyText?: string) {
  const source = (title || bodyText || "").replace(/\s+/g, " ").trim()
  if (!source) return "Untitled post"
  return source.length > 88 ? `${source.slice(0, 88)}...` : source
}

function buildPostSnippet(snippet?: string, bodyText?: string, title?: string) {
  const candidate = (snippet || truncateText(bodyText || "No caption yet.")).replace(/\s+/g, " ").trim()
  const normalizedTitle = (title || "").replace(/\s+/g, " ").trim()
  if (!candidate) return ""
  if (!normalizedTitle) return candidate
  if (candidate === normalizedTitle) return ""
  const titlePrefix = normalizedTitle.replace(/\.\.\.$/, "").trim()
  if (!titlePrefix) return candidate
  if (candidate.startsWith(normalizedTitle)) return ""
  if (candidate.startsWith(titlePrefix)) {
    const remainder = candidate.slice(titlePrefix.length).replace(/^[\s,.;:!?-]+/, "").trim()
    return remainder || ""
  }
  return candidate
}

function normalizeCommunityItem(item: CommunityItemApi): CommunityItem {
  const title = buildPostTitle(item.title, item.body_text)
  return {
    externalObjectId: item.external_object_id,
    threadId: item.thread_id,
    relatedPostId: item.related_post_id,
    accountId: item.account_id,
    accountName: item.account_name,
    platform: item.platform,
    title,
    bodyText: item.body_text || "",
    snippet: buildPostSnippet(item.snippet, item.body_text, title),
    publishedAt: item.published_at,
    commentCount: item.comment_count || 0,
    permalinkUrl: item.permalink_url || "",
    previewImageUrl: item.preview_image_url || "",
    lastActivityAt: item.last_activity_at,
    triageStatus: item.triage_status || "idle",
    interactionCapabilities: item.interaction_capabilities || { inbox_comments: false, reply_comments: false },
  }
}

function normalizeCommunityDetail(item: CommunityItemApi & { messages: CommunityMessage[] }): CommunityDetail {
  return {
    ...normalizeCommunityItem(item),
    messages: item.messages || [],
  }
}

function startReply(message: CommunityMessage) {
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
    syncMessage.value = "Community sync queued."
    await refreshCommunityPosts()
    if (communityDetailPath.value) await refreshCommunityDetail()
  } catch (syncError) {
    syncMessage.value = extractApiError(syncError, "Could not queue community sync.")
  } finally {
    syncPending.value = false
  }
}

async function updateTriageStatus(nextStatus: string) {
  if (!communityDetail.value?.threadId) return
  triagePending.value = nextStatus
  try {
    await apiFetch(`/inbox/threads/${communityDetail.value.threadId}/`, {
      method: "PATCH",
      body: { triage_status: nextStatus },
    })
    await Promise.all([refreshCommunityPosts(), refreshCommunityDetail()])
  } catch (triageError) {
    syncMessage.value = extractApiError(triageError, "Could not update triage status.")
  } finally {
    triagePending.value = null
  }
}

async function sendReply() {
  if (!communityDetail.value?.threadId || !replyTargetId.value || !replyBody.value.trim()) return
  replyPending.value = true
  replyError.value = ""
  try {
    await apiFetch(`/inbox/threads/${communityDetail.value.threadId}/reply/`, {
      method: "POST",
      body: {
        parent_message_id: replyTargetId.value,
        body_text: replyBody.value.trim(),
      },
    })
    replyBody.value = ""
    replyTargetId.value = ""
    await Promise.all([refreshCommunityPosts(), refreshCommunityDetail()])
  } catch (replyRequestError) {
    replyError.value = extractApiError(replyRequestError, "Could not send reply.")
  } finally {
    replyPending.value = false
  }
}

async function sendPostComment() {
  if (!selectedAccountId.value || !selectedCommunityItem.value?.externalObjectId || !replyBody.value.trim()) return
  replyPending.value = true
  replyError.value = ""
  try {
    const updated = await apiFetch<CommunityItemApi & { messages: CommunityMessage[] }>(
      `/inbox/community/${selectedAccountId.value}/posts/${encodeURIComponent(selectedCommunityItem.value.externalObjectId)}/comment/`,
      {
        method: "POST",
        body: {
          body_text: replyBody.value.trim(),
        },
      }
    )
    communityDetail.value = normalizeCommunityDetail(updated)
    replyBody.value = ""
    replyTargetId.value = ""
    await refreshCommunityPosts()
  } catch (commentError) {
    replyError.value = extractApiError(commentError, "Could not post comment.")
  } finally {
    replyPending.value = false
  }
}

async function sendComposer() {
  if (selectedReplyTarget.value) {
    await sendReply()
    return
  }
  await sendPostComment()
}
</script>

<template>
  <div class="community-page">
    <section class="community-shell">
      <header class="community-header">
        <div class="community-header-copy">
          <p class="section-label">Community</p>
          <h1>Comment workspace</h1>
          <p>
            Browse synced posts for the selected page on the left. Open any post to inspect comments and reply from the
            detail pane.
          </p>
        </div>

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
          {{ syncPending ? "Queueing..." : "Refresh community" }}
        </button>
      </header>

      <section class="community-overview-card">
        <div class="community-overview">
          <div class="overview-metric">
            <span>Selected page</span>
            <strong>{{ selectedAccount?.display_name || "Choose a page" }}</strong>
            <p>{{ selectedAccount ? platformName(selectedAccount.channel_code || selectedAccount.provider_code) : "No page selected" }}</p>
          </div>
          <div class="overview-metric">
            <span>Posts loaded</span>
            <strong>{{ communitySummary.totalPosts }}</strong>
            <p>{{ communitySummary.postsWithComments }} with synced comments</p>
          </div>
          <div class="overview-metric" data-tone="danger">
            <span>Open triage</span>
            <strong>{{ communitySummary.unresolved }}</strong>
            <p>Posts that still need attention</p>
          </div>
          <div class="overview-metric" data-tone="success">
            <span>Total comments</span>
            <strong>{{ communitySummary.totalComments }}</strong>
            <p>Across the visible post list</p>
          </div>
        </div>
      </section>

      <p v-if="pageError" class="community-error">{{ extractApiError(pageError, "Could not load community data.") }}</p>
      <p v-if="syncMessage" class="community-note">{{ syncMessage }}</p>

      <div v-if="!hasInteractiveAccounts" class="empty-state large-empty-state">
        <strong>No connected channels support Community yet.</strong>
        <p>Connect a Facebook or Instagram page first, then come back here to review post conversations.</p>
        <NuxtLink class="post-link settings-link" :to="localePath('/app/settings')">Open settings</NuxtLink>
      </div>

      <template v-else>
        <section class="community-layout">
          <aside class="community-list-card">
            <div class="panel-head">
              <div>
                <p class="section-label">Posts</p>
                <h2>{{ communitySummary.totalPosts }} items</h2>
              </div>
              <p class="panel-caption">{{ selectedAccount?.display_name || "All interactive channels" }}</p>
            </div>

            <div v-if="pagePending" class="empty-state">Loading posts...</div>
            <div v-else-if="!communityItems.length" class="empty-state">
              No posts found for this page yet.
            </div>
            <div v-else class="community-post-list">
              <button
                v-for="(item, index) in communityItems"
                :key="item.externalObjectId"
                class="community-post-card"
                :class="{ active: item.externalObjectId === selectedCommunityItem?.externalObjectId }"
                type="button"
                @click="openCommunityItem(item.externalObjectId)"
              >
                <div class="community-post-head">
                  <div class="community-post-main">
                    <div class="community-post-badge" :data-platform="platformClass(item.platform)">
                      <PlatformIcon :platform="platformClass(item.platform)" :size="16" />
                    </div>
                    <div class="community-post-copy">
                      <strong>{{ item.title }}</strong>
                      <p v-if="item.snippet">{{ item.snippet }}</p>
                    </div>
                  </div>
                  <span class="community-post-order">#{{ index + 1 }}</span>
                </div>

                <div class="community-post-meta">
                  <span class="status-pill" :data-tone="triageTone(item.triageStatus)">{{ triageLabel(item.triageStatus) }}</span>
                  <div class="community-post-meta-right">
                    <span class="count-pill">{{ item.commentCount }} comments</span>
                    <span class="time-pill">{{ relativeTime(item.lastActivityAt) }}</span>
                  </div>
                </div>
              </button>
            </div>
          </aside>

          <article class="community-detail-card">
            <div v-if="!selectedCommunityItem" class="empty-state">
              Select a post from the left list to inspect its thread.
            </div>
            <template v-else>
              <div class="detail-hero">
                <div class="detail-title-row">
                  <div class="detail-thread-avatar" :data-platform="platformClass(selectedCommunityItem.platform)">
                    <PlatformIcon :platform="platformClass(selectedCommunityItem.platform)" :size="18" />
                  </div>

                  <div class="detail-title-copy">
                    <p class="section-label">Post {{ detailPosition ? `#${detailPosition}` : "" }}</p>
                    <h2>{{ selectedCommunityItem.accountName }}</h2>
                    <p class="detail-meta">
                      {{ selectedCommunityItem.accountName }} - {{ platformName(selectedCommunityItem.platform) }} - last activity
                      {{ formatDateTime(selectedCommunityItem.lastActivityAt) }}
                    </p>
                  </div>
                </div>

                <div class="detail-actions">
                  <a
                    v-if="selectedCommunityItem.permalinkUrl"
                    class="post-link"
                    :href="selectedCommunityItem.permalinkUrl"
                    rel="noreferrer"
                    target="_blank"
                  >
                    Open post
                  </a>

                  <label v-if="communityDetail?.threadId" class="filter-field compact-field">
                    <span>Triage</span>
                    <select
                      :value="communityDetail?.triageStatus"
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
                  <span>Thread status</span>
                  <strong>{{ triageLabel(selectedCommunityItem.triageStatus) }}</strong>
                </div>
                <div class="summary-pill">
                  <span>Comments</span>
                  <strong>{{ selectedCommunityItem.commentCount }}</strong>
                </div>
                <div class="summary-pill">
                  <span>Mix</span>
                  <strong>{{ inboundMessageCount }} inbound / {{ outboundMessageCount }} outbound</strong>
                </div>
                <div class="summary-pill">
                  <span>Provider object</span>
                  <strong :title="selectedCommunityItem.externalObjectId">{{ compactExternalId(selectedCommunityItem.externalObjectId) }}</strong>
                </div>
              </div>

              <section class="post-body-card">
                <div class="panel-head">
                  <div>
                    <p class="section-label">Content</p>
                    <h3>Full post content</h3>
                  </div>
                  <p class="panel-caption">
                    {{ selectedCommunityItem.publishedAt ? `Published ${formatDateTime(selectedCommunityItem.publishedAt)}` : "Not published yet" }}
                  </p>
                </div>
                <p class="post-body-text">
                  {{ selectedCommunityItem.bodyText || selectedCommunityItem.snippet }}
                </p>
              </section>

              <section class="conversation-section">
                <div class="panel-head">
                  <div>
                    <p class="section-label">Community</p>
                    <h3>Comments and replies</h3>
                  </div>
                  <p class="panel-caption" v-if="communityDetail">Last activity {{ formatDateTime(communityDetail.lastActivityAt) }}</p>
                </div>

                <div v-if="communityDetailPending" class="empty-state">
                  Loading post detail...
                </div>
                <div v-else-if="!communityDetail" class="empty-state">
                  Could not load this post yet.
                </div>
                <div v-else-if="!detailMessages.length" class="empty-state">
                  This post has no comments yet.
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
                          <small>{{ relativeTime(message.published_at) }}</small>
                          <button
                            v-if="message.direction === 'inbound' && canReplyToThread"
                            class="message-action"
                            type="button"
                            @click="startReply(message)"
                          >
                            Reply
                          </button>
                        </div>
                      </div>

                      <p>{{ message.body_text || "No text content." }}</p>
                    </div>
                  </article>
                </div>
              </section>

              <section class="reply-composer" :class="{ disabled: !canCommentOnPost }">
                <div class="reply-composer-head">
                  <div>
                    <p class="section-label">{{ selectedReplyTarget ? "Reply composer" : "Post comment" }}</p>
                    <strong>{{ selectedReplyTarget ? `Replying to ${selectedReplyTarget.author_name}` : "Comment directly on this post" }}</strong>
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

                <p v-if="replyError" class="community-error">{{ replyError }}</p>
                <p v-if="selectedReplyTarget && communityDetail && !canReplyToThread" class="community-note">
                  Replies are not available for this channel.
                </p>
                <p v-else-if="selectedReplyTarget && !communityDetail?.threadId" class="community-note">
                  Replies become available after the post has a synced thread.
                </p>
                <p v-else class="community-note">
                  Type here to publish a new comment directly on the post.
                </p>

                <textarea
                  v-model="replyBody"
                  class="reply-input"
                  :disabled="replyPending || !canCommentOnPost || (!!selectedReplyTarget && !canReplyToThread)"
                  :placeholder="selectedReplyTarget ? 'Write a reply' : 'Write a comment on this post'"
                  rows="4"
                />

                <div class="reply-actions">
                  <span class="reply-hint">
                    {{
                      selectedReplyTarget
                        ? "Your reply will be posted directly to the selected comment."
                        : "This message will be posted as a new top-level comment on the post."
                    }}
                  </span>

                  <button
                    class="sync-button primary-action"
                    type="button"
                    :disabled="replyPending || !replyBody.trim() || !canCommentOnPost || (!!selectedReplyTarget && !canReplyToThread)"
                    @click="sendComposer"
                  >
                    {{ replyPending ? "Sending..." : selectedReplyTarget ? "Send reply" : "Post comment" }}
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
.community-page {
  min-height: 100%;
  padding: 28px;
  background:
    linear-gradient(180deg, rgba(127, 162, 147, 0.08), rgba(127, 162, 147, 0) 180px),
    var(--page-gradient);
}

.community-shell {
  max-width: 1380px;
  margin: 0 auto;
  display: grid;
  gap: 20px;
}

.community-header,
.community-overview-card,
.community-list-card,
.community-detail-card,
.post-body-card {
  border: 1px solid var(--line-soft);
  border-radius: 22px;
  background: var(--panel);
  box-shadow: var(--shadow-panel);
}

.community-header,
.detail-hero,
.detail-actions,
.reply-actions,
.message-head,
.community-post-head,
.community-post-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.community-header {
  padding: 26px 28px;
}

.community-header-copy,
.panel-head,
.reply-composer,
.reply-composer-head,
.detail-title-copy,
.community-post-copy,
.message-head-main,
.message-head-actions {
  display: grid;
  gap: 8px;
}

.community-header-copy h1,
.panel-head h2,
.panel-head h3,
.detail-title-copy h2 {
  margin: 0;
  color: var(--ink);
}

.community-header-copy p:last-child,
.panel-caption,
.detail-meta,
.community-note,
.reply-hint,
.message-direction,
.message-head small,
.community-post-copy p,
.empty-state {
  color: var(--muted);
}

.section-label {
  margin: 0;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
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

.sync-button svg {
  width: 16px;
  height: 16px;
}

.primary-action {
  background: linear-gradient(180deg, var(--action-fill-start) 0%, var(--action-fill-end) 100%);
  border-color: var(--action-border);
  color: var(--action-ink);
}

.community-overview-card {
  padding: 24px;
}

.community-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
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
  font-size: 13px;
  line-height: 1.45;
  color: var(--muted);
}

.overview-metric[data-tone="danger"] strong {
  color: #a02e22;
}

.overview-metric[data-tone="success"] strong {
  color: var(--brand-fill);
}

.community-error,
.community-note {
  margin: 0;
}

.community-error {
  color: #a02e22;
}

.large-empty-state,
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

.community-layout {
  display: grid;
  grid-template-columns: minmax(330px, 0.82fr) minmax(0, 1.48fr);
  gap: 18px;
  align-items: start;
}

.community-list-card,
.community-detail-card {
  padding: 22px;
}

.community-post-list,
.message-list {
  display: grid;
  gap: 12px;
}

.panel-head {
  margin-bottom: 16px;
}

.panel-caption {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  text-align: right;
}

.community-post-card {
  width: 100%;
  padding: 14px 15px;
  border-radius: 18px;
  border: 1px solid var(--line-soft);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02)), var(--surface-muted);
  color: var(--ink);
  display: grid;
  gap: 12px;
  text-align: left;
  transition: border-color 0.14s ease, box-shadow 0.14s ease, transform 0.14s ease;
}

.community-post-card:hover {
  transform: translateY(-1px);
  border-color: rgba(90, 121, 107, 0.24);
  box-shadow: var(--shadow-soft);
}

.community-post-card.active {
  border-color: rgba(90, 121, 107, 0.48);
  background: linear-gradient(180deg, rgba(127, 162, 147, 0.12), rgba(127, 162, 147, 0.04)), var(--surface-muted);
}

.community-post-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 0;
}

.community-post-copy {
  min-width: 0;
}

.community-post-copy strong {
  display: block;
  font-size: 14px;
  line-height: 1.25;
  color: var(--ink);
}

.community-post-copy p {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
}

.community-post-order {
  flex-shrink: 0;
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
}

.community-post-badge,
.detail-thread-avatar {
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

.detail-thread-avatar {
  width: 48px;
  height: 48px;
  border-radius: 14px;
}

.community-post-badge[data-platform="facebook"],
.detail-thread-avatar[data-platform="facebook"] {
  background: #1877f2;
}

.community-post-badge[data-platform="instagram"],
.detail-thread-avatar[data-platform="instagram"] {
  background: #e1306c;
}

.community-post-badge[data-platform="linkedin"],
.detail-thread-avatar[data-platform="linkedin"] {
  background: #0a66c2;
}

.community-post-badge[data-platform="tiktok"],
.detail-thread-avatar[data-platform="tiktok"] {
  background: #111111;
}

.community-post-badge[data-platform="youtube"],
.detail-thread-avatar[data-platform="youtube"] {
  background: #ff0000;
}

.community-post-badge[data-platform="pinterest"],
.detail-thread-avatar[data-platform="pinterest"] {
  background: #e60023;
}

.community-post-meta-right {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.status-pill,
.count-pill,
.time-pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.status-pill {
  padding: 0 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status-pill[data-tone="success"] {
  background: rgba(127, 162, 147, 0.18);
  color: var(--brand-strong);
}

.status-pill[data-tone="amber"] {
  background: rgba(230, 126, 34, 0.14);
  color: #ad5c16;
}

.status-pill[data-tone="danger"] {
  background: rgba(160, 46, 34, 0.12);
  color: #a02e22;
}

.status-pill[data-tone="muted"] {
  background: rgba(107, 118, 111, 0.14);
  color: #58625c;
}

.count-pill,
.time-pill {
  padding: 0 10px;
  color: var(--muted);
  background: rgba(19, 38, 27, 0.05);
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

.summary-pill strong,
.message-head strong,
.reply-composer strong {
  color: var(--ink);
}

.post-body-card,
.reply-composer {
  padding: 18px;
}

.post-body-text {
  margin: 0;
  color: var(--ink);
  line-height: 1.7;
  white-space: pre-wrap;
}

.conversation-section {
  display: grid;
  gap: 14px;
  margin-top: 18px;
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

.message-surface p,
.reply-target p {
  margin: 0;
  color: var(--ink);
  line-height: 1.55;
}

.reply-composer {
  margin-top: 18px;
  border: 1px solid var(--line-soft);
  border-radius: 18px;
  background: var(--surface-muted);
  display: grid;
  gap: 14px;
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

.reply-input,
.filter-field select {
  width: 100%;
  min-height: 42px;
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

.reply-composer.disabled {
  opacity: 0.84;
}

.compact-field {
  min-width: 180px;
}

@media (max-width: 1180px) {
  .community-layout,
  .detail-summary,
  .community-overview {
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

@media (max-width: 860px) {
  .community-page {
    padding: 20px;
  }

  .community-header,
  .detail-hero,
  .detail-actions,
  .reply-actions,
  .message-head,
  .community-post-head,
  .community-post-meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .community-list-card,
  .community-detail-card,
  .community-overview-card {
    padding: 18px;
  }

  .community-post-meta-right,
  .message-head-actions {
    justify-content: flex-start;
    justify-items: start;
    text-align: left;
  }

  .message-card {
    margin-left: calc(var(--depth, 0) * 12px);
  }
}
</style>
