<script setup lang="ts">
definePageMeta({ middleware: "auth" })

type AnalyticsSummary = {
  connected_channels: number
  active_queue_slots: number
  published_attempts: number
  failed_attempts: number
  success_rate: number
}

type AnalyticsSeriesPoint = {
  date: string
  published_attempts: number
  failed_attempts: number
}

type AnalyticsChannel = {
  account_id: string
  display_name: string
  provider_code: string
  channel_code: string
  active_queue_slots: number
  published_attempts: number
  failed_attempts: number
  success_rate: number
  last_activity_at: string | null
}

type AnalyticsFailure = {
  post_id: string
  post_target_id: string
  account_id: string
  account_name: string
  finished_at: string
  error_detail: string
}

type ProviderSync = {
  status: string
  last_success_at: string | null
  last_error: string
  freshness_minutes: number | null
}

type ProviderSummary = {
  impressions: number
  reach: number
  engagement: number
}

type ProviderSeriesPoint = {
  date: string
  impressions: number
  reach: number
  engagement: number
}

type ProviderChannel = {
  account_id: string
  display_name: string
  channel_code: string
  impressions: number
  reach: number
  engagement: number
  synced_at: string | null
  sync_status: string
}

type AnalyticsResponse = {
  source: string
  generated_at: string
  filters: {
    range: "7d" | "30d" | "90d"
    account_id: string | null
    workspace_timezone: string
  }
  summary: AnalyticsSummary
  series: AnalyticsSeriesPoint[]
  channels: AnalyticsChannel[]
  recent_failures: AnalyticsFailure[]
  provider_sync: ProviderSync
  provider_summary: ProviderSummary
  provider_series: ProviderSeriesPoint[]
  provider_channels: ProviderChannel[]
}

type AccountOption = {
  id: string
  display_name: string
  provider_code: string
  channel_code?: string
}

type AnalyticsViewMode = "delivery" | "provider"

const route = useRoute()
const router = useRouter()
const sidebarAccounts = useNuxtData<AccountOption[]>("sidebar-accounts")
const rangeOptions: Array<AnalyticsResponse["filters"]["range"]> = ["7d", "30d", "90d"]
const viewOptions: AnalyticsViewMode[] = ["delivery", "provider"]
const providerSyncPending = ref(false)
const providerSyncMessage = ref("")

const emptyAnalytics = (): AnalyticsResponse => ({
  source: "internal",
  generated_at: new Date().toISOString(),
  filters: {
    range: "30d",
    account_id: null,
    workspace_timezone: "UTC",
  },
  summary: {
    connected_channels: 0,
    active_queue_slots: 0,
    published_attempts: 0,
    failed_attempts: 0,
    success_rate: 0,
  },
  series: [],
  channels: [],
  recent_failures: [],
  provider_sync: {
    status: "idle",
    last_success_at: null,
    last_error: "",
    freshness_minutes: null,
  },
  provider_summary: {
    impressions: 0,
    reach: 0,
    engagement: 0,
  },
  provider_series: [],
  provider_channels: [],
})

const selectedView = computed<AnalyticsViewMode>(() => {
  const value = route.query.tab
  return typeof value === "string" && viewOptions.includes(value as AnalyticsViewMode)
    ? value as AnalyticsViewMode
    : "delivery"
})

const selectedRange = computed<AnalyticsResponse["filters"]["range"]>(() => {
  const value = route.query.range
  return typeof value === "string" && rangeOptions.includes(value as AnalyticsResponse["filters"]["range"])
    ? value as AnalyticsResponse["filters"]["range"]
    : "30d"
})

const selectedAccountId = computed(() => {
  const value = route.query.account
  return typeof value === "string" ? value : ""
})

const requestPath = computed(() => {
  const params = new URLSearchParams()
  params.set("range", selectedRange.value)
  if (selectedAccountId.value) params.set("account", selectedAccountId.value)
  return `/analytics/?${params.toString()}`
})

const { data: analytics, pending, error, refresh } = useAsyncData(
  "analytics-page",
  () => apiFetch<AnalyticsResponse>(requestPath.value),
  {
    default: emptyAnalytics,
    watch: [requestPath],
    server: false,
  }
)

