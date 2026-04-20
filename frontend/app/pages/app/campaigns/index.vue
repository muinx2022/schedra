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

type PendingImagePreview = {
  key: string
  name: string
  url: string
}

type Campaign = {
  id: string
  title: string
  source_file_name: string
  source_media_type: "none" | "video" | "images"
  source_video_detail: MediaAsset | null
  source_images_detail: Array<{
    id: string
    order_index: number
    media_asset: MediaAsset
  }>
  status: string
  segment_count: number
  draft_count: number
  created_at: string
  updated_at: string
}

const acceptedSourceFiles = ".txt,.pdf,.doc,.docx"

const createOpen = ref(false)
const editCampaignId = ref<string | null>(null)
const deleteCampaignId = ref<string | null>(null)

const createTitle = ref("")
const createSourceFile = ref<File | null>(null)
const createMediaType = ref<"none" | "video" | "images">("none")
const selectedVideoId = ref("")
const selectedImageIds = ref<string[]>([])
const selectedImageAssets = ref<MediaAsset[]>([])
const pendingImagePreviews = ref<PendingImagePreview[]>([])

const editTitle = ref("")

const sourceInputRef = ref<HTMLInputElement | null>(null)
const videoInputRef = ref<HTMLInputElement | null>(null)
const imageInputRef = ref<HTMLInputElement | null>(null)

const uploadingCampaign = ref(false)
const uploadingVideo = ref(false)
const uploadingImages = ref(false)
const savingEdit = ref(false)
const deletingCampaign = ref(false)
const progress = ref(0)
const feedback = ref("")
const error = ref("")

const { data: campaigns, refresh: refreshCampaigns } = useAsyncData(
  "campaigns-list",
  () => apiFetch<Campaign[]>("/campaigns/"),
  { lazy: true, default: () => [] }
)

const { data: mediaAssets, refresh: refreshMediaAssets } = useAsyncData(
  "campaign-media-assets-list",
  () => apiFetch<MediaAsset[]>("/media/"),
  { lazy: true, default: () => [] }
)

const videoAssets = computed(() =>
  mediaAssets.value.filter((asset) => asset.kind === "video" || String(asset.content_type || "").startsWith("video/"))
)
const imageAssets = computed(() =>
  mediaAssets.value.filter((asset) => asset.kind === "image" || String(asset.content_type || "").startsWith("image/"))
)
const selectedVideo = computed(() =>
  selectedVideoId.value ? videoAssets.value.find((asset) => asset.id === selectedVideoId.value) || null : null
)
const selectedImages = computed(() =>
  selectedImageIds.value
    .map((id) => selectedImageAssets.value.find((asset) => asset.id === id) || imageAssets.value.find((asset) => asset.id === id))
    .filter((asset): asset is MediaAsset => !!asset)
)
const editCampaign = computed(() =>
  editCampaignId.value ? campaigns.value.find((campaign) => campaign.id === editCampaignId.value) || null : null
)
const deleteCampaign = computed(() =>
  deleteCampaignId.value ? campaigns.value.find((campaign) => campaign.id === deleteCampaignId.value) || null : null
)

const canCreateCampaign = computed(() => {
  if (!createTitle.value.trim() || !createSourceFile.value || uploadingCampaign.value) return false
  if (createMediaType.value === "video") return !!selectedVideoId.value
  if (createMediaType.value === "images") return selectedImageIds.value.length > 0
  return true
})

watch(
  videoAssets,
  (value) => {
    if (createMediaType.value === "video" && !selectedVideoId.value && value.length) {
      selectedVideoId.value = value[0].id
    }
  },
  { immediate: true }
)

watch(createMediaType, (value) => {
  if (value !== "video") selectedVideoId.value = ""
  if (value !== "images") {
    selectedImageIds.value = []
    selectedImageAssets.value = []
    clearPendingImagePreviews()
  }
})

function clearPendingImagePreviews() {
  for (const preview of pendingImagePreviews.value) URL.revokeObjectURL(preview.url)
  pendingImagePreviews.value = []
}

