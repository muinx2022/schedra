<script setup lang="ts">
definePageMeta({ middleware: "auth" })

type MediaAsset = {
  id: string
  title?: string
  file_url: string
  file_name: string
  kind?: string
  content_type?: string
  created_at: string
}

type CampaignSegment = {
  id: string
  order_index: number
  raw_text: string
  caption_text: string
  start_seconds: number
  end_seconds: number
  duration_seconds: number
  status: string
  draft_post: string | null
}

type Campaign = {
  id: string
  title: string
  source_file_url: string
  source_file_name: string
  source_file_type: string
  source_text: string
  source_media_type: "none" | "video" | "images"
  source_video_detail: MediaAsset | null
  source_images_detail: Array<{
    id: string
    order_index: number
    media_asset: MediaAsset
  }>
  status: string
  segment_count: number
  total_video_duration_seconds: number
  segments: CampaignSegment[]
  draft_count: number
  created_at: string
  updated_at: string
}

type SegmentMediaPreview = {
  type: "image" | "video"
  url: string
  title: string
  label: string
  rangeLabel?: string
}

const route = useRoute()
const campaignId = computed(() => String(route.params.id || ""))

const generating = ref(false)
const creatingDrafts = ref(false)
const lightboxMedia = ref<SegmentMediaPreview | null>(null)
const feedback = ref("")
const error = ref("")

const { data: campaign, refresh: refreshCampaign } = useAsyncData(
  () => `campaign-${campaignId.value}`,
  () => apiFetch<Campaign>(`/campaigns/${campaignId.value}/`),
  { watch: [campaignId] }
)

const canGenerate = computed(() => !!campaign.value && !generating.value)
const canCreateDrafts = computed(() =>
  !!campaign.value &&
  campaign.value.segments.length > 0 &&
  !creatingDrafts.value
)

async function generateSegments() {
  if (!campaign.value || generating.value) return

  generating.value = true
  feedback.value = ""
  error.value = ""
  try {
    await apiFetch(`/campaigns/${campaign.value.id}/generate/`, { method: "POST", body: {} })
    await refreshCampaign()
    feedback.value = campaign.value.source_media_type === "video"
      ? "Segments generated and video ranges are ready."
      : "Segments generated and ready for draft creation."
  } catch (err: any) {
    error.value = extractApiError(err, "Could not generate campaign segments.")
  } finally {
    generating.value = false
  }
}

async function createDrafts() {
  if (!campaign.value || creatingDrafts.value) return

  creatingDrafts.value = true
  feedback.value = ""
  error.value = ""
  try {
    const response = await apiFetch<{ created_count: number; draft_count: number }>(
      `/campaigns/${campaign.value.id}/create-drafts/`,
      { method: "POST", body: {} }
    )
    await refreshCampaign()
    feedback.value = response.created_count
      ? `Created ${response.created_count} draft posts.`
      : `All ${response.draft_count} draft posts already exist for this campaign.`
  } catch (err: any) {
    error.value = extractApiError(err, "Could not create draft posts.")
  } finally {
    creatingDrafts.value = false
  }
}

function formatSeconds(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, "0")}`
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function summarizeText(value: string, maxLength = 220) {
  const normalized = value.replace(/\s+/g, " ").trim()
  if (normalized.length <= maxLength) return normalized
  return `${normalized.slice(0, maxLength)}...`
}

function imageLabelForSegment(segment: CampaignSegment) {
  if (!campaign.value || segment.order_index >= campaign.value.source_images_detail.length) return "No image"
  return `Image ${segment.order_index + 1}`
}

function videoRangeUrl(asset: MediaAsset, segment: CampaignSegment) {
  if (segment.end_seconds <= segment.start_seconds) return asset.file_url
  return `${asset.file_url}#t=${segment.start_seconds},${segment.end_seconds}`
}

function segmentMediaFor(segment: CampaignSegment): SegmentMediaPreview | null {
  if (!campaign.value) return null
  if (campaign.value.source_media_type === "video" && campaign.value.source_video_detail) {
    const asset = campaign.value.source_video_detail
    const rangeLabel = `${formatSeconds(segment.start_seconds)} - ${formatSeconds(segment.end_seconds)}`
    return {
      type: "video",
      url: videoRangeUrl(asset, segment),
      title: asset.title || asset.file_name,
      label: `Video clip ${segment.order_index + 1}`,
      rangeLabel,
    }
  }
  if (campaign.value.source_media_type === "images") {
    const item = campaign.value.source_images_detail[segment.order_index]
    if (!item) return null
    return {
      type: "image",
      url: item.media_asset.file_url,
      title: item.media_asset.title || item.media_asset.file_name,
      label: `Image ${segment.order_index + 1}`,
    }
  }
  return null
}