const accountOptions = computed(() => {
  const items = sidebarAccounts.data.value || []
  const fallback = [
    ...analytics.value.channels.map((item) => ({
      id: item.account_id,
      display_name: item.display_name,
      provider_code: item.provider_code,
      channel_code: item.channel_code,
    })),
    ...analytics.value.provider_channels
      .filter((item) => !analytics.value.channels.some((channel) => channel.account_id === item.account_id))
      .map((item) => ({
        id: item.account_id,
        display_name: item.display_name,
        provider_code: item.channel_code,
        channel_code: item.channel_code,
      })),
  ]
  return (items.length ? items : fallback).map((item) => ({
    id: item.id,
    label: item.display_name,
    platform: platformName(item.channel_code || item.provider_code),
  }))
})

const deliverySummaryCards = computed(() => [
  {
    label: "Published",
    value: analytics.value.summary.published_attempts,
    detail: "Successful publish attempts",
    tone: "success",
  },
  {
    label: "Failed",
    value: analytics.value.summary.failed_attempts,
    detail: "Attempts that need follow-up",
    tone: "danger",
  },
  {
    label: "Success rate",
    value: `${analytics.value.summary.success_rate}%`,
    detail: "Published vs failed attempts",
    tone: "brand",
  },
  {
    label: "Connected channels",
    value: analytics.value.summary.connected_channels,
    detail: `${analytics.value.summary.active_queue_slots} active queue slots`,
    tone: "ink",
  },
])

const providerSummaryCards = computed(() => [
  {
    label: "Impressions",
    value: analytics.value.provider_summary.impressions,
    detail: "Provider-reported impressions",
    tone: "brand",
  },
  {
    label: "Reach",
    value: analytics.value.provider_summary.reach,
    detail: "Unique accounts reached",
    tone: "success",
  },
  {
    label: "Engagement",
    value: analytics.value.provider_summary.engagement,
    detail: "Normalized engagement signal",
    tone: "ink",
  },
  {
    label: "Sync status",
    value: syncStatusLabel(analytics.value.provider_sync.status),
    detail: providerFreshnessLabel(analytics.value.provider_sync),
    tone: analytics.value.provider_sync.status === "error" ? "danger" : "soft",
  },
])

const maxDeliverySeriesValue = computed(() =>
  Math.max(
    1,
    ...analytics.value.series.map((item) => Math.max(item.published_attempts, item.failed_attempts))
  )
)

const maxProviderSeriesValue = computed(() =>
  Math.max(
    1,
    ...analytics.value.provider_series.map((item) => Math.max(item.impressions, item.reach, item.engagement))
  )
)

const hasDeliverySeriesData = computed(() =>
  analytics.value.series.some((item) => item.published_attempts > 0 || item.failed_attempts > 0)
)

const hasProviderSeriesData = computed(() =>
  analytics.value.provider_series.some((item) => item.impressions > 0 || item.reach > 0 || item.engagement > 0)
)

function updateQuery(patch: Record<string, string | undefined>) {
  router.replace({ query: { ...route.query, ...patch } })
}

function setView(view: AnalyticsViewMode) {
  updateQuery({ tab: view === "delivery" ? undefined : view })
}

function setRange(nextRange: AnalyticsResponse["filters"]["range"]) {
  updateQuery({ range: nextRange === "30d" ? undefined : nextRange })
}

function setAccount(nextAccountId: string) {
  updateQuery({ account: nextAccountId || undefined })
}

function chartHeight(value: number, maxValue: number) {
  return `${Math.max(8, Math.round((value / Math.max(1, maxValue)) * 100))}%`
}

function formatDayLabel(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  })
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

function formatCompactNumber(value: number) {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value)
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

function syncStatusLabel(status: string) {
  const labels: Record<string, string> = {
    idle: "Idle",
    running: "Running",
    success: "Healthy",
    error: "Needs attention",
    partial: "Partial",
  }
  return labels[status] ?? status
}

function providerFreshnessLabel(sync: ProviderSync) {
  if (sync.status === "running") return "Refresh in progress"
  if (typeof sync.freshness_minutes === "number") return `Last success ${sync.freshness_minutes} minutes ago`
  if (sync.last_error) return sync.last_error
  return "No provider sync recorded yet"
}

