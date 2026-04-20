<script setup lang="ts">
definePageMeta({ middleware: "auth" })

type Post = {
  id: string
  caption_text: string
  delivery_status: string
  scheduled_at: string | null
  published_at: string | null
  created_at: string
  media_items: Array<{ id: string }>
  targets: Array<{ social_account: string }>
}

type SocialAccount = {
  id: string
  display_name: string
}

const { data: posts } = useAsyncData(
  "calendar-posts",
  () => apiFetch<Post[]>("/posts/"),
  { lazy: true, default: () => [] }
)

const { data: accounts } = useAsyncData(
  "calendar-accounts",
  () => apiFetch<SocialAccount[]>("/accounts/"),
  { lazy: true, default: () => [] }
)

function parseTime(value?: string | null) {
  if (!value) return null
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? null : time
}

const upcoming = computed(() =>
  posts.value
    .filter((post) => ["queued", "scheduled", "publishing"].includes(post.delivery_status))
    .sort((a, b) => {
      const aTime = parseTime(a.scheduled_at) ?? Number.POSITIVE_INFINITY
      const bTime = parseTime(b.scheduled_at) ?? Number.POSITIVE_INFINITY
      return aTime - bTime
    })
)

const scheduledUpcoming = computed(() =>
  upcoming.value.filter((post) => parseTime(post.scheduled_at) !== null)
)

const history = computed(() =>
  posts.value
    .filter((post) => ["published", "failed", "canceled"].includes(post.delivery_status))
    .sort((a, b) => {
      const aTime = parseTime(a.published_at || a.created_at) ?? 0
      const bTime = parseTime(b.published_at || b.created_at) ?? 0
      return bTime - aTime
    })
)

const weekDays = computed(() => {
  const base = startOfWeek(new Date())
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(base)
    date.setDate(base.getDate() + index)
    const items = scheduledUpcoming.value.filter((post) => {
      return sameDay(new Date(post.scheduled_at as string), date)
    })
    return { date, items }
  })
})

function startOfWeek(date: Date) {
  const copy = new Date(date)
  const day = copy.getDay()
  const diff = day === 0 ? -6 : 1 - day
  copy.setDate(copy.getDate() + diff)
  copy.setHours(0, 0, 0, 0)
  return copy
}

function sameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

function accountName(post: Post) {
  const id = post.targets[0]?.social_account
  return accounts.value.find((account) => account.id === id)?.display_name || "No page"
}

function editLink(post: Post) {
  return {
    path: "/app/posts",
    query: {
      tab: ["published", "failed", "canceled"].includes(post.delivery_status) ? "sent" : "queue",
      account: post.targets[0]?.social_account,
      post: post.id,
    },
  }
}

function timeLabel(post: Post) {
  if (!post.scheduled_at) return "Unscheduled"
  return new Date(post.scheduled_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
}

function fullDateLabel(value?: string | null) {
  if (!value) return "Unscheduled"
  return new Date(value).toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function postTitle(post: Post) {
  const text = post.caption_text?.trim()
  if (!text) return "Untitled post"
  return text.length > 92 ? `${text.slice(0, 92)}...` : text
}

function statusTone(status: string) {
  if (status === "published") return "success"
  if (status === "failed") return "danger"
  if (status === "scheduled" || status === "queued") return "amber"
  if (status === "publishing") return "brand"
  return "muted"
}
</script>

<template>
  <div class="calendar-page">
    <section class="calendar-hero">
      <div>
        <p class="calendar-kicker">Publishing calendar</p>
        <h1>Weekly schedule and history</h1>
        <p class="calendar-subtitle">
          See what is queued next, what has a locked schedule, and jump straight back into the publishing workspace.
        </p>
      </div>
      <div class="calendar-summary">
        <div>
          <span>Upcoming</span>
          <strong>{{ scheduledUpcoming.length }}</strong>
        </div>
        <div>
          <span>Published</span>
          <strong>{{ history.filter((post) => post.delivery_status === "published").length }}</strong>
        </div>
      </div>
    </section>

    <section class="calendar-board">
      <article class="calendar-panel calendar-panel-wide">
        <div class="calendar-panel-head">
          <div>
            <p class="calendar-section-label">This week</p>
            <h2>Upcoming timeline</h2>
          </div>
        </div>

        <div class="week-grid">
          <div v-for="day in weekDays" :key="day.date.toISOString()" class="day-column">
            <div class="day-head">
              <strong>{{ day.date.toLocaleDateString("en-US", { weekday: "short" }) }}</strong>
              <span>{{ day.date.toLocaleDateString("en-US", { month: "short", day: "numeric" }) }}</span>
            </div>

            <div v-if="day.items.length" class="day-cards">
              <NuxtLink v-for="post in day.items" :key="post.id" :to="editLink(post)" class="timeline-card">
                <span class="calendar-status" :data-tone="statusTone(post.delivery_status)">{{ post.delivery_status }}</span>
                <strong>{{ postTitle(post) }}</strong>
                <div class="timeline-meta">
                  <span>{{ accountName(post) }}</span>
                  <span>{{ timeLabel(post) }}</span>
                  <span>{{ post.media_items.length }} media</span>
                </div>
              </NuxtLink>
            </div>
            <div v-else class="day-empty">No posts</div>
          </div>
        </div>
      </article>

      <article class="calendar-panel">
        <div class="calendar-panel-head">
          <div>
            <p class="calendar-section-label">Queue health</p>
            <h2>Next actions</h2>
          </div>
        </div>

        <div class="action-list">
          <NuxtLink v-for="post in upcoming.slice(0, 5)" :key="post.id" :to="editLink(post)" class="action-row">
            <strong>{{ postTitle(post) }}</strong>
            <span>{{ fullDateLabel(post.scheduled_at) }}</span>
          </NuxtLink>
          <div v-if="!upcoming.length" class="calendar-empty">Nothing queued or scheduled yet.</div>
        </div>
      </article>

      <article class="calendar-panel calendar-panel-wide">
        <div class="calendar-panel-head">
          <div>
            <p class="calendar-section-label">History</p>
            <h2>Published and delivery results</h2>
          </div>
        </div>

        <div v-if="history.length" class="history-list">
          <NuxtLink v-for="post in history.slice(0, 12)" :key="post.id" :to="editLink(post)" class="history-row">
            <div>
              <span class="calendar-status" :data-tone="statusTone(post.delivery_status)">{{ post.delivery_status }}</span>
              <strong>{{ postTitle(post) }}</strong>
            </div>
            <div class="history-meta">
              <span>{{ accountName(post) }}</span>
              <span>{{ fullDateLabel(post.published_at || post.created_at) }}</span>
            </div>
          </NuxtLink>
        </div>
        <div v-else class="calendar-empty">No published history yet.</div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.calendar-page {
  padding: 30px;
}

.calendar-hero,
.calendar-panel {
  border-radius: 28px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-panel);
}

.calendar-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 26px;
  margin-bottom: 18px;
}

