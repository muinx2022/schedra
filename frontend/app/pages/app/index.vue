<script setup lang="ts">
definePageMeta({ middleware: "auth" })

type Idea = {
  id: number
  title: string
  note: string
  column: string
  tags: string[]
  created_at?: string
  updated_at?: string
}

type Post = {
  id: string
  caption_text: string
  delivery_status: string
  scheduled_at?: string | null
  published_at?: string | null
  created_at: string
  media_items?: Array<{ id: string }>
  targets?: Array<{ social_account: string }>
}

type Account = {
  id: string
  display_name: string
  provider_code: string
  channel_code?: string
  channel_name?: string
  status: string
  queue_slots?: Array<{ id: string; is_active: boolean }>
}

type MediaAsset = {
  id: string
  title?: string
  file_name: string
  created_at: string
}

const session = useSessionState()

const { data: ideas } = useAsyncData(
  "dashboard-ideas",
  () => apiFetch<Idea[]>("/ideas/"),
  { lazy: true, default: () => [], server: false }
)

const { data: posts } = useAsyncData(
  "dashboard-posts",
  () => apiFetch<Post[]>("/posts/"),
  { lazy: true, default: () => [], server: false }
)

const { data: accounts } = useAsyncData(
  "dashboard-accounts",
  () => apiFetch<Account[]>("/accounts/"),
  { lazy: true, default: () => [], server: false }
)

const { data: assets } = useAsyncData(
  "dashboard-assets",
  () => apiFetch<MediaAsset[]>("/media/"),
  { lazy: true, default: () => [], server: false }
)

const workspaceName = computed(() => session.user?.workspace?.name || "Your workspace")
const accountCount = computed(() => accounts.value.length)
const assetCount = computed(() => assets.value.length)
const draftCount = computed(() => posts.value.filter(post => post.delivery_status === "draft").length)
const queuedCount = computed(() =>
  posts.value.filter(post => ["queued", "scheduled", "publishing"].includes(post.delivery_status)).length
)
const publishedCount = computed(() =>
  posts.value.filter(post => post.delivery_status === "published").length
)
const readyIdeasCount = computed(() => ideas.value.filter(idea => idea.column === "done").length)

const completionRate = computed(() => {
  const total = ideas.value.length
  if (!total) return 0
  return Math.round((readyIdeasCount.value / total) * 100)
})

const connectedChannels = computed(() =>
  accounts.value.filter(account => account.status === "active" || account.status === "connected")
)

const queuedWithSchedule = computed(() =>
  posts.value
    .filter(post => ["queued", "scheduled", "publishing"].includes(post.delivery_status))
    .sort((a, b) => {
      const aTime = a.scheduled_at ? new Date(a.scheduled_at).getTime() : Infinity
      const bTime = b.scheduled_at ? new Date(b.scheduled_at).getTime() : Infinity
      return aTime - bTime
    })
)

const nextPost = computed(() => queuedWithSchedule.value[0] || null)

const recentDrafts = computed(() =>
  posts.value
    .filter(post => post.delivery_status === "draft")
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 3)
)

const recentAssets = computed(() =>
  assets.value
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 4)
)

const ideaFocus = computed(() => {
  const order = ["unassigned", "todo", "in_progress", "done"]
  const labels: Record<string, string> = {
    unassigned: "Needs triage",
    todo: "Ready to plan",
    in_progress: "In progress",
    done: "Ready to publish",
  }

  return order
    .map(column => ({
      column,
      label: labels[column],
      count: ideas.value.filter(idea => idea.column === column).length,
    }))
    .filter(item => item.count > 0)
    .sort((a, b) => b.count - a.count)[0] || { column: "unassigned", label: "Needs triage", count: 0 }
})

const stats = computed(() => [
  {
    label: "Queued posts",
    value: queuedCount.value,
    tone: "brand",
    detail: nextPost.value
      ? `Next up ${formatDateTime(nextPost.value.scheduled_at || nextPost.value.created_at)}`
      : "No post scheduled yet",
  },
  {
    label: "Drafts",
    value: draftCount.value,
    tone: "amber",
    detail: draftCount.value ? "Open drafts and tighten copy before publishing" : "Nothing sitting in drafts",
  },
  {
    label: "Connected channels",
    value: connectedChannels.value.length,
    tone: "ink",
    detail: accountCount.value ? `${accountCount.value} channel${accountCount.value > 1 ? "s" : ""} in workspace` : "Connect your first channel",
  },
  {
    label: "Media assets",
    value: assetCount.value,
    tone: "soft",
    detail: assetCount.value ? "Library is ready for image-first posting" : "Upload visuals to speed up publishing",
  },
])

