export type UploadMediaAssetResponse = {
  id: string
  title?: string
  file_url: string
  file_name: string
  kind?: string
  content_type?: string
  size_bytes?: number
  created_at: string
}

export function uploadMediaAsset(
  file: File,
  options?: {
    title?: string
    onProgress?: (percent: number) => void
  }
) {
  return new Promise<UploadMediaAssetResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const formData = new FormData()
    formData.append("file", file)
    formData.append("title", options?.title || file.name.replace(/\.[^.]+$/, ""))

    xhr.open("POST", "/api/media-upload", true)
    xhr.responseType = "json"
    xhr.withCredentials = true

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return
      options?.onProgress?.(Math.min(100, Math.round((event.loaded / event.total) * 100)))
    }

    xhr.onload = () => {
      const response = xhr.response
      if (xhr.status >= 200 && xhr.status < 300 && response) {
        options?.onProgress?.(100)
        resolve(response)
        return
      }

      reject(new Error(response?.detail || response?.message || xhr.statusText || "Upload failed."))
    }

    xhr.onerror = () => reject(new Error("Upload failed."))
    xhr.send(formData)
  })
}