function openMediaLightbox(media: SegmentMediaPreview | null) {
  if (!media) return
  lightboxMedia.value = media
}

function closeMediaLightbox() {
  lightboxMedia.value = null
}
</script>

<template>
  <div class="campaign-detail-page">
    <div class="detail-hero">
      <div>
        <NuxtLink to="/app/campaigns" class="back-link">← Back to campaigns</NuxtLink>
        <p class="detail-kicker">Campaign detail</p>
        <h1>{{ campaign?.title || "Campaign" }}</h1>
        <p v-if="campaign" class="detail-subtitle">
          {{ campaign.source_file_name }} · Updated {{ formatDate(campaign.updated_at) }}
        </p>
      </div>
    </div>

    <p v-if="error" class="campaigns-alert error">{{ error }}</p>
    <p v-if="feedback" class="campaigns-alert success">{{ feedback }}</p>

    <template v-if="campaign">
      <div class="stats-row">
        <div class="stat-box">
          <span>Status</span>
          <strong>{{ campaign.status }}</strong>
        </div>
        <div class="stat-box">
          <span>Segments</span>
          <strong>{{ campaign.segment_count }}</strong>
        </div>
        <div class="stat-box">
          <span>Media</span>
          <strong>
            {{
              campaign.source_media_type === "video"
                ? formatSeconds(campaign.total_video_duration_seconds || 0)
                : campaign.source_media_type === "images"
                  ? `${campaign.source_images_detail.length} images`
                  : "Text only"
            }}
          </strong>
        </div>
        <div class="stat-box">
          <span>Drafts</span>
          <strong>{{ campaign.draft_count }}</strong>
        </div>
      </div>

      <div class="content-grid">
        <section class="detail-card">
          <div class="card-head">
            <div>
              <p class="section-label">Source</p>
              <h2>Campaign source</h2>
            </div>
          </div>

          <div class="summary-box">
            <span class="field-label">Source file</span>
            <p>{{ campaign.source_file_name }} · {{ campaign.source_file_type.toUpperCase() }}</p>
          </div>

          <div v-if="campaign.source_media_type === 'video' && campaign.source_video_detail" class="summary-box">
            <span class="field-label">Source video</span>
            <video :src="campaign.source_video_detail.file_url" controls preload="metadata"></video>
            <p>{{ campaign.source_video_detail.title || campaign.source_video_detail.file_name }}</p>
          </div>

          <div v-if="campaign.source_media_type === 'images' && campaign.source_images_detail.length" class="summary-box">
            <span class="field-label">Selected images</span>
            <div class="selected-images-row">
              <img
                v-for="item in campaign.source_images_detail"
                :key="item.id"
                :src="item.media_asset.file_url"
                :alt="item.media_asset.title || item.media_asset.file_name"
              />
            </div>
          </div>

          <div class="summary-box">
            <span class="field-label">Extracted text preview</span>
            <p>{{ campaign.source_text ? summarizeText(campaign.source_text, 420) : "Generate to extract text." }}</p>
          </div>

          <div class="source-actions">
            <button type="button" class="campaign-btn campaign-btn-primary" :disabled="!canGenerate" @click="generateSegments">
              {{ generating ? "Generating..." : "Generate segments" }}
            </button>
          </div>
        </section>

        <section class="detail-card">
          <div class="card-head">
            <div>
              <p class="section-label">Draft output</p>
              <h2>Segments</h2>
            </div>
            <div class="draft-actions">
              <button type="button" class="campaign-btn campaign-btn-primary" :disabled="!canCreateDrafts" @click="createDrafts">
                {{ creatingDrafts ? "Creating..." : "Create drafts" }}
              </button>
              <NuxtLink to="/app/posts?tab=drafts" class="campaign-btn campaign-btn-secondary">Open drafts</NuxtLink>
            </div>
          </div>

          <div v-if="campaign.segments.length" class="segments-table">
            <article v-for="segment in campaign.segments" :key="segment.id" class="segment-row">
              <div class="segment-copy">
                <div class="segment-meta">
                  <strong>Segment {{ segment.order_index + 1 }}</strong>
                  <template v-if="campaign.source_media_type === 'video'">
                    <span>{{ formatSeconds(segment.start_seconds) }} - {{ formatSeconds(segment.end_seconds) }}</span>
                    <span>{{ formatSeconds(segment.duration_seconds) }}</span>
                  </template>
                  <template v-else-if="campaign.source_media_type === 'images'">
                    <span>{{ imageLabelForSegment(segment) }}</span>
                  </template>
                  <template v-else>
                    <span>Text only</span>
                  </template>
                </div>
                <p>{{ summarizeText(segment.caption_text) }}</p>
                <small v-if="segment.draft_post">Draft linked: {{ segment.draft_post }}</small>
              </div>

              <div class="segment-media-cell">
                <button
                  v-if="segmentMediaFor(segment)"
                  type="button"
                  class="segment-media-preview"
                  @click="openMediaLightbox(segmentMediaFor(segment))"
                >
                  <video
                    v-if="segmentMediaFor(segment)?.type === 'video'"
                    :src="segmentMediaFor(segment)?.url"
                    muted
                    playsinline
                    preload="metadata"
                  ></video>
                  <img
                    v-else
                    :src="segmentMediaFor(segment)?.url"
                    :alt="segmentMediaFor(segment)?.title"
                  />
                  <span>{{ segmentMediaFor(segment)?.label }}</span>
                  <small v-if="segmentMediaFor(segment)?.rangeLabel">{{ segmentMediaFor(segment)?.rangeLabel }}</small>
                </button>
                <span v-else class="segment-no-media">No media</span>
              </div>
            </article>
          </div>
          <div v-else class="empty-state">
            No segments yet. Click Generate to parse the source file into campaign segments.
          </div>
        </section>
      </div>
    </template>

    <Teleport to="body">
      <div v-if="lightboxMedia" class="media-lightbox" @click.self="closeMediaLightbox">
        <section class="media-lightbox-card">
          <div class="media-lightbox-head">
            <div>
              <p class="section-label">{{ lightboxMedia.label }}</p>
              <h2>{{ lightboxMedia.title }}</h2>
              <span v-if="lightboxMedia.rangeLabel">{{ lightboxMedia.rangeLabel }}</span>
            </div>
            <button type="button" class="campaign-icon-btn" @click="closeMediaLightbox">x</button>
          </div>
          <video
            v-if="lightboxMedia.type === 'video'"
            :src="lightboxMedia.url"
            controls
            autoplay
            preload="metadata"
          ></video>
          <img v-else :src="lightboxMedia.url" :alt="lightboxMedia.title" />
        </section>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.campaign-detail-page {
  padding: 32px;
  display: grid;
  gap: 20px;
}