async function queueProviderSync() {
  providerSyncPending.value = true
  providerSyncMessage.value = ""
  try {
    await apiFetch("/analytics/provider-sync/", {
      method: "POST",
      body: selectedAccountId.value ? { account: selectedAccountId.value } : {},
    })
    providerSyncMessage.value = "Provider refresh queued. Background workers will update Meta insights."
    await refresh()
  } catch (syncError) {
    providerSyncMessage.value = extractApiError(syncError, "Could not queue provider refresh.")
  } finally {
    providerSyncPending.value = false
  }
}
</script>

<template>
  <div class="analytics-page">
    <section class="analytics-shell">
      <header class="analytics-header">
        <div class="analytics-header-copy">
          <p class="analytics-kicker">Analytics</p>
          <h1>Workspace performance</h1>
          <p class="analytics-subtitle">
            Track delivery health and synced Meta provider insights by day and by channel.
          </p>
        </div>

        <div class="analytics-controls">
          <div class="range-control" role="tablist" aria-label="Analytics mode">
            <button
              v-for="view in viewOptions"
              :key="view"
              class="range-pill"
              :class="{ active: selectedView === view }"
              @click="setView(view)"
            >
              {{ view === "delivery" ? "Delivery" : "Provider" }}
            </button>
          </div>

          <div class="range-control" role="tablist" aria-label="Analytics range">
            <button
              v-for="range in rangeOptions"
              :key="range"
              class="range-pill"
              :class="{ active: selectedRange === range }"
              @click="setRange(range)"
            >
              {{ range }}
            </button>
          </div>

          <label class="channel-select-wrap">
            <span>Channel</span>
            <select class="channel-select" :value="selectedAccountId" @change="setAccount(($event.target as HTMLSelectElement).value)">
              <option value="">All channels</option>
              <option v-for="option in accountOptions" :key="option.id" :value="option.id">
                {{ option.label }} - {{ option.platform }}
              </option>
            </select>
          </label>
        </div>
      </header>

      <p v-if="error" class="analytics-error">{{ extractApiError(error, "Could not load analytics.") }}</p>
      <p v-if="providerSyncMessage" class="analytics-note">{{ providerSyncMessage }}</p>

      <template v-if="selectedView === 'delivery'">
        <section class="analytics-summary">
          <article
            v-for="card in deliverySummaryCards"
            :key="card.label"
            class="analytics-card summary-card"
            :data-tone="card.tone"
          >
            <span>{{ card.label }}</span>
            <strong>{{ card.value }}</strong>
            <small>{{ card.detail }}</small>
          </article>
        </section>

        <section class="analytics-grid">
          <article class="analytics-card analytics-panel analytics-panel-wide">
            <div class="analytics-panel-head">
              <div>
                <p class="section-label">Daily trend</p>
                <h2>Published vs failed</h2>
              </div>
              <small>{{ analytics.filters.workspace_timezone }} - Updated {{ formatDateTime(analytics.generated_at) }}</small>
            </div>

            <div v-if="pending" class="analytics-empty">Loading analytics...</div>
            <div v-else-if="!hasDeliverySeriesData" class="analytics-empty">
              No publish attempts in this range yet.
            </div>
            <div v-else class="chart-shell">
              <div
                v-for="point in analytics.series"
                :key="point.date"
                class="chart-column"
              >
                <div class="chart-bars">
                  <span
                    class="chart-bar published"
                    :style="{ height: chartHeight(point.published_attempts, maxDeliverySeriesValue) }"
                    :title="`${point.published_attempts} published`"
                  />
                  <span
                    class="chart-bar failed"
                    :style="{ height: chartHeight(point.failed_attempts, maxDeliverySeriesValue) }"
                    :title="`${point.failed_attempts} failed`"
                  />
                </div>
                <small>{{ formatDayLabel(point.date) }}</small>
              </div>
            </div>
          </article>

          <article class="analytics-card analytics-panel">
            <div class="analytics-panel-head">
              <div>
                <p class="section-label">Failures</p>
                <h2>Recent failures</h2>
              </div>
            </div>

            <div v-if="!analytics.recent_failures.length" class="analytics-empty">
              No recent failures in this range.
            </div>
            <div v-else class="failure-list">
              <NuxtLink
                v-for="failure in analytics.recent_failures"
                :key="failure.post_target_id"
                class="failure-row"
                :to="`/app/posts?post=${failure.post_id}`"
              >
                <div>
                  <strong>{{ failure.account_name }}</strong>
                  <p>{{ failure.error_detail }}</p>
                </div>
                <span>{{ formatDateTime(failure.finished_at) }}</span>
              </NuxtLink>
            </div>
          </article>

          <article class="analytics-card analytics-panel analytics-panel-full">
            <div class="analytics-panel-head">
              <div>
                <p class="section-label">Channels</p>
                <h2>Channel performance</h2>
              </div>
            </div>

            <div v-if="!analytics.channels.length" class="analytics-empty">
              No connected channels match this filter.
            </div>
            <div v-else class="channel-table">
              <div class="channel-table-head">
                <span>Channel</span>
                <span>Published</span>
                <span>Failed</span>
                <span>Success</span>
                <span>Last activity</span>
              </div>

              <div
                v-for="channel in analytics.channels"
                :key="channel.account_id"
                class="channel-table-row"
              >
                <div class="channel-meta">
                  <div class="channel-badge">{{ providerBadge(channel.channel_code || channel.provider_code) }}</div>
                  <div>
                    <strong>{{ channel.display_name }}</strong>
                    <p>{{ platformName(channel.channel_code || channel.provider_code) }} - {{ channel.active_queue_slots }} queue slots</p>
                  </div>
                </div>
                <span>{{ channel.published_attempts }}</span>
                <span>{{ channel.failed_attempts }}</span>
                <span>{{ channel.success_rate }}%</span>
                <span>{{ formatDateTime(channel.last_activity_at) }}</span>
              </div>
            </div>
          </article>
        </section>
      </template>

      <template v-else>
        <section class="analytics-summary">
          <article
            v-for="card in providerSummaryCards"
            :key="card.label"
            class="analytics-card summary-card"
            :data-tone="card.tone"
          >
            <span>{{ card.label }}</span>
            <strong>{{ card.label === 'Sync status' ? card.value : formatCompactNumber(Number(card.value)) }}</strong>
            <small>{{ card.detail }}</small>
          </article>
        </section>

        <section class="analytics-grid">
          <article class="analytics-card analytics-panel analytics-panel-wide">
            <div class="analytics-panel-head">
              <div>
                <p class="section-label">Provider trend</p>
                <h2>Meta daily insights</h2>
              </div>
              <div class="provider-actions">
                <small>{{ syncStatusLabel(analytics.provider_sync.status) }} - {{ formatDateTime(analytics.provider_sync.last_success_at) }}</small>
                <button class="sync-button" type="button" :disabled="providerSyncPending" @click="queueProviderSync">
                  {{ providerSyncPending ? "Queueing..." : "Refresh provider data" }}
                </button>
              </div>
            </div>

            <div v-if="pending" class="analytics-empty">Loading analytics...</div>
            <div v-else-if="analytics.provider_sync.last_error" class="analytics-empty analytics-empty-danger">
              {{ analytics.provider_sync.last_error }}
            </div>
            <div v-else-if="!hasProviderSeriesData" class="analytics-empty">
              No provider insights have been synced for this range yet.
            </div>
            <div v-else class="chart-shell provider-chart-shell">
              <div
                v-for="point in analytics.provider_series"
                :key="point.date"
                class="chart-column"
              >
                <div class="chart-bars provider-bars">
                  <span
                    class="chart-bar provider-impressions"
                    :style="{ height: chartHeight(point.impressions, maxProviderSeriesValue) }"
                    :title="`${point.impressions} impressions`"
                  />
                  <span
                    class="chart-bar provider-reach"
                    :style="{ height: chartHeight(point.reach, maxProviderSeriesValue) }"
                    :title="`${point.reach} reach`"
                  />
                  <span
                    class="chart-bar provider-engagement"
                    :style="{ height: chartHeight(point.engagement, maxProviderSeriesValue) }"
                    :title="`${point.engagement} engagement`"
                  />
                </div>
                <small>{{ formatDayLabel(point.date) }}</small>
              </div>
            </div>
          </article>

          <article class="analytics-card analytics-panel">
            <div class="analytics-panel-head">
              <div>
                <p class="section-label">Sync health</p>
                <h2>Provider sync</h2>
              </div>
            </div>

            <div class="sync-health-card">
              <strong>{{ syncStatusLabel(analytics.provider_sync.status) }}</strong>
              <p>{{ providerFreshnessLabel(analytics.provider_sync) }}</p>
              <small v-if="analytics.provider_sync.last_success_at">
                Last success {{ formatDateTime(analytics.provider_sync.last_success_at) }}
              </small>
            </div>
          </article>

          <article class="analytics-card analytics-panel analytics-panel-full">
            <div class="analytics-panel-head">
              <div>
                <p class="section-label">Channels</p>
                <h2>Provider channel insights</h2>
              </div>
            </div>

            <div v-if="!analytics.provider_channels.length" class="analytics-empty">
              Provider insights are available for Meta Facebook Pages and Instagram Business accounts after sync.
            </div>
            <div v-else class="channel-table">
              <div class="channel-table-head provider-table-head">
                <span>Channel</span>
                <span>Impressions</span>
                <span>Reach</span>
                <span>Engagement</span>
                <span>Status</span>
              </div>

              <div
                v-for="channel in analytics.provider_channels"
                :key="channel.account_id"
                class="channel-table-row"
              >
                <div class="channel-meta">
                  <div class="channel-badge">{{ providerBadge(channel.channel_code) }}</div>
                  <div>
                    <strong>{{ channel.display_name }}</strong>
                    <p>{{ platformName(channel.channel_code) }} - synced {{ formatDateTime(channel.synced_at) }}</p>
                  </div>
                </div>
                <span>{{ formatCompactNumber(channel.impressions) }}</span>
                <span>{{ formatCompactNumber(channel.reach) }}</span>
                <span>{{ formatCompactNumber(channel.engagement) }}</span>
                <span>{{ syncStatusLabel(channel.sync_status) }}</span>
              </div>
            </div>
          </article>
        </section>
      </template>
    </section>
  </div>