const quickLinks = [
  {
    title: "Build a campaign",
    text: "Upload one document and one source video, then fan out draft posts.",
    to: "/app/campaigns",
  },
  {
    title: "Start drafting",
    text: "Open the composer and move content into queue faster.",
    to: "/app/posts",
  },
  {
    title: "Review idea pipeline",
    text: "Clear the backlog and push stronger ideas to ready.",
    to: "/app/ideas",
  },
  {
    title: "Open analytics",
    text: "Track delivery health, provider reach, and stale sync windows.",
    to: "/app/analytics",
  },
  {
    title: "Review inbox",
    text: "Triage comments from published content without leaving the workspace.",
    to: "/app/inbox",
  },
  {
    title: "Manage channels",
    text: "Add or clean up connected channels before publishing.",
    to: "/app/settings",
  },
]

function formatDateTime(value?: string | null) {
  if (!value) return "Unscheduled"
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function formatDate(value?: string | null) {
  if (!value) return "No date"
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  })
}

function relativeTime(value?: string | null) {
  if (!value) return "No activity"
  const diff = Date.now() - new Date(value).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function postTitle(post: Post) {
  const text = post.caption_text?.trim()
  if (!text) return "Untitled draft"
  return text.length > 84 ? `${text.slice(0, 84)}...` : text
}

function assetTitle(asset: MediaAsset) {
  return asset.title || asset.file_name
}

function platformInitial(code: string) {
  if (code === "instagram") return "I"
  if (code === "facebook") return "F"
  return (code || "?").slice(0, 1).toUpperCase()
}

function activeQueueSlots(account: Account) {
  return (account.queue_slots || []).filter(slot => slot.is_active).length
}
</script>

<template>
  <div class="dashboard-page">
    <section class="dashboard-hero">
      <div class="dashboard-hero-copy">
        <p class="dashboard-kicker">Workspace overview</p>
        <h1>{{ workspaceName }}</h1>
        <p class="dashboard-subtitle">
          A cleaner control surface for ideas, drafts, channels, and scheduled publishing.
        </p>

        <div class="dashboard-hero-actions">
          <NuxtLink class="btn" to="/app/posts">Open publishing</NuxtLink>
          <NuxtLink class="btn secondary dashboard-ghost-btn" to="/app/ideas">Review ideas</NuxtLink>
        </div>
      </div>

      <div class="dashboard-hero-panel">
        <div class="dashboard-highlight">
          <span class="dashboard-highlight-label">Pipeline focus</span>
          <strong>{{ ideaFocus.label }}</strong>
          <p>
            {{ ideaFocus.count }}
            item{{ ideaFocus.count === 1 ? "" : "s" }}
            currently sit in the biggest bucket.
          </p>
        </div>

        <div class="dashboard-mini-stats">
          <div>
            <span>Ideas ready</span>
            <strong>{{ readyIdeasCount }}</strong>
          </div>
          <div>
            <span>Published</span>
            <strong>{{ publishedCount }}</strong>
          </div>
          <div>
            <span>Completion</span>
            <strong>{{ completionRate }}%</strong>
          </div>
        </div>
      </div>
    </section>

    <section class="dashboard-stats">
      <article
        v-for="stat in stats"
        :key="stat.label"
        class="dashboard-stat-card"
        :data-tone="stat.tone"
      >
        <span class="dashboard-stat-label">{{ stat.label }}</span>
        <strong class="dashboard-stat-value">{{ stat.value }}</strong>
        <p class="dashboard-stat-detail">{{ stat.detail }}</p>
      </article>
    </section>

    <section class="dashboard-grid">
      <article class="dashboard-panel dashboard-panel-wide">
        <div class="dashboard-panel-head">
          <div>
            <p class="dashboard-section-label">Quick actions</p>
            <h2>Move the workspace forward</h2>
          </div>
        </div>

        <div class="dashboard-actions-grid">
          <NuxtLink
            v-for="link in quickLinks"
            :key="link.to"
            :to="link.to"
            class="dashboard-action-card"
          >
            <strong>{{ link.title }}</strong>
            <span>{{ link.text }}</span>
          </NuxtLink>
        </div>
      </article>

      <article class="dashboard-panel">
        <div class="dashboard-panel-head">
          <div>
            <p class="dashboard-section-label">Next up</p>
            <h2>Publishing cadence</h2>
          </div>
        </div>

        <div v-if="nextPost" class="dashboard-next-post">
          <span class="dashboard-pill">Scheduled</span>
          <strong>{{ postTitle(nextPost) }}</strong>
          <p>{{ formatDateTime(nextPost.scheduled_at || nextPost.created_at) }}</p>
        </div>
        <div v-else class="dashboard-empty">
          No scheduled post yet. Queue one from the publishing workspace.
        </div>
      </article>

      <article class="dashboard-panel dashboard-panel-wide">
        <div class="dashboard-panel-head">
          <div>
            <p class="dashboard-section-label">Channels</p>
            <h2>Connected destinations</h2>
          </div>
          <NuxtLink to="/app/settings" class="dashboard-text-link">Manage</NuxtLink>
        </div>

        <div v-if="accounts.length" class="dashboard-channel-list">
          <div v-for="account in accounts" :key="account.id" class="dashboard-channel-row">
            <div class="dashboard-channel-meta">
              <div class="dashboard-channel-badge">{{ platformInitial(account.channel_code || account.provider_code) }}</div>
              <div>
                <strong>{{ account.display_name }}</strong>
                <p>{{ account.channel_name || account.provider_code }} · {{ activeQueueSlots(account) }} queue slot{{ activeQueueSlots(account) === 1 ? "" : "s" }}</p>
              </div>
            </div>
            <span class="dashboard-status" :data-status="account.status">{{ account.status }}</span>
          </div>
        </div>
        <div v-else class="dashboard-empty">
          No channels connected yet. Add one before you start scheduling posts.
        </div>
      </article>

      <article class="dashboard-panel">
        <div class="dashboard-panel-head">
          <div>
            <p class="dashboard-section-label">Recent drafts</p>
            <h2>Needs polish</h2>
          </div>
          <NuxtLink to="/app/posts?tab=drafts" class="dashboard-text-link">Open drafts</NuxtLink>
        </div>

        <div v-if="recentDrafts.length" class="dashboard-list">
          <div v-for="post in recentDrafts" :key="post.id" class="dashboard-list-row">
            <strong>{{ postTitle(post) }}</strong>
            <span>{{ relativeTime(post.created_at) }}</span>
          </div>
        </div>
        <div v-else class="dashboard-empty">
          Draft inbox is clear.
        </div>
      </article>

      <article class="dashboard-panel">
        <div class="dashboard-panel-head">
          <div>
            <p class="dashboard-section-label">Media library</p>
            <h2>Latest uploads</h2>
          </div>
          <NuxtLink to="/app/media" class="dashboard-text-link">Open library</NuxtLink>
        </div>

        <div v-if="recentAssets.length" class="dashboard-list">
          <div v-for="asset in recentAssets" :key="asset.id" class="dashboard-list-row">
            <strong>{{ assetTitle(asset) }}</strong>
            <span>{{ formatDate(asset.created_at) }}</span>
          </div>
        </div>
        <div v-else class="dashboard-empty">
          No media uploaded yet.
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.dashboard-page {
  padding: 32px;
}

.dashboard-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  gap: 22px;
  margin-bottom: 22px;
}

