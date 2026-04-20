<script setup lang="ts">
definePageMeta({ middleware: "auth" })

const { data: assets, refresh } = useAsyncData(
  "media-assets",
  () => apiFetch<any[]>("/media/"),
  { lazy: true, default: () => [] }
)

const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref("")
const dragOver = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const deletingId = ref<string | null>(null)
const previewAsset = ref<any>(null)

type Toast = { id: number; message: string; kind: "success" | "error" }
const toasts = ref<Toast[]>([])
let _toastId = 0

function showToast(message: string, kind: Toast["kind"] = "success") {
  const id = ++_toastId
  toasts.value.push({ id, message, kind })
  setTimeout(() => {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }, 3500)
}

async function uploadFiles(files: FileList | File[]) {
  const list = Array.from(files).filter((f) => f.type.startsWith("image/") || f.type.startsWith("video/"))
  if (!list.length) return

  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = ""

  try {
    for (let index = 0; index < list.length; index++) {
      const file = list[index]
      uploadStatus.value = `Uploading ${index + 1}/${list.length}: ${file.name}`
      await uploadMediaAsset(file, {
        onProgress(percent) {
          const normalized = Math.min(percent, 99)
          uploadProgress.value = Math.round(((index + normalized / 100) / list.length) * 100)
          if (percent >= 100) {
            uploadStatus.value = `Processing ${index + 1}/${list.length}: ${file.name}`
          }
        },
      })
      uploadProgress.value = Math.round(((index + 1) / list.length) * 100)
    }
    await refresh()
    showToast(list.length === 1 ? "Media uploaded!" : `${list.length} files uploaded!`)
  } catch (e: any) {
    showToast(extractApiError(e, "Upload failed"), "error")
  } finally {
    uploading.value = false
    uploadProgress.value = 0
    uploadStatus.value = ""
  }
}

function isVideoAsset(asset: any) {
  return asset?.kind === "video" || String(asset?.content_type || "").startsWith("video/")
}

function onFileInput(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (files?.length) uploadFiles(files)
  ;(e.target as HTMLInputElement).value = ""
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  const files = e.dataTransfer?.files
  if (files?.length) uploadFiles(files)
}

async function deleteAsset(id: string) {
  deletingId.value = id
  try {
    await apiFetch(`/media/${id}/`, { method: "DELETE" })
    await refresh()
    showToast("Deleted.")
  } catch {
    showToast("Failed to delete", "error")
  } finally {
    deletingId.value = null
  }
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(str: string) {
  return new Date(str).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}
</script>

<template>
  <div class="media-page">
    <div class="media-header">
      <div>
        <h1 class="media-title">Media Library</h1>
        <p class="media-subtitle">{{ (assets || []).length }} asset{{ (assets || []).length !== 1 ? "s" : "" }}</p>
      </div>
      <button class="btn" style="display:flex;align-items:center;gap:6px" @click="fileInputRef?.click()">
        <span style="font-size:18px;line-height:1">+</span> Upload
      </button>
    </div>

    <div
      class="upload-zone"
      :class="{ 'drag-active': dragOver, uploading }"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop.prevent="onDrop"
      @click="fileInputRef?.click()"
    >
      <input ref="fileInputRef" type="file" accept="image/*,video/*" multiple style="display:none" @change="onFileInput" />
      <template v-if="uploading">
        <div class="upload-spinner"></div>
        <span class="upload-zone-label">Uploading... {{ uploadProgress }}%</span>
        <span v-if="uploadStatus" class="upload-zone-hint">{{ uploadStatus }}</span>
      </template>
      <template v-else>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="upload-icon"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        <span class="upload-zone-label">Drop media here or <u>browse</u></span>
        <span class="upload-zone-hint">PNG, JPG, WEBP, MP4, MOV, WEBM</span>
      </template>
    </div>

    <div v-if="(assets || []).length" class="media-grid">
      <div
        v-for="asset in assets"
        :key="asset.id"
        class="media-card"
        @click="previewAsset = asset"
      >
        <div class="media-card-img">
          <video v-if="isVideoAsset(asset)" :src="asset.file_url" muted playsinline preload="metadata"></video>
          <img v-else :src="asset.file_url" :alt="asset.alt_text || asset.title" />
          <button
            class="media-card-delete"
            :disabled="deletingId === asset.id"
            @click.stop="deleteAsset(asset.id)"
            title="Delete"
          >{{ deletingId === asset.id ? "..." : "×" }}</button>
        </div>
        <div class="media-card-info">
          <span class="media-card-name">{{ asset.title || asset.file_name }}</span>
          <span class="media-card-meta">{{ formatSize(asset.size_bytes) }} · {{ formatDate(asset.created_at) }}</span>
        </div>
      </div>
    </div>

    <div v-else class="media-empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.25"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
      <p>No media yet. Upload your first image or video above.</p>
    </div>

    <Teleport to="body">
      <div v-if="previewAsset" class="lightbox" @click.self="previewAsset = null">
        <div class="lightbox-box">
          <button class="lightbox-close" @click="previewAsset = null">×</button>
          <video v-if="isVideoAsset(previewAsset)" :src="previewAsset.file_url" class="lightbox-img" controls playsinline preload="metadata"></video>
          <img v-else :src="previewAsset.file_url" :alt="previewAsset.title" class="lightbox-img" />
          <div class="lightbox-meta">
            <span class="lightbox-name">{{ previewAsset.title || previewAsset.file_name }}</span>
            <span class="lightbox-detail">{{ previewAsset.file_name }} · {{ formatSize(previewAsset.size_bytes) }} · {{ formatDate(previewAsset.created_at) }}</span>
          </div>
        </div>
      </div>

      <div class="toast-stack">
        <TransitionGroup name="toast">
          <div v-for="t in toasts" :key="t.id" class="toast" :class="t.kind">
            <span class="toast-icon">{{ t.kind === "success" ? "✓" : "×" }}</span>
            {{ t.message }}
          </div>
        </TransitionGroup>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.media-page {
  padding: 36px 40px;
  max-width: 1100px;
  margin: 0 auto;
}

.media-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 24px;
}