.detail-hero,
.hero-actions,
.card-head,
.draft-actions,
.segment-meta {
  display: flex;
  gap: 12px;
}

.detail-hero,
.card-head {
  align-items: flex-start;
  justify-content: space-between;
}

.hero-actions,
.draft-actions,
.segment-meta {
  align-items: center;
  flex-wrap: wrap;
}

.source-actions {
  display: flex;
  justify-content: flex-start;
}

.campaign-btn,
.campaign-icon-btn {
  border: 1px solid var(--line);
  background: var(--control-bg);
  color: var(--ink);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-soft);
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease, box-shadow 0.14s ease, transform 0.14s ease;
}

.campaign-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 9px 12px;
}

.campaign-icon-btn {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 900;
  line-height: 1;
}

.campaign-btn:hover:not(:disabled),
.campaign-icon-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: var(--brand-outline);
  background: var(--control-bg-hover);
  box-shadow: var(--shadow-panel);
}

.campaign-btn:disabled,
.campaign-icon-btn:disabled {
  opacity: 1;
  background: var(--disabled-bg);
  border-color: var(--disabled-border);
  color: var(--disabled-ink);
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.campaign-btn-primary {
  border-color: var(--action-border);
  background: linear-gradient(180deg, var(--action-fill-start) 0%, var(--action-fill-end) 100%);
  color: var(--action-ink);
}

.campaign-btn-primary:hover:not(:disabled) {
  border-color: var(--action-border);
  background: linear-gradient(180deg, var(--action-fill-hover-start) 0%, var(--action-fill-hover-end) 100%);
}

.campaign-btn-primary:active:not(:disabled) {
  background: linear-gradient(180deg, var(--action-fill-active-start) 0%, var(--action-fill-active-end) 100%);
}

.back-link {
  display: inline-block;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 700;
  color: var(--brand-strong);
}

.detail-kicker,
.section-label {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}

.detail-hero h1,
.detail-card h2 {
  margin: 0;
  color: var(--ink);
}

.detail-subtitle,
.summary-box p,
.segment-row p,
.empty-state {
  color: var(--muted);
}

.detail-subtitle,
.summary-box p,
.segment-row p {
  margin: 8px 0 0;
  line-height: 1.7;
}

.campaigns-alert {
  margin: 0;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid transparent;
}

.campaigns-alert.success {
  background: rgba(127, 162, 147, 0.12);
  border-color: rgba(127, 162, 147, 0.2);
  color: #355347;
}

.campaigns-alert.error {
  background: rgba(160, 46, 34, 0.08);
  border-color: rgba(160, 46, 34, 0.16);
  color: #8b2a20;
}

.stats-row,
.content-grid,
.segments-table {
  display: grid;
  gap: 12px;
}

.stats-row {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.content-grid {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr);
}

.detail-card {
  display: grid;
  gap: 16px;
  align-content: start;
  padding: 24px;
  border-radius: 28px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-panel);
}