.dashboard-hero-copy,
.dashboard-hero-panel,
.dashboard-panel,
.dashboard-stat-card {
  border: 1px solid var(--line-soft);
  border-radius: 28px;
  background: var(--panel);
  box-shadow: var(--shadow-panel);
}

.dashboard-hero-copy {
  padding: 34px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(244, 248, 252, 0.94)),
    var(--panel);
}

.dashboard-kicker,
.dashboard-section-label {
  margin: 0 0 10px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--brand);
}

.dashboard-hero-copy h1,
.dashboard-panel h2 {
  margin: 0;
  color: var(--ink);
}

.dashboard-hero-copy h1 {
  font-size: clamp(34px, 4vw, 52px);
  line-height: 1.02;
  letter-spacing: -0.04em;
}

.dashboard-subtitle {
  max-width: 640px;
  margin: 14px 0 0;
  font-size: 15px;
  line-height: 1.7;
  color: var(--muted);
}

.dashboard-hero-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.dashboard-ghost-btn {
  background: var(--surface-muted);
}

.dashboard-hero-panel {
  padding: 22px;
  background:
    linear-gradient(180deg, rgba(111, 140, 128, 0.96), rgba(95, 127, 114, 0.98));
  color: #fff8ec;
}

.dashboard-highlight {
  padding: 18px 18px 20px;
  border-radius: 22px;
  background: rgba(255, 248, 236, 0.08);
  border: 1px solid rgba(255, 248, 236, 0.08);
}

.dashboard-highlight-label {
  display: block;
  margin-bottom: 10px;
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 248, 236, 0.66);
}

.dashboard-highlight strong {
  display: block;
  font-size: 28px;
  line-height: 1.05;
}

.dashboard-highlight p {
  margin: 10px 0 0;
  font-size: 14px;
  line-height: 1.6;
  color: rgba(255, 248, 236, 0.76);
}

.dashboard-mini-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.dashboard-mini-stats div {
  padding: 14px 12px;
  border-radius: 18px;
  background: rgba(255, 248, 236, 0.05);
  border: 1px solid rgba(255, 248, 236, 0.08);
}