function resetCreateForm() {
  createTitle.value = ""
  createSourceFile.value = null
  createMediaType.value = "none"
  selectedVideoId.value = ""
  selectedImageIds.value = []
  selectedImageAssets.value = []
  clearPendingImagePreviews()
  progress.value = 0
  if (sourceInputRef.value) sourceInputRef.value.value = ""
}

function openCreateModal() {
  resetCreateForm()
  createOpen.value = true
  error.value = ""
}

function closeCreateModal() {
  createOpen.value = false
  resetCreateForm()
}

function onSourceFileChange(event: Event) {
  createSourceFile.value = (event.target as HTMLInputElement).files?.[0] || null
  error.value = ""
}

function upsertMediaAsset(asset: MediaAsset) {
  mediaAssets.value = [asset, ...mediaAssets.value.filter((item) => item.id !== asset.id)]
}

async function uploadNewVideo(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  ;(event.target as HTMLInputElement).value = ""
  if (!file) return

  createMediaType.value = "video"
  uploadingVideo.value = true
  error.value = ""
  feedback.value = ""
  try {
    const asset = await uploadMediaAsset(file, {})
    upsertMediaAsset(asset)
    await refreshMediaAssets()
    selectedVideoId.value = asset.id
    feedback.value = `Uploaded source video: ${asset.title || asset.file_name}`
  } catch (err: any) {
    error.value = extractApiError(err, "Could not upload the source video.")
  } finally {
    uploadingVideo.value = false
  }
}

async function uploadNewImage(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ""
  if (!files.length) return

  createMediaType.value = "images"
  uploadingImages.value = true
  error.value = ""
  feedback.value = ""
  const pendingPreviews = files.map((file) => ({
    key: `${file.name}-${file.size}-${file.lastModified}`,
    name: file.name,
    url: URL.createObjectURL(file),
  }))
  pendingImagePreviews.value = [...pendingImagePreviews.value, ...pendingPreviews]
  try {
    const uploadedIds: string[] = []
    for (const [index, file] of files.entries()) {
      const pendingKey = pendingPreviews[index]?.key
      const asset = await uploadMediaAsset(file, {})
      upsertMediaAsset(asset)
      uploadedIds.push(asset.id)
      selectedImageAssets.value = [asset, ...selectedImageAssets.value.filter((item) => item.id !== asset.id)]
      selectedImageIds.value = [...new Set([...selectedImageIds.value, asset.id])]
      if (pendingKey) {
        const pending = pendingImagePreviews.value.find((preview) => preview.key === pendingKey)
        if (pending) URL.revokeObjectURL(pending.url)
        pendingImagePreviews.value = pendingImagePreviews.value.filter((preview) => preview.key !== pendingKey)
      }
    }
    await refreshMediaAssets()
    feedback.value = uploadedIds.length === 1
      ? "Uploaded 1 source image."
      : `Uploaded ${uploadedIds.length} source images.`
  } catch (err: any) {
    clearPendingImagePreviews()
    error.value = extractApiError(err, "Could not upload the source image.")
  } finally {
    uploadingImages.value = false
  }
}

function removeSelectedImage(imageId: string) {
  selectedImageIds.value = selectedImageIds.value.filter((id) => id !== imageId)
  selectedImageAssets.value = selectedImageAssets.value.filter((asset) => asset.id !== imageId)
}

async function createCampaign() {
  if (!createSourceFile.value || !canCreateCampaign.value) return

  uploadingCampaign.value = true
  progress.value = 0
  error.value = ""
  feedback.value = ""
  try {
    const campaign = await uploadCampaignSource(createSourceFile.value, {
      mediaType: createMediaType.value,
      sourceVideoId: createMediaType.value === "video" ? selectedVideoId.value : undefined,
      sourceImageIds: createMediaType.value === "images" ? selectedImageIds.value : undefined,
      title: createTitle.value,
      onProgress(percent) {
        progress.value = percent
      },
    })
    await refreshCampaigns()
    closeCreateModal()
    feedback.value = `Campaign "${campaign.title}" created.`
  } catch (err: any) {
    error.value = extractApiError(err, "Could not create campaign.")
  } finally {
    uploadingCampaign.value = false
    progress.value = 0
  }
}

function startEditCampaign(campaign: Campaign) {
  editCampaignId.value = campaign.id
  editTitle.value = campaign.title
  error.value = ""
}

