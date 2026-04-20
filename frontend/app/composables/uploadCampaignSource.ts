export type UploadCampaignResponse = {
  id: string
  title: string
  source_file_type: string
  source_media_type: string
  status: string
}

export function uploadCampaignSource(
  file: File,
  options: {
    mediaType: "none" | "video" | "images"
    sourceVideoId?: string
    sourceImageIds?: string[]
    title?: string
    onProgress?: (percent: number) => void
  }
) {
  return new Promise<UploadCampaignResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const formData = new FormData()
    formData.append("source_file", file)
    formData.append("source_media_type", options.mediaType)
    if (options.sourceVideoId) formData.append("source_video", options.sourceVideoId)
    for (const id of options.sourceImageIds || []) formData.append("source_images", id)
    if (options.title?.trim()) formData.append("title", options.title.trim())

    xhr.open("POST", "/api/campaign-upload", true)
    xhr.responseType = "json"
    xhr.withCredentials = true

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return
      options.onProgress?.(Math.min(100, Math.round((event.loaded / event.total) * 100)))
    }

    xhr.onload = () => {
      const response = xhr.response
      if (xhr.status >= 200 && xhr.status < 300 && response) {
        options.onProgress?.(100)
        resolve(response)
        return
      }
      reject(new Error(response?.detail || response?.message || xhr.statusText || "Campaign upload failed."))
    }

    xhr.onerror = () => reject(new Error("Campaign upload failed."))
    xhr.send(formData)
  })
}