</template>

<style scoped>
.analytics-page {
  padding: 28px;
}

.analytics-shell {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  gap: 20px;
}

.analytics-header,
.analytics-card {
  border: 1px solid var(--line-soft);
  border-radius: 20px;
  background: var(--panel);
  box-shadow: var(--shadow-panel);
}

.analytics-header {
  padding: 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
}

.analytics-header-copy,
.channel-select-wrap,
.provider-actions {
  display: grid;
  gap: 8px;
}

.analytics-kicker,
.section-label {
  margin: 0;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}

.analytics-header h1,
.analytics-panel h2 {
  margin: 0;
  color: var(--ink);
}

.analytics-subtitle,
.analytics-panel-head small,
.summary-card span,
.summary-card small,
.failure-row p,
.channel-meta p,
.analytics-empty,
.channel-select-wrap span,
.sync-health-card p,
.sync-health-card small,
.analytics-note {
  color: var(--muted);
}

.analytics-controls {
  display: grid;
  gap: 12px;
  justify-items: end;
}

.range-control {
  display: inline-flex;
  gap: 6px;
  padding: 4px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--surface-muted);
}

.range-pill,
.sync-button {
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-weight: 700;
  cursor: pointer;
}

.range-pill.active {
  background: var(--panel);
  color: var(--ink);
  box-shadow: var(--shadow-soft);
}