.stat-box,
.summary-box,
.segment-row,
.empty-state {
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid var(--line-soft);
  background: var(--surface);
}

.stat-box span,
.field-label {
  display: block;
  margin-bottom: 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 6px 10px;
  border: 1px solid var(--line-soft);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status-pill[data-status="uploaded"] {
  background: #f3f6f9;
  color: #4f5a54;
}

.status-pill[data-status="generated"] {
  background: #eef4f1;
  color: #406052;
}

.status-pill[data-status="drafted"] {
  background: #f3f6f9;
  color: #5f6b64;
}

.status-pill[data-status="failed"] {
  background: #f3f6f9;
  color: #6f7a74;
}

.summary-box video {
  width: 100%;
  margin-top: 8px;
  border-radius: 14px;
  background: #111;
}

.selected-images-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
}

.selected-images-row img {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 12px;
}

.segment-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 150px;
  gap: 14px;
  align-items: start;
}

.segment-row small {
  color: var(--brand-strong);
  font-weight: 600;
}

.segment-copy {
  min-width: 0;
}

.segment-media-cell {
  min-height: 112px;
  display: flex;
  align-items: stretch;
  justify-content: flex-end;
}

.segment-media-preview {
  width: 150px;
  display: grid;
  gap: 6px;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--control-bg);
  color: var(--ink);
  cursor: pointer;
  text-align: left;
  box-shadow: var(--shadow-soft);
}

.segment-media-preview:hover {
  transform: translateY(-1px);
  border-color: rgba(95, 127, 114, 0.42);
  box-shadow: var(--shadow-panel);
}

.segment-media-preview img,
.segment-media-preview video {
  width: 100%;
  height: 86px;
  object-fit: cover;
  border-radius: 12px;
  background: #111;
}

.segment-media-preview span {
  font-size: 12px;
  font-weight: 800;
}

.segment-media-preview small,
.segment-no-media {
  color: var(--muted);
  font-size: 11px;
}

.segment-no-media {
  width: 150px;
  display: grid;
  place-items: center;
  border: 1px dashed var(--line);
  border-radius: 16px;
  background: var(--surface-muted);
}

.media-lightbox {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(12, 22, 18, 0.76);
  backdrop-filter: blur(10px);
}

.media-lightbox-card {
  width: min(980px, 100%);
  max-height: calc(100vh - 48px);
  display: grid;
  gap: 14px;
  padding: 18px;
  border-radius: 26px;
  background: var(--panel);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
  overflow: auto;
}

.media-lightbox-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.media-lightbox-head h2 {
  margin: 0;
  color: var(--ink);
}

.media-lightbox-head span {
  display: inline-block;
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

.media-lightbox-card > img,
.media-lightbox-card > video {
  width: 100%;
  max-height: 72vh;
  object-fit: contain;
  border-radius: 18px;
  background: #111;
}

@media (max-width: 1080px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .campaign-detail-page {
    padding: 20px;
  }

  .detail-hero,
  .hero-actions,
  .card-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .stats-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .segment-row {
    grid-template-columns: 1fr;
  }

  .segment-media-cell {
    justify-content: flex-start;
  }

  .segment-media-preview,
  .segment-no-media {
    width: 100%;
  }
}
</style>