function closeEditModal() {
  editCampaignId.value = null
  editTitle.value = ""
}

async function saveCampaignTitle() {
  if (!editCampaign.value || !editTitle.value.trim() || savingEdit.value) return

  savingEdit.value = true
  error.value = ""
  feedback.value = ""
  try {
    await apiFetch(`/campaigns/${editCampaign.value.id}/`, {
      method: "PATCH",
      body: { title: editTitle.value.trim() },
    })
    await refreshCampaigns()
    feedback.value = "Campaign title updated."
    closeEditModal()
  } catch (err: any) {
    error.value = extractApiError(err, "Could not update the campaign title.")
  } finally {
    savingEdit.value = false
  }
}

function startDeleteCampaign(campaign: Campaign) {
  deleteCampaignId.value = campaign.id
  error.value = ""
}

function closeDeleteModal() {
  deleteCampaignId.value = null
}

async function confirmDeleteCampaign() {
  if (!deleteCampaign.value || deletingCampaign.value) return

  deletingCampaign.value = true
  error.value = ""
  feedback.value = ""
  try {
    await apiFetch(`/campaigns/${deleteCampaign.value.id}/`, { method: "DELETE" })
    await refreshCampaigns()
    feedback.value = `Deleted campaign "${deleteCampaign.value.title}".`
    closeDeleteModal()
  } catch (err: any) {
    error.value = extractApiError(err, "Could not delete the campaign.")
  } finally {
    deletingCampaign.value = false
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function mediaLabel(campaign: Campaign) {
  if (campaign.source_media_type === "video") return "Video"
  if (campaign.source_media_type === "images") return `${campaign.source_images_detail.length} images`
  return "Text only"
}

function viewCampaign(campaign: Campaign) {
  return navigateTo(`/app/campaigns/${campaign.id}`)
}
</script>

<template>
  <div class="campaigns-page">
    <div class="campaigns-hero">
      <div>
        <p class="campaigns-kicker">Campaign manager</p>
        <h1>Campaigns</h1>
        <p class="campaigns-subtitle">
          Manage campaigns from one list. Create new campaigns here, then open each campaign to generate segments and create draft posts.
        </p>
      </div>
    </div>

    <p v-if="error" class="campaigns-alert error">{{ error }}</p>
    <p v-if="feedback" class="campaigns-alert success">{{ feedback }}</p>

    <section class="campaign-list-card">
      <div class="campaign-list-head">
        <div>
          <p class="section-label">All campaigns</p>
          <h2>{{ campaigns.length }} campaign{{ campaigns.length === 1 ? "" : "s" }}</h2>
        </div>
        <button type="button" class="campaign-btn campaign-btn-primary" @click="openCreateModal">Create campaign</button>
      </div>

      <div v-if="campaigns.length" class="campaign-table">
        <article v-for="campaign in campaigns" :key="campaign.id" class="campaign-row">
          <div class="campaign-main">
            <button type="button" class="campaign-title" @click="viewCampaign(campaign)">{{ campaign.title }}</button>
            <p>{{ campaign.source_file_name }}</p>
          </div>
          <div class="campaign-meta">
            <span class="meta-chip">{{ mediaLabel(campaign) }}</span>
            <span class="meta-chip">{{ campaign.segment_count }} segments</span>
            <span class="meta-chip">{{ campaign.draft_count }} drafts</span>
            <span class="status-pill" :data-status="campaign.status">{{ campaign.status }}</span>
          </div>
          <div class="campaign-time">
            <span>Updated</span>
            <strong>{{ formatDate(campaign.updated_at) }}</strong>
          </div>
          <div class="campaign-actions">
            <button type="button" class="campaign-btn campaign-btn-secondary" @click="viewCampaign(campaign)">View</button>
            <button type="button" class="campaign-btn campaign-btn-secondary" @click="startEditCampaign(campaign)">Edit</button>
            <button type="button" class="campaign-btn campaign-btn-danger" @click="startDeleteCampaign(campaign)">Delete</button>
          </div>
        </article>
      </div>
      <div v-else class="empty-state">
        No campaigns yet. Create one first, then open it to generate segments and draft posts.
      </div>
    </section>

    <Teleport to="body">
      <div v-if="createOpen" class="modal-shell" @click.self="closeCreateModal">
        <section class="modal-card modal-card-wide">
          <div class="modal-head">
            <div>
              <p class="section-label">New campaign</p>
              <h2>Create campaign</h2>
            </div>
            <button type="button" class="campaign-icon-btn" @click="closeCreateModal">×</button>
          </div>

          <div class="form-grid">
            <div class="field-group field-span-2">
              <label class="field-label">Campaign title</label>
              <input v-model="createTitle" class="text-input" type="text" placeholder="Required title" />
            </div>

            <div class="field-group field-span-2">
              <label class="field-label">Source document</label>
              <input
                ref="sourceInputRef"
                class="file-input"
                type="file"
                :accept="acceptedSourceFiles"
                @change="onSourceFileChange"
              />
              <p class="field-help">Accepted formats: TXT, PDF, DOC, DOCX. Document should contain <code>##SEGMENT</code> blocks.</p>
              <p v-if="createSourceFile" class="field-value">{{ createSourceFile.name }}</p>
            </div>

            <div class="field-group field-span-2">
              <label class="field-label">Media strategy</label>
              <div class="strategy-row">
                <button
                  type="button"
                  class="strategy-pill"
                  :class="{ active: createMediaType === 'none' }"
                  @click="createMediaType = 'none'"
                >
                  Text only
                </button>
                <button
                  type="button"
                  class="strategy-pill"
                  :class="{ active: createMediaType === 'video' }"
                  @click="createMediaType = 'video'"
                >
                  Video
                </button>
                <button
                  type="button"
                  class="strategy-pill"
                  :class="{ active: createMediaType === 'images' }"
                  @click="createMediaType = 'images'"
                >
                  Image list
                </button>
              </div>
            </div>

            <div v-if="createMediaType === 'video'" class="field-group field-span-2 video-picker">
              <div>
                <label class="field-label">Source video</label>
                <select v-model="selectedVideoId" class="text-input">
                  <option value="">Select a video</option>
                  <option v-for="asset in videoAssets" :key="asset.id" :value="asset.id">
                    {{ asset.title || asset.file_name }}
                  </option>
                </select>
              </div>
              <label class="campaign-btn campaign-btn-secondary upload-file-btn" :class="{ disabled: uploadingVideo }">
                {{ uploadingVideo ? "Uploading..." : "Upload new video" }}
                <input ref="videoInputRef" type="file" accept="video/*" :disabled="uploadingVideo" class="file-button-input" @change="uploadNewVideo" />
              </label>
              <div v-if="selectedVideo" class="video-preview">
                <video :src="selectedVideo.file_url" controls preload="metadata"></video>
                <p>{{ selectedVideo.title || selectedVideo.file_name }}</p>
              </div>
            </div>

            <div v-if="createMediaType === 'images'" class="field-group field-span-2 image-picker">
              <div class="image-picker-head">
                <label class="field-label">Source images</label>
                <button type="button" class="campaign-btn campaign-btn-secondary" :disabled="uploadingImages" @click="imageInputRef?.click()">
                  {{ uploadingImages ? "Uploading..." : "Upload new image" }}
                </button>
              </div>
              <input
                ref="imageInputRef"
                type="file"
                accept="image/*"
                multiple
                :disabled="uploadingImages"
                class="hidden-input"
                @change="uploadNewImage"
              />
              <p v-if="uploadingImages" class="field-help">Uploading selected images...</p>
              <p class="field-help">
                Image mode needs at least one image. Images map by order: segment 1 uses image 1, segment 2 uses image 2, later segments without images become text-only drafts.
              </p>
              <div v-if="pendingImagePreviews.length || selectedImages.length" class="image-grid">
                <div v-for="preview in pendingImagePreviews" :key="preview.key" class="image-tile uploading">
                  <img :src="preview.url" :alt="preview.name" />
                  <span>{{ preview.name }}</span>
                  <small>Uploading...</small>
                </div>
                <div v-for="asset in selectedImages" :key="asset.id" class="image-tile">
                  <img :src="asset.file_url" :alt="asset.title || asset.file_name" />
                  <span>{{ asset.title || asset.file_name }}</span>
                  <button type="button" class="campaign-btn campaign-btn-danger remove-image-btn" @click="removeSelectedImage(asset.id)">Remove</button>
                </div>
              </div>
              <div v-else class="empty-state compact">No campaign images selected yet.</div>
            </div>

            <div v-if="createMediaType === 'none'" class="field-group field-span-2 empty-state compact">
              This campaign will be created as text only. Generate and create drafts later on the campaign detail page.
            </div>
          </div>

          <div v-if="uploadingCampaign" class="progress-block">
            <div class="progress-bar">
              <span :style="{ width: `${progress}%` }"></span>
            </div>
            <small>Uploading source file... {{ progress }}%</small>
          </div>

          <div class="modal-actions">
            <button type="button" class="campaign-btn campaign-btn-secondary" @click="closeCreateModal">Cancel</button>
            <button type="button" class="campaign-btn campaign-btn-primary" :disabled="!canCreateCampaign" @click="createCampaign">
              {{ uploadingCampaign ? "Creating..." : "Create campaign" }}
            </button>
          </div>
        </section>
      </div>

      <div v-if="editCampaign" class="modal-shell" @click.self="closeEditModal">
        <section class="modal-card">
          <div class="modal-head">
            <div>
              <p class="section-label">Edit campaign</p>
              <h2>Update title</h2>
            </div>
            <button type="button" class="campaign-icon-btn" @click="closeEditModal">×</button>
          </div>

          <label class="field-label">Campaign title</label>
          <input v-model="editTitle" class="text-input" type="text" />
          <p class="field-help">Only the title can be edited here.</p>

          <div class="modal-actions">
            <button type="button" class="campaign-btn campaign-btn-secondary" @click="closeEditModal">Cancel</button>
            <button type="button" class="campaign-btn campaign-btn-primary" :disabled="!editTitle.trim() || savingEdit" @click="saveCampaignTitle">
              {{ savingEdit ? "Saving..." : "Save title" }}
            </button>
          </div>
        </section>
      </div>

      <div v-if="deleteCampaign" class="modal-shell" @click.self="closeDeleteModal">
        <section class="modal-card">
          <div class="modal-head">
            <div>
              <p class="section-label">Delete campaign</p>
              <h2>{{ deleteCampaign.title }}</h2>
            </div>
            <button type="button" class="campaign-icon-btn" @click="closeDeleteModal">×</button>
          </div>

          <p class="modal-copy">
            This will remove the campaign and its generated segments. Existing draft posts created from it are not described here as recoverable, so treat this as destructive.
          </p>

          <div class="modal-actions">
            <button type="button" class="campaign-btn campaign-btn-secondary" @click="closeDeleteModal">Cancel</button>
            <button type="button" class="campaign-btn campaign-btn-danger" :disabled="deletingCampaign" @click="confirmDeleteCampaign">
              {{ deletingCampaign ? "Deleting..." : "Delete campaign" }}
            </button>
          </div>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.campaigns-page {
  padding: 32px;
  display: grid;
  gap: 20px;
  align-content: start;
}

.campaigns-hero,
.campaign-list-head,
.modal-head,
.modal-actions,
.image-picker-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.campaigns-kicker,
.section-label {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}

.campaigns-hero h1,
.campaign-list-card h2,
.modal-card h2 {
  margin: 0;
  color: var(--ink);
}

.campaigns-subtitle,
.campaigns-alert,
.field-help,
.field-value,
.campaign-row p,
.modal-copy,
.empty-state {
  color: var(--muted);
}

.campaigns-subtitle {
  margin: 12px 0 0;
  max-width: 760px;
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

.campaign-list-card,
.modal-card {
  display: grid;
  gap: 16px;
  align-content: start;
  padding: 24px;
  border-radius: 28px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-panel);
}

.campaign-table {
  display: grid;
  gap: 12px;
}

.campaign-row {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 1.2fr) 140px auto;
  gap: 14px;
  align-items: center;
  padding: 18px;
  border-radius: 20px;
  border: 1px solid var(--line-soft);
  background: var(--surface);
}

.campaign-title {
  border: 0;
  padding: 0;
  background: transparent;
  font-size: 16px;
  font-weight: 800;
  color: var(--ink);
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.campaign-title:hover {
  text-decoration: underline;
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
  padding: 9px 12px;
}

.campaign-icon-btn {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
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

.campaign-btn-danger {
  border-color: rgba(138, 39, 28, 0.28);
  background: linear-gradient(180deg, #fff4f1 0%, #f7ded8 100%);
  color: #a02e22;
}

.campaign-btn-danger:hover:not(:disabled) {
  border-color: rgba(138, 39, 28, 0.4);
  background: linear-gradient(180deg, #ffe9e3 0%, #f1cfc6 100%);
}

.campaign-main p,
.campaign-time span {
  margin: 6px 0 0;
  font-size: 13px;
}

.campaign-meta,
.campaign-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.campaign-time {
  display: grid;
  gap: 4px;
}

.campaign-time strong {
  font-size: 13px;
}

.meta-chip,
.status-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.meta-chip {
  background: var(--surface-muted);
  color: var(--muted);
}

.status-pill {
  border: 1px solid var(--line-soft);
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

.modal-shell {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(16, 30, 25, 0.48);
  backdrop-filter: blur(8px);
}

.modal-card {
  width: min(620px, 100%);
  max-height: calc(100vh - 48px);
  overflow: auto;
}

.modal-card-wide {
  width: min(920px, 100%);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.field-group {
  display: grid;
  gap: 8px;
}

.field-span-2 {
  grid-column: 1 / -1;
}

.field-label {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.text-input,
.file-input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 12px 14px;
  background: var(--input-bg);
  color: var(--ink);
}

.field-help,
.field-value,
.modal-copy {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
}

.strategy-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.strategy-pill {
  border: 1px solid var(--line);
  background: var(--control-bg);
  color: var(--ink);
  border-radius: 999px;
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: var(--shadow-soft);
}

.strategy-pill.active {
  background: linear-gradient(180deg, var(--action-fill-start) 0%, var(--action-fill-end) 100%);
  border-color: var(--action-border);
  color: var(--action-ink);
}

.video-picker,
.image-picker {
  display: grid;
  gap: 12px;
}

.video-preview {
  display: grid;
  gap: 10px;
  padding: 14px;
  border-radius: 18px;
  background: var(--surface-muted);
}

.video-preview video {
  width: 100%;
  border-radius: 14px;
  background: #111;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
}

.image-tile {
  display: grid;
  gap: 6px;
  padding: 8px;
  border: 1px solid var(--line-soft);
  border-radius: 14px;
  background: var(--surface);
}

.image-tile img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 10px;
}

.image-tile span {
  font-size: 12px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-tile small {
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

.image-tile.uploading {
  border-color: rgba(95, 127, 114, 0.22);
  background: rgba(127, 162, 147, 0.1);
}

.remove-image-btn {
  padding: 6px 8px;
  font-size: 11px;
  font-weight: 700;
}

.progress-block {
  display: grid;
  gap: 8px;
}

.progress-bar {
  height: 10px;
  border-radius: 999px;
  background: rgba(19, 38, 27, 0.08);
  overflow: hidden;
}

.progress-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #5f7f72, #7fa293);
}

.hidden-input {
  display: none;
}

.upload-file-btn {
  position: relative;
  overflow: hidden;
  width: fit-content;
}

.upload-file-btn.disabled {
  background: var(--disabled-bg);
  border-color: var(--disabled-border);
  color: var(--disabled-ink);
  cursor: not-allowed;
  box-shadow: none;
  pointer-events: none;
}

.file-button-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.file-button-input:disabled {
  cursor: not-allowed;
}

.empty-state {
  padding: 18px;
  border-radius: 18px;
  background: var(--surface-muted);
  border: 1px dashed var(--line);
}

.empty-state.compact {
  padding: 14px 16px;
}

@media (max-width: 1200px) {
  .campaign-row {
    grid-template-columns: 1fr 1fr;
  }

  .campaign-main {
    grid-column: 1 / -1;
  }

  .campaign-actions {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .campaign-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .campaigns-page {
    padding: 20px;
  }

  .campaigns-hero,
  .campaign-list-head,
  .modal-head,
  .modal-actions,
  .image-picker-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .field-span-2 {
    grid-column: auto;
  }
}
</style>