.calendar-kicker,
.calendar-section-label {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--brand);
}

.calendar-hero h1,
.calendar-panel h2 {
  margin: 0;
  color: var(--ink);
}

.calendar-subtitle {
  margin: 10px 0 0;
  max-width: 760px;
  color: var(--muted);
  line-height: 1.7;
}

.calendar-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  min-width: 240px;
}

.calendar-summary div {
  padding: 14px;
  border-radius: 18px;
  background: var(--surface);
  border: 1px solid var(--line-soft);
}

.calendar-summary span,
.day-head span,
.timeline-meta,
.history-meta,
.action-row span,
.day-empty,
.calendar-empty {
  color: var(--muted);
  font-size: 12px;
}

.calendar-summary strong {
  display: block;
  margin-top: 6px;
  font-size: 28px;
}

.calendar-board {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 18px;
}

.calendar-panel {
  grid-column: span 4;
  padding: 22px;
}

.calendar-panel-wide {
  grid-column: span 8;
}

.calendar-panel-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.week-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
}

.day-column {
  display: grid;
  gap: 10px;
  align-content: start;
}

.day-head {
  display: grid;
  gap: 4px;
  padding-bottom: 6px;
}

.day-head strong {
  font-size: 13px;
}

.day-cards,
.action-list,
.history-list {
  display: grid;
  gap: 10px;
}

.timeline-card,
.action-row,
.history-row {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: 18px;
  border: 1px solid var(--line-soft);
  background: var(--surface);
  transition: transform 0.14s ease, border-color 0.14s ease, box-shadow 0.14s ease;
}

.timeline-card:hover,
.action-row:hover,
.history-row:hover {
  transform: translateY(-1px);
  border-color: rgba(127, 162, 147, 0.24);
  box-shadow: 0 12px 26px rgba(19, 38, 27, 0.08);
}

.timeline-card strong,
.history-row strong,
.action-row strong {
  color: var(--ink);
  line-height: 1.45;
}

.timeline-meta,
.history-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.history-row,
.action-row {
  grid-template-columns: 1fr auto;
  align-items: center;
}

.history-row div:first-child {
  display: grid;
  gap: 8px;
}

.calendar-status {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  border-radius: 999px;
  padding: 6px 10px;
  border: 1px solid var(--line-soft);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.calendar-status[data-tone="success"] {
  background: #eef4f1;
  color: var(--brand-strong);
}

.calendar-status[data-tone="amber"] {
  background: #f3f6f9;
  color: #5f6b64;
}

.calendar-status[data-tone="brand"] {
  background: #eef4f1;
  color: #4d665c;
}

.calendar-status[data-tone="danger"] {
  background: #f3f6f9;
  color: #6f7a74;
}

.calendar-status[data-tone="muted"] {
  background: #f3f6f9;
  color: #58625c;
}

.day-empty,
.calendar-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100px;
  border: 1px dashed var(--line);
  border-radius: 18px;
  background: var(--surface);
  text-align: center;
}

@media (max-width: 1200px) {
  .calendar-board {
    grid-template-columns: 1fr 1fr;
  }

  .calendar-panel,
  .calendar-panel-wide {
    grid-column: auto;
  }

  .week-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .calendar-page {
    padding: 20px;
  }

  .calendar-hero,
  .calendar-summary,
  .calendar-board,
  .week-grid,
  .history-row,
  .action-row {
    grid-template-columns: 1fr;
  }

  .calendar-hero {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