.media-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 4px;
}

.media-subtitle {
  font-size: 13px;
  color: var(--muted);
  margin: 0;
}

.upload-zone {
  border: 2px dashed var(--line);
  border-radius: 16px;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  margin-bottom: 32px;
  color: var(--muted);
  background: var(--surface);
}

.upload-zone:hover,
.upload-zone.drag-active {
  border-color: var(--brand);
  background: rgba(127, 162, 147, 0.08);
  color: var(--brand);
}

.upload-zone.uploading {
  pointer-events: none;
  opacity: 0.7;
}

.upload-icon {
  color: inherit;
}

.upload-zone-label {
  font-size: 14px;
  font-weight: 500;
}

.upload-zone-hint {
  font-size: 12px;
  opacity: 0.65;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.upload-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

.media-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  background: var(--surface);
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.15s;
}

.media-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.media-card-img {
  position: relative;
  aspect-ratio: 1;
  background: var(--surface-muted);
  overflow: hidden;
}

.media-card-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.media-card-img video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  background: #111;
}

.media-card-delete {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: white;
  border: 0;
  font-size: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.12s;
}

.media-card:hover .media-card-delete {
  opacity: 1;
}

.media-card-delete:hover {
  background: #c0392b;
}

.media-card-info {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.media-card-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.media-card-meta {
  font-size: 11px;
  color: var(--muted);
}

.media-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 0;
  color: var(--muted);
  font-size: 14px;
}

.media-empty p {
  margin: 0;
}

.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 24px;
}

.lightbox-box {
  position: relative;
  background: var(--panel);
  border-radius: 16px;
  overflow: hidden;
  max-width: 820px;
  width: 100%;
  box-shadow: 0 32px 80px rgba(0, 0, 0, 0.35);
}

.lightbox-close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  border: 0;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.lightbox-close:hover {
  background: rgba(0, 0, 0, 0.75);
}

.lightbox-img {
  width: 100%;
  max-height: 70vh;
  object-fit: contain;
  display: block;
  background: var(--surface-muted);
}

.lightbox-meta {
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-top: 1px solid var(--line);
}

.lightbox-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.lightbox-detail {
  font-size: 12px;
  color: var(--muted);
}

.toast-stack {
  position: fixed;
  bottom: 28px;
  right: 28px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 9999;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  color: white;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  min-width: 220px;
  max-width: 360px;
  pointer-events: auto;
}

.toast.success {
  background: #7fa293;
}

.toast.error {
  background: #c0392b;
}

.toast-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  flex-shrink: 0;
}

.toast-enter-active {
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-leave-active {
  transition: all 0.18s ease-in;
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(12px) scale(0.96);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.97);
}
</style>