.sync-button {
  border: 1px solid var(--line);
  background: var(--surface-muted);
  color: var(--ink);
}

.sync-button:disabled {
  opacity: 0.65;
  cursor: wait;
}

.channel-select {
  min-width: 240px;
  min-height: 40px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: var(--input-bg);
  color: var(--ink);
}

.analytics-error {
  margin: 0;
  color: #a02e22;
}

.analytics-note {
  margin: 0;
}

.analytics-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  padding: 20px;
  display: grid;
  gap: 10px;
}

.summary-card strong {
  font-size: 34px;
  line-height: 1;
  color: var(--ink);
}

.summary-card[data-tone="success"] {
  background: linear-gradient(180deg, rgba(233, 248, 241, 0.92), rgba(255, 255, 255, 0.98));
}

.summary-card[data-tone="danger"] {
  background: linear-gradient(180deg, rgba(251, 240, 238, 0.92), rgba(255, 255, 255, 0.98));
}

.summary-card[data-tone="brand"] {
  background: linear-gradient(180deg, rgba(239, 244, 242, 0.95), rgba(255, 255, 255, 0.98));
}

.summary-card[data-tone="ink"] {
  background: linear-gradient(180deg, rgba(243, 247, 251, 0.96), rgba(255, 255, 255, 0.98));
}