.dashboard-mini-stats span {
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(255, 248, 236, 0.62);
}

.dashboard-mini-stats strong {
  font-size: 22px;
}

.dashboard-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 22px;
}

.dashboard-stat-card {
  padding: 22px;
}

.dashboard-stat-card[data-tone="brand"] {
  background: linear-gradient(180deg, rgba(233, 248, 241, 0.92), rgba(255, 255, 255, 0.98));
}

.dashboard-stat-card[data-tone="amber"] {
  background: linear-gradient(180deg, rgba(247, 249, 252, 0.96), rgba(255, 255, 255, 0.98));
}

.dashboard-stat-card[data-tone="ink"] {
  background: linear-gradient(180deg, rgba(239, 244, 242, 0.95), rgba(255, 255, 255, 0.98));
}

.dashboard-stat-card[data-tone="soft"] {
  background: linear-gradient(180deg, rgba(243, 247, 251, 0.96), rgba(255, 255, 255, 0.98));
}

.dashboard-stat-label {
  display: block;
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
}

.dashboard-stat-value {
  display: block;
  font-size: 34px;
  line-height: 1;
  letter-spacing: -0.04em;
  color: var(--ink);
}

.dashboard-stat-detail {
  margin: 12px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--muted);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 18px;
}

.dashboard-panel {
  grid-column: span 4;
  padding: 22px;
}

.dashboard-panel-wide {
  grid-column: span 8;
}

.dashboard-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.dashboard-text-link {
  font-size: 13px;
  font-weight: 700;
  color: var(--brand);
}

.dashboard-actions-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.dashboard-action-card {
  display: grid;
  gap: 8px;
  padding: 18px;
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff, #f6f8fb);
  border: 1px solid var(--line-soft);
  transition: transform 0.14s ease, box-shadow 0.14s ease, border-color 0.14s ease;
}

.dashboard-action-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(19, 38, 27, 0.08);
  border-color: rgba(127, 162, 147, 0.22);
}

.dashboard-action-card strong {
  font-size: 16px;
}

.dashboard-action-card span,
.dashboard-channel-row p,
.dashboard-next-post p,
.dashboard-empty {
  font-size: 13px;
  line-height: 1.6;
  color: var(--muted);
}

.dashboard-next-post {
  display: grid;
  gap: 10px;
  padding: 18px;
  border-radius: 22px;
  background: var(--surface-muted);
  border: 1px solid var(--line-soft);
}

.dashboard-next-post strong {
  font-size: 20px;
  line-height: 1.35;
}

.dashboard-pill {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--brand-strong);
  background: rgba(127, 162, 147, 0.18);
}

.dashboard-channel-list,
.dashboard-list {
  display: grid;
  gap: 12px;
}

.dashboard-channel-row,
.dashboard-list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 18px;
  background: var(--surface-muted);
  border: 1px solid var(--line-soft);
}

.dashboard-channel-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.dashboard-channel-meta strong,
.dashboard-list-row strong {
  display: block;
  color: var(--ink);
}

.dashboard-channel-meta p,
.dashboard-list-row span {
  margin: 2px 0 0;
}

.dashboard-channel-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(111, 140, 128, 0.96), rgba(127, 162, 147, 0.98));
  color: #fff8ec;
  font-size: 13px;
  font-weight: 800;
}

.dashboard-status {
  border-radius: 999px;
  padding: 7px 10px;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: rgba(19, 38, 27, 0.08);
  color: var(--ink);
}

.dashboard-status[data-status="active"],
.dashboard-status[data-status="connected"] {
  background: rgba(127, 162, 147, 0.18);
  color: var(--brand-strong);
}

.dashboard-empty {
  padding: 18px;
  border-radius: 20px;
  background: var(--surface-muted);
  border: 1px dashed rgba(19, 38, 27, 0.12);
}

@media (max-width: 1100px) {
  .dashboard-hero,
  .dashboard-stats {
    grid-template-columns: 1fr 1fr;
  }

  .dashboard-grid {
    grid-template-columns: 1fr 1fr;
  }

  .dashboard-panel,
  .dashboard-panel-wide {
    grid-column: auto;
  }

  .dashboard-actions-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .dashboard-page {
    padding: 20px;
  }

  .dashboard-hero,
  .dashboard-stats,
  .dashboard-grid,
  .dashboard-mini-stats {
    grid-template-columns: 1fr;
  }

  .dashboard-hero-copy,
  .dashboard-hero-panel,
  .dashboard-panel,
  .dashboard-stat-card {
    border-radius: 24px;
  }

  .dashboard-hero-actions,
  .dashboard-list-row,
  .dashboard-channel-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