.summary-card[data-tone="soft"] {
  background: linear-gradient(180deg, rgba(245, 247, 241, 0.96), rgba(255, 255, 255, 0.98));
}

.analytics-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 18px;
}

.analytics-panel {
  padding: 22px;
  grid-column: span 4;
}

.analytics-panel-wide {
  grid-column: span 8;
}

.analytics-panel-full {
  grid-column: span 12;
}

.analytics-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.analytics-empty,
.sync-health-card {
  padding: 18px;
  border-radius: 18px;
  border: 1px dashed rgba(19, 38, 27, 0.12);
  background: var(--surface-muted);
}

.analytics-empty-danger {
  color: #a02e22;
}

.sync-health-card strong {
  color: var(--ink);
}

.chart-shell {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(22px, 1fr));
  gap: 10px;
  align-items: end;
  min-height: 260px;
}

.provider-chart-shell {
  min-height: 300px;
}

.chart-column {
  display: grid;
  gap: 10px;
  align-items: end;
  justify-items: center;
}

.chart-bars {
  width: 100%;
  min-height: 210px;
  display: flex;
  align-items: end;
  justify-content: center;
  gap: 4px;
}

.provider-bars {
  min-height: 250px;
}

.chart-bar {
  width: min(14px, 100%);
  border-radius: 999px 999px 6px 6px;
}

.chart-bar.published {
  background: linear-gradient(180deg, #7fa293, #6f8c80);
}

.chart-bar.failed {
  background: linear-gradient(180deg, #d37d70, #b85c4c);
}

.provider-impressions {
  background: linear-gradient(180deg, #60776d, #415b50);
}

.provider-reach {
  background: linear-gradient(180deg, #88a59a, #698579);
}

.provider-engagement {
  background: linear-gradient(180deg, #d6a16c, #b47f47);
}

.chart-column small {
  font-size: 11px;
  color: var(--muted);
  writing-mode: vertical-rl;
  transform: rotate(180deg);
}

.failure-list,
.channel-table {
  display: grid;
  gap: 10px;
}

.failure-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  background: var(--surface-muted);
}

.failure-row strong,
.channel-meta strong {
  color: var(--ink);
}

.failure-row p {
  margin: 4px 0 0;
  line-height: 1.5;
}

.failure-row span {
  min-width: 120px;
  text-align: right;
  font-size: 12px;
  color: var(--muted);
}

.channel-table-head,
.channel-table-row {
  display: grid;
  grid-template-columns: minmax(240px, 2.2fr) repeat(4, minmax(0, 1fr));
  gap: 12px;
  align-items: center;
}

.channel-table-head {
  padding: 0 2px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.channel-table-row {
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid var(--line-soft);
  background: var(--surface-muted);
  color: var(--ink);
}

.channel-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.channel-badge {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(180deg, #6f8c80, #7fa293);
  color: #fff8ec;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 900;
  flex-shrink: 0;
}

@media (max-width: 1100px) {
  .analytics-summary {
    grid-template-columns: 1fr 1fr;
  }

  .analytics-grid {
    grid-template-columns: 1fr;
  }

  .analytics-panel,
  .analytics-panel-wide,
  .analytics-panel-full {
    grid-column: auto;
  }
}

@media (max-width: 760px) {
  .analytics-page {
    padding: 20px;
  }

  .analytics-header,
  .analytics-panel-head,
  .failure-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .analytics-summary {
    grid-template-columns: 1fr;
  }

  .analytics-controls {
    width: 100%;
    justify-items: stretch;
  }

  .channel-select,
  .range-control {
    min-width: 0;
    width: 100%;
  }

  .chart-shell {
    overflow-x: auto;
    padding-bottom: 6px;
  }

  .chart-column {
    min-width: 28px;
  }

  .channel-table-head {
    display: none;
  }

  .channel-table-row {
    grid-template-columns: 1fr;
  }

  .failure-row span {
    min-width: 0;
    text-align: left;
  }
}
</style>
