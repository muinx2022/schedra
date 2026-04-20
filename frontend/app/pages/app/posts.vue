<script setup lang="ts">
definePageMeta({ middleware: "auth" })

type Tab = "queue" | "drafts" | "sent"
type Strategy = "draft" | "queue" | "schedule" | "publish"

type MediaAsset = {
  id: string
  title?: string
  file_url: string
  file_name: string
  kind?: string
  size_bytes?: number
  created_at: string
}

const VIDEO_EXT = /\.(mp4|mov|avi|webm|mkv)$/i

type PostMedia = {
  id: string
  media_asset: string
  file_url: string | null
  kind: string
  role: string
  order_index: number
}

type PostTarget = {
  id: string
  social_account: string
  delivery_strategy: string
  delivery_status: string
  scheduled_at: string | null
}

type Post = {
  id: string
  internal_name: string
  caption_text: string
  delivery_strategy: string
  delivery_status: string
  scheduled_at: string | null
  published_at: string | null
  created_at: string
  updated_at: string
  payload: Record<string, any>
  media_items: PostMedia[]
  targets: PostTarget[]
}

type SocialAccount = {
  id: string
  display_name: string
  provider_code: string
  provider_name: string
  channel_code: string
  channel_name: string
  account_type: string
  status: string
  queue_slots: Array<{
    id: string
    weekday: number
    local_time: string
    is_active: boolean
    position: number
  }>
}

type Toast = { id: number; message: string; kind: "success" | "error" }

const route = useRoute()
const router = useRouter()

const activeTab = computed<Tab>({
  get: () => (["queue", "drafts", "sent"].includes(route.query.tab as string) ? route.query.tab as Tab : "queue"),
  set: (val) => router.replace({ query: { ...route.query, tab: val } }),
})

const activeAccount = computed<string>({
  get: () => (route.query.account as string) || "",
  set: (val) => router.replace({ query: { ...route.query, account: val || undefined } }),
})

const selectedPostId = ref<string | null>(null)
const showComposer = ref(false)
const publishingId = ref<string | null>(null)
const deletingId = ref<string | null>(null)
const duplicatingId = ref<string | null>(null)
const pendingDeletePostId = ref<string | null>(null)
const pendingDuplicatePostId = ref<string | null>(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref("")
const dragOver = ref(false)
const saving = ref(false)
const error = ref("")
const fileInputRef = ref<HTMLInputElement | null>(null)
const actionMenuOpen = ref(false)
const actionGroupRef = ref<HTMLElement | null>(null)

const toasts = ref<Toast[]>([])
let toastId = 0

function onDocumentPointerDown(event: PointerEvent) {
  if (!actionMenuOpen.value) return
  const target = event.target
  if (!(target instanceof Node)) return
  if (actionGroupRef.value?.contains(target)) return
  actionMenuOpen.value = false
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocumentPointerDown)
})

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onDocumentPointerDown)
})

const form = reactive({
  caption_text: "",
  social_accounts: [] as string[],
  strategy: "draft" as Strategy,
  post_mode: "single" as "single" | "carousel",
  scheduled_at: "",
})

const selectedAssets = ref<MediaAsset[]>([])

const { data: posts, refresh: refreshPosts } = useAsyncData(
  "posts",
  () => apiFetch<Post[]>("/posts/"),
  { lazy: true, default: () => [] }
)

const { data: accounts } = useAsyncData(
  "post-accounts",
  () => apiFetch<SocialAccount[]>("/accounts/"),
  { lazy: true, default: () => [] }
)

const { data: mediaAssets } = useAsyncData(
  "post-media-assets",
  () => apiFetch<MediaAsset[]>("/media/"),
  { lazy: true, default: () => [] }
)

watch(
  accounts,
  (value) => {
    const availableIds = new Set(value.map((account) => account.id))
    form.social_accounts = form.social_accounts.filter((id) => availableIds.has(id))
    // Only set default account when composer is not editing an existing post
    if (!form.social_accounts.length && value.length && !selectedPostId.value) {
      form.social_accounts = [activeAccount.value || value[0].id]
    }
  },
  { immediate: true }
)

watch(
  () => route.query.post,
  (value) => {
    if (typeof value === "string") {
      const post = posts.value.find((item) => item.id === value)
      if (post) {
        editPost(post)
        showComposer.value = true
      } else {
        selectedPostId.value = value
      }
    } else if (!value) {
      selectedPostId.value = null
      showComposer.value = false
    }
  },
  { immediate: true }
)

const activePosts = computed(() =>
  posts.value.filter((post) => {
    if (activeTab.value === "queue") return ["queued", "scheduled", "publishing"].includes(post.delivery_status)
    if (activeTab.value === "drafts") return post.delivery_status === "draft"
    return ["published", "failed", "canceled"].includes(post.delivery_status)
  }).filter(matchesAccount)
)

const groupedPosts = computed(() => {
  const groups = new Map<string, Post[]>()
  for (const post of activePosts.value) {
    const key = groupLabel(post)
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(post)
  }
  return [...groups.entries()]
})

const currentPost = computed(() =>
  selectedPostId.value ? posts.value.find((post) => post.id === selectedPostId.value) || null : null
)

const selectedAccounts = computed(() =>
  accounts.value.filter((account) => form.social_accounts.includes(account.id))
)
const selectedAccount = computed(() => selectedAccounts.value[0] || null)
const selectedChannelName = computed(() => selectedAccount.value?.channel_name || selectedAccount.value?.provider_name || "Channel")
const selectedAccountIsInstagram = computed(() => selectedAccount.value?.account_type === "instagram_business")
const selectedInstagramModeLabel = computed(() => form.post_mode === "carousel" ? "Carousel" : "Single post")
const selectedChannelDescriptor = computed(() => {
  const t = selectedAccount.value?.account_type
  if (t === "instagram_business") return "Instagram Business"
  if (t === "tiktok_creator") return "TikTok Creator"
  if (t === "youtube_channel") return "YouTube Channel"
  if (t === "personal") return "LinkedIn Profile"
  if (t === "pinterest_board") return "Pinterest Board"
  return "Facebook Page"
})
const selectedInstagramAccounts = computed(() =>
  selectedAccounts.value.filter((account) => account.account_type === "instagram_business")
)
const selectedYoutubeAccounts = computed(() =>
  selectedAccounts.value.filter((account) => account.account_type === "youtube_channel")
)
const selectedVideoAssets = computed(() =>
  selectedAssets.value.filter((a) => a.kind === "video" || (!a.kind && VIDEO_EXT.test(a.file_name || "")))
)
const selectedImageAssets = computed(() =>
  selectedAssets.value.filter((a) => a.kind === "image" || (!a.kind && !VIDEO_EXT.test(a.file_name || "")))
)
const selectedAccountsLabel = computed(() => {
  if (!selectedAccounts.value.length) return "No channels selected"
  if (selectedAccounts.value.length === 1) return selectedAccounts.value[0].display_name
  return `${selectedAccounts.value.length} channels selected`
})

watch(
  selectedAccount,
  (value) => {
    if (!selectedInstagramAccounts.value.length) form.post_mode = "single"
  }
)

const filteredChannel = computed(() =>
  activeAccount.value ? accounts.value.find((account) => account.id === activeAccount.value) || null : null
)

const hasChannels = computed(() => accounts.value.length > 0)
const hasActiveQueueSlots = computed(() =>
  selectedAccounts.value.length > 0 && selectedAccounts.value.every((account) => account.queue_slots?.some((slot) => slot.is_active))
)

const canSaveDraft = computed(() =>
  !!form.caption_text.trim() && !saving.value
)
const canQueue = computed(() =>
  !!form.caption_text.trim() && !!form.social_accounts.length && hasActiveQueueSlots.value && !saving.value
)
const canSchedule = computed(() =>
  !!form.caption_text.trim() && !!form.social_accounts.length && !!form.scheduled_at && !saving.value
)
const canPublishNow = computed(() =>
  !!form.caption_text.trim() && !!form.social_accounts.length && !saving.value
)

const scheduleActionHint = computed(() => {
  if (saving.value) return "Saving in progress"
  if (!form.caption_text.trim()) return "Add a caption first"
  if (!form.social_accounts.length) return "Choose at least one channel"
  if (!form.scheduled_at) return "Pick a date and time"
  return "Use selected time"
})

const nextStepActions = computed(() => [
  {
    strategy: "draft" as Strategy,
    icon: "D",
    label: "Save draft",
    hint: "Keep it editable",
    disabled: !canSaveDraft.value,
  },
  {
    strategy: "queue" as Strategy,
    icon: "Q",
    label: "Add to queue",
    hint: hasActiveQueueSlots.value ? "Use next queue slot" : "Needs active queue slots",
    disabled: !canQueue.value,
  },
  {
    strategy: "schedule" as Strategy,
    icon: "S",
    label: "Schedule",
    hint: scheduleActionHint.value,
    disabled: !canSchedule.value,
  },
  {
    strategy: "publish" as Strategy,
    icon: "P",
    label: "Publish now",
    hint: "Send immediately",
    disabled: !canPublishNow.value,
  },
])

const minDateTime = computed(() => {
  const now = new Date()
  now.setSeconds(0, 0)
  return now.toISOString().slice(0, 16)
})

function showToast(message: string, kind: Toast["kind"] = "success") {
  const id = ++toastId
  toasts.value.push({ id, message, kind })
  setTimeout(() => {
    toasts.value = toasts.value.filter((toast) => toast.id !== id)
  }, 3500)
}

function matchesAccount(post: Post) {
  if (!activeAccount.value) return true
  return post.targets.some((target) => target.social_account === activeAccount.value)
}

function groupLabel(post: Post) {
  const raw = post.scheduled_at || post.published_at || post.created_at
  const date = new Date(raw)
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(today.getDate() + 1)
  if (date.toDateString() === today.toDateString()) return "Today"
  if (date.toDateString() === tomorrow.toDateString()) return "Tomorrow"
  return date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })
}

function accountFor(post: Post) {
  const targetId = post.targets[0]?.social_account
  return accounts.value.find((account) => account.id === targetId) || null
}

function accountDescriptor(account?: SocialAccount | null) {
  if (!account) return "Channel"
  if (account.account_type === "instagram_business") return "Instagram Business"
  if (account.account_type === "tiktok_creator") return "TikTok Creator"
  if (account.account_type === "youtube_channel") return "YouTube Channel"
  if (account.account_type === "personal") return "LinkedIn Profile"
  if (account.account_type === "pinterest_board") return "Pinterest Board"
  return "Facebook Page"
}

function accountBadgeLabel(account?: SocialAccount | null) {
  if (!account) return "CH"
  if (account.account_type === "instagram_business") return "IG"
  if (account.account_type === "tiktok_creator") return "TT"
  if (account.account_type === "youtube_channel") return "YT"
  if (account.account_type === "personal") return "LI"
  if (account.account_type === "pinterest_board") return "PT"
  return "FB"
}

function accountMonogram(account?: SocialAccount | null) {
  if (!account?.display_name) return "?"
  return account.display_name.trim().charAt(0).toUpperCase()
}

function accountQueueCount(account?: SocialAccount | null) {
  return account?.queue_slots.filter((slot) => slot.is_active).length || 0
}

function accountPlatformClass(account?: SocialAccount | null) {
  const providerCode = (account?.provider_code || account?.channel_code || "").toLowerCase()
  if (providerCode === "instagram") return "instagram"
  if (providerCode === "tiktok") return "tiktok"
  if (providerCode === "youtube") return "youtube"
  if (providerCode === "linkedin") return "linkedin"
  if (providerCode === "pinterest") return "pinterest"
  if (providerCode === "facebook") return "facebook"
  if (account?.account_type === "instagram_business") return "instagram"
  if (account?.account_type === "tiktok_creator") return "tiktok"
  if (account?.account_type === "youtube_channel") return "youtube"
  if (account?.account_type === "personal") return "linkedin"
  if (account?.account_type === "pinterest_board") return "pinterest"
  return "facebook"
}

function accountTooltip(account?: SocialAccount | null) {
  if (!account) return "Channel"
  return `${accountBadgeLabel(account)}: ${account.display_name}`
}

function toggleSelectedAccount(accountId: string) {
  if (form.social_accounts.includes(accountId)) {
    form.social_accounts = form.social_accounts.filter((id) => id !== accountId)
    return
  }
  form.social_accounts = [...form.social_accounts, accountId]
}

function platformName(code: string) {
  const names: Record<string, string> = {
    facebook: "Facebook", instagram: "Instagram", tiktok: "TikTok",
    linkedin: "LinkedIn", youtube: "YouTube", pinterest: "Pinterest",
  }
  return names[code] ?? code
}

const groupedChannels = computed(() => {
  const groups: Record<string, SocialAccount[]> = {}
  for (const acc of accounts.value ?? []) {
    const key = accountPlatformClass(acc)
    if (!groups[key]) groups[key] = []
    groups[key].push(acc)
  }
  return groups
})

const groupSelectAll = reactive<Record<string, boolean>>({})
const groupModal = ref({ open: false, platform: "", search: "" })
const groupModalSelected = ref<string[]>([])
const channelSearch = ref("")

const filteredGroupedChannels = computed(() => {
  const query = channelSearch.value.trim().toLowerCase()
  if (!query) return groupedChannels.value

  const groups: Record<string, SocialAccount[]> = {}
  for (const [platform, groupAccs] of Object.entries(groupedChannels.value)) {
    const matches = groupAccs.filter((acc) =>
      [acc.display_name, acc.channel_name, acc.provider_name, accountDescriptor(acc)]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(query))
    )
    if (matches.length) groups[platform] = matches
  }
  return groups
})

const modalAccounts = computed(() =>
  (groupedChannels.value[groupModal.value.platform] ?? []).filter((acc) =>
    acc.display_name.toLowerCase().includes(groupModal.value.search.toLowerCase())
  )
)

function selectedCountForGroup(platform: string) {
  const ids = (groupedChannels.value[platform] ?? []).map((a) => a.id)
  return form.social_accounts.filter((id) => ids.includes(id)).length
}

function visibleAccountsForGroup(groupAccs: SocialAccount[]) {
  return channelSearch.value.trim() ? groupAccs.slice(0, 40) : groupAccs.slice(0, 8)
}

function hiddenAccountsForGroup(groupAccs: SocialAccount[]) {
  return Math.max(0, groupAccs.length - visibleAccountsForGroup(groupAccs).length)
}

function toggleGroupSelectAll(platform: string, checked: boolean) {
  const ids = (groupedChannels.value[platform] ?? []).map((a) => a.id)
  groupSelectAll[platform] = checked
  if (checked) {
    form.social_accounts = [...new Set([...form.social_accounts, ...ids])]
  } else {
    form.social_accounts = form.social_accounts.filter((id) => !ids.includes(id))
  }
}

function openGroupModal(platform: string) {
  groupModal.value = { open: true, platform, search: "" }
  const ids = (groupedChannels.value[platform] ?? []).map((a) => a.id)
  const already = form.social_accounts.filter((id) => ids.includes(id))
  groupModalSelected.value = already.length ? already : [...ids]
}

function confirmGroupModal() {
  const platform = groupModal.value.platform
  const ids = (groupedChannels.value[platform] ?? []).map((a) => a.id)
  form.social_accounts = [
    ...form.social_accounts.filter((id) => !ids.includes(id)),
    ...groupModalSelected.value,
  ]
  groupModal.value.open = false
}

function accountModeLabel(account?: SocialAccount | null, post?: Post | null) {
  if (!account) return "Post"
  if (account.account_type === "instagram_business") {
    return post && postModeFor(post) === "carousel" ? "Carousel" : "Single post"
  }
  return "Feed post"
}

function strategyFor(post: Post): Strategy {
  if (post.delivery_status === "scheduled" || post.delivery_strategy === "schedule") return "schedule"
  if (post.delivery_status === "queued" || post.delivery_strategy === "queue") return "queue"
  return "draft"
}

function postModeFor(post: Post): "single" | "carousel" {
  const mode = post.payload?.feed_post?.mode
  return mode === "carousel" ? "carousel" : "single"
}

function mediaValidationError(): string | null {
  const images = selectedImageAssets.value
  const videos = selectedVideoAssets.value
  const hasImages = images.length > 0
  const hasVideos = videos.length > 0
  const isMixed = hasImages && hasVideos

  for (const account of selectedAccounts.value) {
    const t = account.account_type

    if (t === "youtube_channel") {
      if (!hasVideos) return "YouTube requires a video file."
      if (videos.length > 1) return "YouTube only supports one video per post."
      if (hasImages) return "YouTube posts cannot include images alongside a video."
    } else if (t === "instagram_business") {
      if (isMixed) return "Instagram doesn't support mixing images and videos in one post."
      if (form.post_mode === "carousel") {
        if (hasVideos) return "Instagram carousel only supports images."
        if (images.length < 2) return "Instagram carousel requires at least 2 images."
      } else {
        if (selectedAssets.value.length > 1) return "Instagram single post requires exactly one image or video."
      }
    } else if (t === "page") {
      if (isMixed) return "Facebook doesn't support mixing images and videos in one post."
      if (hasVideos && videos.length > 1) return "Facebook only supports one video per post."
    } else if (t === "personal") {
      if (isMixed) return "LinkedIn doesn't support mixing images and videos in one post."
      if (hasVideos && videos.length > 1) return "LinkedIn only supports one video per post."
    } else if (t === "tiktok_creator") {
      if (isMixed) return "TikTok doesn't support mixing images and videos in one post."
      if (hasVideos && videos.length > 1) return "TikTok only supports one video per post."
    } else if (t === "pinterest_board") {
      if (isMixed) return "Pinterest doesn't support mixing images and videos in one post."
      if (hasVideos && videos.length > 1) return "Pinterest only supports one video per post."
      if (hasImages && images.length > 5) return "Pinterest carousel supports at most 5 images."
    }
  }
  return null
}

function captionValidationError(): string | null {
  const caption = form.caption_text.trim()
  for (const account of selectedAccounts.value) {
    if (account.account_type === "pinterest_board" && caption.length > 500) {
      return `Pinterest caption must be 500 characters or less (currently ${caption.length}).`
    }
  }
  return null
}

function resetComposer(strategy: Strategy = "draft") {
  selectedPostId.value = null
  form.caption_text = ""
  form.strategy = strategy
  form.post_mode = "single"
  form.scheduled_at = ""
  form.social_accounts = activeAccount.value || accounts.value[0]?.id ? [activeAccount.value || accounts.value[0]?.id] : []
  selectedAssets.value = []
  error.value = ""
}

function startNewPost(strategy: Strategy = "draft") {
  resetComposer(strategy)
  actionMenuOpen.value = false
  showComposer.value = true
  router.replace({ query: { ...route.query, post: undefined } })
}

function editPost(post: Post) {
  selectedPostId.value = post.id
  showComposer.value = true
  actionMenuOpen.value = false
  router.replace({ query: { ...route.query, post: post.id } })
  form.caption_text = post.caption_text || ""
  form.social_accounts = post.targets.map((target) => target.social_account).filter(Boolean)
  if (!form.social_accounts.length) {
    form.social_accounts = activeAccount.value || accounts.value[0]?.id ? [activeAccount.value || accounts.value[0]?.id] : []
  }
  form.scheduled_at = post.scheduled_at ? new Date(post.scheduled_at).toISOString().slice(0, 16) : ""
  form.strategy = strategyFor(post)
  form.post_mode = postModeFor(post)
  selectedAssets.value = (post.media_items || [])
    .slice()
    .sort((a, b) => a.order_index - b.order_index)
    .map((item) => ({
      id: item.media_asset,
      title: "",
      file_url: item.file_url || "",
      file_name: "",
      kind: item.kind,
      created_at: post.created_at,
    }))
  error.value = ""
}

function closeComposer() {
  showComposer.value = false
  actionMenuOpen.value = false
  resetComposer()
  router.replace({ query: { ...route.query, post: undefined } })
}

function normalizePostAssets(post: Post): MediaAsset[] {
  return (post.media_items || [])
    .slice()
    .sort((a, b) => a.order_index - b.order_index)
    .map((item) => ({
      id: item.media_asset,
      title: "",
      file_url: item.file_url || "",
      file_name: "",
      kind: item.kind,
      created_at: post.created_at,
    }))
}

async function duplicatePost(post: Post) {
  try {
    await apiFetch<Post>("/posts/", {
      method: "POST",
      body: buildPostPayload("draft", post.caption_text, post.targets.map((target) => target.social_account).filter(Boolean), normalizePostAssets(post), "", postModeFor(post)),
    })
    activeTab.value = "drafts"
    await refreshPosts()
    showToast("Draft duplicated.")
  } catch (e: any) {
    showToast(extractApiError(e, "Failed to duplicate post"), "error")
  }
}

function requestDuplicatePost(postId: string) {
  pendingDuplicatePostId.value = postId
}

function cancelDuplicatePost() {
  pendingDuplicatePostId.value = null
}

const pendingDuplicatePost = computed(() =>
  pendingDuplicatePostId.value ? posts.value.find((post) => post.id === pendingDuplicatePostId.value) || null : null
)

async function confirmDuplicatePost() {
  if (!pendingDuplicatePost.value) return

  duplicatingId.value = pendingDuplicatePost.value.id
  try {
    await duplicatePost(pendingDuplicatePost.value)
    pendingDuplicatePostId.value = null
  } finally {
    duplicatingId.value = null
  }
}

async function uploadFiles(files: FileList | File[]) {
  const list = Array.from(files).filter((file) =>
    file.type.startsWith("image/") || file.type.startsWith("video/")
  )
  if (!list.length) {
    error.value = "Only image and video files are supported."
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = ""
  error.value = ""
  try {
    const uploaded: MediaAsset[] = []
    for (let index = 0; index < list.length; index++) {
      const file = list[index]
      uploadStatus.value = `Uploading ${index + 1}/${list.length}: ${file.name}`
      const asset = await uploadMediaAsset(file, {
        onProgress(percent) {
          const normalized = Math.min(percent, 99)
          uploadProgress.value = Math.round(((index + normalized / 100) / list.length) * 100)
          if (percent >= 100) {
            uploadStatus.value = `Processing ${index + 1}/${list.length}: ${file.name}`
          }
        },
      })
      uploadProgress.value = Math.round(((index + 1) / list.length) * 100)
      uploaded.push(asset)
    }
    for (const asset of uploaded) addAsset(asset)
    await refreshNuxtData("post-media-assets")
    const videoCount = uploaded.filter((a) => a.kind === "video" || VIDEO_EXT.test(a.file_name || "")).length
    const imageCount = uploaded.length - videoCount
    const parts: string[] = []
    if (imageCount) parts.push(`${imageCount} image${imageCount > 1 ? "s" : ""}`)
    if (videoCount) parts.push(`${videoCount} video${videoCount > 1 ? "s" : ""}`)
    showToast(`${parts.join(" and ")} attached.`)
  } catch (e: any) {
    showToast(extractApiError(e, "Upload failed"), "error")
  } finally {
    uploading.value = false
    uploadProgress.value = 0
    uploadStatus.value = ""
  }
}

function onFileInput(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (files?.length) uploadFiles(files)
  ;(event.target as HTMLInputElement).value = ""
}

function onDrop(event: DragEvent) {
  dragOver.value = false
  const files = event.dataTransfer?.files
  if (files?.length) uploadFiles(files)
}

function addAsset(asset: MediaAsset) {
  if (!selectedAssets.value.some((item) => item.id === asset.id)) selectedAssets.value.push(asset)
}

function isVideoAsset(asset?: MediaAsset | null) {
  if (!asset) return false
  return asset.kind === "video" || VIDEO_EXT.test(asset.file_name || "")
}

function removeAsset(index: number) {
  selectedAssets.value.splice(index, 1)
}

function moveAsset(index: number, direction: -1 | 1) {
  const next = index + direction
  if (next < 0 || next >= selectedAssets.value.length) return
  const clone = [...selectedAssets.value]
  ;[clone[index], clone[next]] = [clone[next], clone[index]]
  selectedAssets.value = clone
}

function buildMediaItems(assets: MediaAsset[]) {
  return assets.map((asset, index) => ({
    media_asset: asset.id,
    kind: asset.kind || (VIDEO_EXT.test(asset.file_name || "") ? "video" : "image"),
    role: index === 0 ? "primary" : "secondary",
    order_index: index,
  }))
}

function buildTargets(strategy: Strategy, socialAccounts: string[], scheduledAt: string) {
  if (!socialAccounts.length) return []
  const deliveryStrategy = strategy === "publish" || strategy === "draft" ? "now" : strategy
  return socialAccounts.map((socialAccount) => ({
    social_account: socialAccount,
    delivery_strategy: deliveryStrategy,
    scheduled_at: strategy === "schedule" && scheduledAt ? scheduledAt : null,
  }))
}

function buildPostPayload(
  strategy: Strategy,
  caption: string,
  socialAccounts: string[],
  assets: MediaAsset[],
  scheduledAt: string,
  postMode: "single" | "carousel" = "single"
) {
  const payload: Record<string, any> = {
    caption_text: caption,
    content_type: "feed_post",
    editorial_state: "draft",
    delivery_strategy: strategy === "publish" ? "now" : strategy === "draft" ? "now" : strategy,
    delivery_status: "draft",
    scheduled_at: strategy === "schedule" ? scheduledAt : null,
    payload: { version: 1, feed_post: { mode: postMode } },
    media_items: buildMediaItems(assets),
  }
  // Only include targets when accounts are explicitly provided.
  // Omitting targets on PATCH preserves existing targets on the server.
  if (socialAccounts.length) {
    payload.targets = buildTargets(strategy, socialAccounts, scheduledAt)
  }
  return payload
}

async function persistPostForAccount(strategy: Strategy, accountId: string | null) {
  const payload = buildPostPayload(
    strategy,
    form.caption_text.trim(),
    accountId ? [accountId] : [],
    selectedAssets.value,
    form.scheduled_at,
    form.post_mode
  )

  if (selectedPostId.value) {
    return await apiFetch<Post>(`/posts/${selectedPostId.value}/`, {
      method: "PATCH",
      body: payload,
    })
  }

  return await apiFetch<Post>("/posts/", {
    method: "POST",
    body: payload,
  })
}

async function dispatchPost(post: Post, strategy: Strategy) {
  if (strategy === "publish") {
    await apiFetch(`/posts/${post.id}/publish_now/`, { method: "POST", body: {} })
  } else if (strategy === "queue") {
    await apiFetch(`/posts/${post.id}/queue/`, { method: "POST", body: {} })
  } else if (strategy === "schedule") {
    await apiFetch(`/posts/${post.id}/schedule/`, {
      method: "POST",
      body: { scheduled_at: form.scheduled_at },
    })
  }
}

async function submit(strategy: Strategy) {
  if (!form.caption_text.trim()) return
  if ((strategy === "publish" || strategy === "queue" || strategy === "schedule") && !form.social_accounts.length) {
    error.value = "Select at least one channel before continuing."
    return
  }
  const mediaErr = mediaValidationError()
  if (mediaErr) { error.value = mediaErr; return }
  const captionErr = captionValidationError()
  if (captionErr) { error.value = captionErr; return }
  if (strategy === "queue" && !hasActiveQueueSlots.value) {
    error.value = "One or more selected channels have no active queue slots."
    return
  }
  if (strategy === "schedule" && !form.scheduled_at) {
    error.value = "Choose a schedule time."
    return
  }

  saving.value = true
  error.value = ""
  try {
    // Edit mode: update single existing post with first account
    if (selectedPostId.value) {
      const post = await persistPostForAccount(strategy, form.social_accounts[0] || null)
      await dispatchPost(post, strategy)
    } else {
      // New post: one post per account (or one draft if no accounts)
      const accountIds = form.social_accounts.length ? form.social_accounts : [null]
      const createdPosts = await Promise.all(accountIds.map((id) => persistPostForAccount(strategy, id)))
      await Promise.all(createdPosts.map((post) => dispatchPost(post, strategy)))
    }

    if (strategy === "publish") {
      activeTab.value = "sent"
      showToast(form.social_accounts.length > 1 ? `Published to ${form.social_accounts.length} channels.` : "Post published.")
    } else if (strategy === "queue") {
      activeTab.value = "queue"
      showToast(form.social_accounts.length > 1 ? `Added to queue for ${form.social_accounts.length} channels.` : "Post added to queue.")
    } else if (strategy === "schedule") {
      activeTab.value = "queue"
      showToast(form.social_accounts.length > 1 ? `Scheduled for ${form.social_accounts.length} channels.` : "Post scheduled.")
    } else {
      activeTab.value = "drafts"
      showToast(selectedPostId.value ? "Draft updated." : "Draft saved.")
    }

    await refreshPosts()
    closeComposer()
  } catch (e: any) {
    error.value = extractApiError(e, "Failed to save post")
    showToast(error.value, "error")
  } finally {
    saving.value = false
  }
}

function runNextStep(strategy: Strategy) {
  actionMenuOpen.value = false
  submit(strategy)
}

async function publishNow(postId: string) {
  publishingId.value = postId
  try {
    await apiFetch(`/posts/${postId}/publish_now/`, { method: "POST", body: {} })
    await refreshPosts()
    activeTab.value = "sent"
    showToast("Post published.")
  } catch (e: any) {
    showToast(extractApiError(e, "Failed to publish"), "error")
  } finally {
    publishingId.value = null
  }
}

function requestDeletePost(postId: string) {
  pendingDeletePostId.value = postId
}

function cancelDeletePost() {
  pendingDeletePostId.value = null
}

const pendingDeletePost = computed(() =>
  pendingDeletePostId.value ? posts.value.find((post) => post.id === pendingDeletePostId.value) || null : null
)

async function confirmDeletePost() {
  if (!pendingDeletePostId.value) return

  const postId = pendingDeletePostId.value

  deletingId.value = postId
  try {
    await apiFetch(`/posts/${postId}/`, { method: "DELETE" })
    if (selectedPostId.value === postId) closeComposer()
    await refreshPosts()
    pendingDeletePostId.value = null
    showToast("Post deleted.")
  } catch (e: any) {
    showToast(extractApiError(e, "Failed to delete"), "error")
  } finally {
    deletingId.value = null
  }
}

function statusTone(status: string) {
  if (status === "published") return "success"
  if (status === "failed") return "danger"
  if (status === "queued" || status === "scheduled") return "amber"
  if (status === "publishing") return "brand"
  return "muted"
}

function statusLabel(status: string) {
  if (status === "queued") return "Queued"
  if (status === "scheduled") return "Scheduled"
  if (status === "publishing") return "Publishing"
  if (status === "published") return "Published"
  if (status === "failed") return "Failed"
  if (status === "canceled") return "Canceled"
  return "Draft"
}

function shortDateTime(value?: string | null) {
  if (!value) return "No date"
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function relativeTime(value: string) {
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
  if (!text) return "Untitled post"
  return text.length > 110 ? `${text.slice(0, 110)}...` : text
}

function postExcerpt(post: Post) {
  const text = post.caption_text?.trim()
  if (!text) return "Add a caption to preview how this post will read in feed."
  return text.length > 220 ? `${text.slice(0, 220)}...` : text
}

function postTime(post: Post) {
  const raw = post.scheduled_at || post.published_at || post.created_at
  return new Date(raw).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  })
}

function primaryMedia(post: Post) {
  return (post.media_items || [])
    .slice()
    .sort((a, b) => a.order_index - b.order_index)[0] || null
}

function previewTime() {
  if (form.scheduled_at) return `Schedule ready for ${shortDateTime(form.scheduled_at)}`
  return "Choose an action below"
}

function pageHint() {
  if (!hasChannels.value) return "Connect a channel before publishing."
  if (!selectedAccounts.value.length) return "Choose at least one channel to publish."
  if (!hasActiveQueueSlots.value) return "Queue needs an active slot on every selected channel."
  const mediaErr = mediaValidationError()
  if (mediaErr) return mediaErr
  const captionErr = captionValidationError()
  if (captionErr) return captionErr
  return `${selectedAccounts.value.length} channel${selectedAccounts.value.length === 1 ? "" : "s"} ready`
}
</script>

<template>
  <div class="posts-workspace">
    <section class="posts-shell">
      <header class="posts-header">
        <div class="posts-header-main">
          <div class="posts-icon">P</div>
          <div>
            <h1 class="posts-title">{{ filteredChannel?.display_name || "All Channels" }}</h1>
            <p class="posts-subtitle">Manage drafts, queue, and publishing across every connected channel.</p>
          </div>
        </div>

        <div class="posts-header-actions">
          <button class="header-btn" type="button">List</button>
          <NuxtLink to="/app/calendar" class="header-btn">Calendar</NuxtLink>
          <button class="btn" @click="startNewPost('draft')">+ New Post</button>
        </div>
      </header>

      <div class="posts-toolbar">
        <nav class="posts-tabs">
          <button class="tab-btn" :class="{ active: activeTab === 'queue' }" @click="activeTab = 'queue'">
            Queue <span>{{ posts.filter((post) => ['queued', 'scheduled', 'publishing'].includes(post.delivery_status) && matchesAccount(post)).length }}</span>
          </button>
          <button class="tab-btn" :class="{ active: activeTab === 'drafts' }" @click="activeTab = 'drafts'">
            Drafts <span>{{ posts.filter((post) => post.delivery_status === 'draft' && matchesAccount(post)).length }}</span>
          </button>
          <button class="tab-btn" :class="{ active: activeTab === 'sent' }" @click="activeTab = 'sent'">
            Sent <span>{{ posts.filter((post) => ['published', 'failed', 'canceled'].includes(post.delivery_status) && matchesAccount(post)).length }}</span>
          </button>
        </nav>

        <div class="toolbar-filters">
          <button class="toolbar-chip" type="button">
            {{ filteredChannel ? filteredChannel.display_name : "All Channels" }}
          </button>
          <button v-if="filteredChannel" class="toolbar-chip" type="button" @click="activeAccount = ''">
            Clear filter
          </button>
        </div>
      </div>

      <div v-if="!activePosts.length" class="posts-empty">
        <strong>No posts in this view</strong>
        <p>Create a post or switch to another tab.</p>
        <button class="btn secondary" @click="startNewPost('draft')">New post</button>
      </div>

      <div v-else class="posts-feed">
        <section v-for="[label, group] in groupedPosts" :key="label" class="post-group">
          <div class="group-label">{{ label }}</div>

          <article v-for="post in group" :key="post.id" class="timeline-row">
            <div class="timeline-time">{{ postTime(post) }}</div>

            <div class="timeline-card" :class="{ active: selectedPostId === post.id }">
              <div class="timeline-card-body" @click="editPost(post)">
                <div class="timeline-card-main">
                  <div class="post-account-line">
                    <div class="post-avatar" :class="accountPlatformClass(accountFor(post))">
                      <PlatformIcon v-if="accountFor(post)" :platform="accountPlatformClass(accountFor(post))" :size="17" />
                      <span v-else>P</span>
                    </div>
                    <div class="post-account-copy">
                      <strong>{{ accountFor(post)?.display_name || "No channel selected" }}</strong>
                      <span>{{ statusLabel(post.delivery_status) }} · {{ shortDateTime(post.scheduled_at || post.published_at || post.created_at) }}</span>
                    </div>
                  </div>

                  <div class="post-body-copy">
                    <strong class="post-row-title">{{ postTitle(post) }}</strong>
                    <p class="post-excerpt">{{ postExcerpt(post) }}</p>
                  </div>

                  <div class="post-card-footer">
                    <span>You created this {{ relativeTime(post.created_at) }}</span>
                    <span>{{ accountModeLabel(accountFor(post), post) }}</span>
                    <span>{{ post.media_items?.length || 0 }} media</span>
                  </div>
                </div>

                <div v-if="primaryMedia(post)" class="timeline-media">
                  <video v-if="isVideoAsset(primaryMedia(post))" :src="primaryMedia(post)?.file_url || ''" muted playsinline preload="metadata"></video>
                  <img v-else :src="primaryMedia(post)?.file_url || ''" :alt="postTitle(post)" />
                </div>
              </div>

              <div class="timeline-actions">
                <div class="timeline-actions-primary">
                  <span class="action-label">Quick action</span>
                  <button
                    v-if="['draft', 'queued', 'scheduled', 'failed', 'canceled'].includes(post.delivery_status)"
                    class="mini-btn"
                    :disabled="publishingId === post.id"
                    @click.stop="publishNow(post.id)"
                  >
                    {{ publishingId === post.id ? "Publishing..." : "Publish Now" }}
                  </button>
                  <button
                    v-else
                    class="mini-btn"
                    @click.stop="editPost(post)"
                  >
                    View post
                  </button>
                </div>

                <div class="timeline-actions-secondary">
                  <span class="action-label">Manage</span>
                  <div class="action-cluster">
                    <button class="icon-btn" @click.stop="editPost(post)">Edit</button>
                    <button class="icon-btn" @click.stop="requestDuplicatePost(post.id)">Duplicate</button>
                    <button
                      class="icon-btn danger"
                      :disabled="deletingId === post.id"
                      @click.stop="requestDeletePost(post.id)"
                    >
                      {{ deletingId === post.id ? "Deleting..." : "Delete" }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </section>
      </div>
    </section>

    <div v-if="showComposer" class="composer-overlay" @click.self="closeComposer" @dragover.prevent @drop.prevent>
      <div class="composer-modal" :class="{ 'has-channels': hasChannels }">
        <aside v-if="hasChannels" class="channel-rail composer-channels">
          <div class="channel-rail-head">
            <div>
              <p class="editor-label">Channels</p>
              <strong>Publish destinations</strong>
            </div>
            <span class="channel-rail-count">{{ selectedAccounts.length }} / {{ accounts.length }}</span>
          </div>

          <input
            v-model="channelSearch"
            class="channel-search-input"
            type="search"
            placeholder="Search channels..."
          />

          <div class="channel-rail-scroll">
            <div v-for="(groupAccs, platform) in filteredGroupedChannels" :key="platform" class="channel-group">
              <div class="channel-group-header">
                <span class="channel-group-label">{{ platformName(String(platform)) }}</span>
                <span class="channel-group-count">{{ selectedCountForGroup(String(platform)) }} / {{ (groupedChannels[String(platform)] ?? []).length }}</span>
              </div>

              <div class="channel-group-actions">
                <button class="channel-group-action" type="button" @click="toggleGroupSelectAll(String(platform), true)">All</button>
                <button class="channel-group-action" type="button" @click="toggleGroupSelectAll(String(platform), false)">None</button>
                <button
                  v-if="groupAccs.length > visibleAccountsForGroup(groupAccs).length"
                  class="channel-group-action"
                  type="button"
                  @click="openGroupModal(String(platform))"
                >
                  Manage
                </button>
              </div>

              <div class="channel-pill-row vertical">
                <button
                  v-for="account in visibleAccountsForGroup(groupAccs)"
                  :key="account.id"
                  class="channel-pill"
                  :class="{ selected: form.social_accounts.includes(account.id) }"
                  :title="accountTooltip(account)"
                  @click="toggleSelectedAccount(account.id)"
                >
                  <span class="channel-pill-avatar" :class="accountPlatformClass(account)">
                    <PlatformIcon :platform="accountPlatformClass(account)" :size="16" />
                  </span>
                  <span class="channel-pill-meta">
                    <strong>{{ account.display_name }}</strong>
                    <small>{{ accountDescriptor(account) }}</small>
                  </span>
                  <span class="channel-pill-badge" :class="accountPlatformClass(account)">{{ accountBadgeLabel(account) }}</span>
                </button>
              </div>

              <button
                v-if="hiddenAccountsForGroup(groupAccs)"
                class="channel-show-more"
                type="button"
                @click="openGroupModal(String(platform))"
              >
                Show {{ hiddenAccountsForGroup(groupAccs) }} more
              </button>
            </div>

            <div v-if="!Object.keys(filteredGroupedChannels).length" class="channel-empty-search">
              No channels match this search.
            </div>
          </div>
        </aside>

        <section class="editor-panel composer-editor">
          <div class="editor-header">
            <div>
              <p class="editor-kicker">{{ currentPost ? "Editing existing post" : "New post" }}</p>
              <h2>{{ currentPost ? "Refine and dispatch" : "Build the next post" }}</h2>
            </div>
            <div class="editor-header-actions">
              <button class="pill-btn" @click="startNewPost('draft')">Reset</button>
              <button class="pill-btn" @click="closeComposer">Close</button>
            </div>
          </div>

          <div v-if="!hasChannels" class="editor-alert warning">
            <strong>No channels connected.</strong>
            <span>Connect a channel before queueing, scheduling, or publishing.</span>
            <NuxtLink to="/app/settings" class="editor-link">Open settings</NuxtLink>
          </div>

          <div v-if="error" class="editor-alert danger">
            {{ error }}
          </div>

          <input ref="fileInputRef" type="file" accept="image/*,video/mp4,video/quicktime,video/webm,video/x-msvideo" multiple style="display:none" @change="onFileInput" />

          <template v-if="false">
            <div v-for="(groupAccs, platform) in groupedChannels" :key="platform" class="channel-group">
              <div class="channel-group-header">
                <span class="channel-group-label">{{ platformName(String(platform)) }}</span>
                <span class="channel-group-count">{{ groupAccs.length }}</span>
              </div>

              <div v-if="groupAccs.length <= 10" class="channel-pill-row">
                <button
                  v-for="account in groupAccs"
                  :key="account.id"
                  class="channel-pill"
                  :class="{ selected: form.social_accounts.includes(account.id) }"
                  :title="accountTooltip(account)"
                  @click="toggleSelectedAccount(account.id)"
                >
                  <span class="channel-pill-avatar" :class="accountPlatformClass(account)">
                    <PlatformIcon :platform="accountPlatformClass(account)" :size="16" />
                  </span>
                  <span class="channel-pill-meta">
                    <strong>{{ account.display_name }}</strong>
                    <small>{{ accountDescriptor(account) }}</small>
                    <span>{{ accountDescriptor(account) }} · {{ account.queue_slots.filter((slot) => slot.is_active).length }} queue slots</span>
                  </span>
                  <span class="channel-pill-badge" :class="accountPlatformClass(account)">{{ accountBadgeLabel(account) }}</span>
                </button>
              </div>

              <div v-else class="channel-group-compact">
                <label class="channel-group-select-all">
                  <input
                    type="checkbox"
                    :checked="groupSelectAll[String(platform)]"
                    @change="(e) => toggleGroupSelectAll(String(platform), (e.target as HTMLInputElement).checked)"
                  />
                  Select all ({{ groupAccs.length }})
                </label>
                <button
                  class="channel-group-select-btn"
                  :disabled="groupSelectAll[String(platform)]"
                  @click="openGroupModal(String(platform))"
                >
                  Select ({{ selectedCountForGroup(String(platform)) }})
                </button>
              </div>
            </div>

          </template>

          <div v-if="selectedInstagramAccounts.length" class="ig-type-row">
            <span class="editor-label">Post type</span>
            <div class="ig-type-toggle">
              <button class="ig-type-opt" :class="{ active: form.post_mode === 'single' }" @click="form.post_mode = 'single'">Single</button>
              <button class="ig-type-opt" :class="{ active: form.post_mode === 'carousel' }" @click="form.post_mode = 'carousel'">Carousel</button>
            </div>
            <span class="ig-type-req">
              <template v-if="form.post_mode === 'single'">{{ selectedAssets.length === 1 ? '1 image · ready' : `1 image needed` }}</template>
              <template v-else>{{ selectedAssets.length >= 2 ? `${selectedAssets.length} images · ready` : `2+ images needed` }}</template>
            </span>
          </div>

          <div class="editor-block grow">
            <label class="editor-label">Caption</label>
            <textarea
              v-model="form.caption_text"
              class="caption-input"
              placeholder="Write the caption here..."
            />
          </div>

          <div class="editor-block">
            <div class="media-strip">
              <div
                v-for="(asset, index) in selectedAssets"
                :key="asset.id"
                class="media-thumb"
              >
                <video v-if="isVideoAsset(asset)" :src="asset.file_url" muted playsinline preload="metadata"></video>
                <img v-else :src="asset.file_url" :alt="asset.title || asset.file_name" />
                <div class="media-thumb-actions">
                  <button class="media-icon-btn" :disabled="index === 0" @click="moveAsset(index, -1)">←</button>
                  <button class="media-icon-btn" :disabled="index === selectedAssets.length - 1" @click="moveAsset(index, 1)">→</button>
                  <button class="media-icon-btn danger" @click="removeAsset(index)">×</button>
                </div>
              </div>
              <button
                class="media-add-btn"
                :class="{ empty: !selectedAssets.length, 'drag-active': dragOver }"
                @click="fileInputRef?.click()"
                @dragover.prevent="dragOver = true"
                @dragleave="dragOver = false"
                @drop.prevent="onDrop"
              >
                <span class="media-add-icon">{{ uploading ? "..." : "+" }}</span>
                <span v-if="uploading">{{ uploadProgress }}%</span>
                <span v-else>{{ selectedAssets.length ? "Add media" : "Drag & drop or\nselect media" }}</span>
                <span v-if="uploading && uploadStatus">{{ uploadStatus }}</span>
              </button>
            </div>
          </div>

          <div class="editor-footer">
            <div class="editor-footnote">
              <strong>{{ pageHint() }}</strong>
              <div class="schedule-row">
                <input v-model="form.scheduled_at" type="datetime-local" :min="minDateTime" class="schedule-input" />
                <span class="schedule-note">for Schedule</span>
              </div>
            </div>

            <div class="editor-actions">
              <div ref="actionGroupRef" class="next-action-group" :class="{ open: actionMenuOpen }">
                <button
                  class="btn next-action-trigger"
                  type="button"
                  :disabled="saving || !form.caption_text.trim()"
                  @click="actionMenuOpen = !actionMenuOpen"
                >
                  Next step
                  <span>v</span>
                </button>
                <div v-if="actionMenuOpen" class="next-action-menu">
                  <div
                    v-for="action in nextStepActions"
                    :key="action.strategy"
                    class="next-action-wrap"
                    :data-tooltip="action.strategy === 'schedule' && action.disabled ? action.hint : null"
                  >
                    <button
                      class="next-action-item"
                      type="button"
                      :disabled="action.disabled"
                      @click="runNextStep(action.strategy)"
                    >
                      <span class="next-action-icon" aria-hidden="true">{{ action.icon }}</span>
                      <span class="next-action-copy">
                        <strong>{{ action.label }}</strong>
                        <span>{{ action.hint }}</span>
                      </span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <aside class="preview-panel composer-preview">
          <p class="preview-kicker">Preview</p>

          <div class="preview-scroll">
            <div v-for="account in selectedAccounts" :key="account.id" class="channel-preview-card">
              <div class="channel-preview-head">
                <div class="channel-preview-avatar" :class="accountPlatformClass(account)">
                  <PlatformIcon :platform="accountPlatformClass(account)" :size="20" />
                </div>
                <div>
                  <strong>{{ account.display_name }}</strong>
                  <span>{{ accountDescriptor(account) }} · {{ account.channel_name || account.provider_name }} · {{ previewTime() }}</span>
                </div>
              </div>

              <p class="channel-preview-text">{{ form.caption_text || "Your caption preview will appear here." }}</p>

              <div v-if="selectedAssets.length" class="channel-preview-media" :class="`count-${Math.min(selectedAssets.length, 3)}`">
                <template v-for="asset in selectedAssets.slice(0, 3)" :key="asset.id">
                  <video v-if="isVideoAsset(asset)" :src="asset.file_url" muted playsinline preload="metadata"></video>
                  <img v-else :src="asset.file_url" :alt="asset.title || asset.file_name" />
                </template>
              </div>

              <div class="channel-preview-actions">
                <span>{{ accountPlatformClass(account) === 'instagram' ? "Feed" : "Post" }}</span>
                <span>{{ accountPlatformClass(account) === 'instagram' ? selectedInstagramModeLabel : "Single post" }}</span>
                <span>{{ selectedAssets.length }} image{{ selectedAssets.length === 1 ? "" : "s" }}</span>
              </div>
            </div>
          </div>

        </aside>
      </div>
    </div>

    <div v-if="pendingDeletePost" class="confirm-overlay" @click.self="cancelDeletePost">
      <section class="confirm-modal">
        <p class="confirm-kicker">Confirm delete</p>
        <h3>Delete this post?</h3>
        <p class="confirm-copy">
          <strong>{{ postTitle(pendingDeletePost) }}</strong>
          will be removed permanently from this workspace.
        </p>
        <div class="confirm-actions">
          <button class="btn secondary" type="button" @click="cancelDeletePost">Cancel</button>
          <button class="icon-btn danger confirm-delete-btn" type="button" :disabled="deletingId === pendingDeletePost.id" @click="confirmDeletePost">
            {{ deletingId === pendingDeletePost.id ? "Deleting..." : "Delete post" }}
          </button>
        </div>
      </section>
    </div>

    <div v-if="pendingDuplicatePost" class="confirm-overlay" @click.self="cancelDuplicatePost">
      <section class="confirm-modal">
        <p class="confirm-kicker">Confirm duplicate</p>
        <h3>Create a copy of this post?</h3>
        <p class="confirm-copy">
          A new draft will be created from
          <strong>{{ postTitle(pendingDuplicatePost) }}</strong>.
        </p>
        <div class="confirm-actions">
          <button class="btn secondary" type="button" @click="cancelDuplicatePost">Cancel</button>
          <button class="mini-btn confirm-duplicate-btn" type="button" :disabled="duplicatingId === pendingDuplicatePost.id" @click="confirmDuplicatePost">
            {{ duplicatingId === pendingDuplicatePost.id ? "Duplicating..." : "Duplicate post" }}
          </button>
        </div>
      </section>
    </div>
  </div>

  <Teleport to="body">
    <div v-if="groupModal.open" class="channel-modal-overlay" @click.self="groupModal.open = false">
      <div class="channel-modal">
        <div class="channel-modal-header">
          <span>Select {{ platformName(groupModal.platform) }}</span>
          <button class="channel-modal-close" @click="groupModal.open = false">×</button>
        </div>
        <input v-model="groupModal.search" placeholder="Search..." class="channel-modal-search" />
        <div class="channel-modal-list">
          <label v-for="acc in modalAccounts" :key="acc.id" class="channel-modal-item">
            <input type="checkbox" :value="acc.id" v-model="groupModalSelected" />
            <span>{{ acc.display_name }}</span>
          </label>
        </div>
        <div class="channel-modal-footer">
          <button class="btn secondary" @click="groupModal.open = false">Cancel</button>
          <button class="btn" @click="confirmGroupModal">OK</button>
        </div>
      </div>
    </div>
  </Teleport>

  <Teleport to="body">
    <div class="toast-stack">
      <TransitionGroup name="toast">
        <div v-for="toast in toasts" :key="toast.id" class="toast" :class="toast.kind">
          <span class="toast-icon">{{ toast.kind === "success" ? "✓" : "×" }}</span>
          {{ toast.message }}
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.posts-workspace {
  padding: 24px;
  background: var(--page-gradient);
  min-height: 100%;
}

.group-label,
.editor-kicker,
.preview-kicker,
.library-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--muted);
}

.posts-shell {
  max-width: 1120px;
  margin: 0 auto;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--panel);
  overflow: hidden;
  box-shadow: var(--shadow-panel);
}

.posts-header,
.posts-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 22px;
  background: var(--panel);
}

.posts-header {
  border-bottom: 1px solid var(--line);
}

.posts-toolbar {
  border-bottom: 1px solid var(--line);
}

.posts-header-main,
.posts-header-actions,
.toolbar-filters,
.timeline-card-body,
.post-account-line,
.timeline-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.posts-header-main {
  min-width: 0;
}

.posts-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  border: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 800;
  color: var(--muted);
  background: var(--surface);
}

.posts-title {
  margin: 0;
  font-size: 28px;
  line-height: 1.1;
  letter-spacing: -0.03em;
  color: var(--ink);
}

.posts-subtitle {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.5;
}

.header-btn,
.toolbar-chip,
.icon-btn {
  border: 1px solid var(--line);
  background: var(--control-bg);
  color: var(--ink);
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-soft);
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease, box-shadow 0.14s ease, transform 0.14s ease;
}

.header-btn:hover,
.toolbar-chip:hover,
.icon-btn:hover {
  transform: translateY(-1px);
  border-color: var(--brand-outline);
  background: var(--control-bg-hover);
  box-shadow: var(--shadow-panel);
}

.posts-feed {
  padding: 18px 22px 26px;
  background: var(--panel);
}

.composer-overlay {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(16, 30, 25, 0.48);
  backdrop-filter: blur(8px);
}

.composer-modal {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  grid-template-rows: min(920px, calc(100vh - 48px));
  gap: 18px;
  width: min(1400px, 100%);
}

.composer-modal.has-channels {
  grid-template-columns: 260px minmax(0, 1fr) 420px;
  width: min(1600px, 100%);
}

.composer-editor {
  min-height: 0;
  overflow: auto;
}

.composer-preview {
  min-height: 0;
  overflow: hidden;
}

.composer-channels {
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.posts-tabs {
  display: flex;
  align-items: center;
  gap: 20px;
  min-width: 0;
  overflow-x: auto;
}

.tab-btn {
  border: 1px solid transparent;
  background: transparent;
  padding: 8px 12px;
  font-weight: 600;
  color: var(--muted);
  cursor: pointer;
  white-space: nowrap;
  border-radius: 999px;
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease;
}

.tab-btn span {
  margin-left: 4px;
  color: var(--muted);
}

.tab-btn.active {
  color: var(--action-ink);
  border-color: var(--action-border);
  background: linear-gradient(180deg, var(--action-fill-start) 0%, var(--action-fill-end) 100%);
}

.tab-btn:hover:not(.active) {
  color: var(--ink);
  background: var(--surface-muted);
  border-color: var(--line-soft);
}

.post-group {
  display: grid;
  gap: 14px;
  margin-bottom: 24px;
}

.group-label {
  padding-left: 88px;
}

.timeline-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.timeline-time {
  padding-top: 18px;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  text-align: right;
}

.timeline-card {
  display: grid;
  gap: 12px;
  padding: 0;
  border-radius: 14px;
  border: 1px solid var(--line-soft);
  background: var(--surface);
  overflow: hidden;
}

.timeline-card.active {
  border-color: rgba(127, 162, 147, 0.35);
}

.timeline-card-body {
  align-items: stretch;
  justify-content: space-between;
  padding: 16px;
  cursor: pointer;
}

.timeline-card-main {
  display: grid;
  gap: 14px;
  min-width: 0;
  flex: 1;
}

.post-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: #1877f2;
  border: 1px solid rgba(19, 38, 27, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 800;
  color: #ffffff;
  flex-shrink: 0;
}

.post-avatar.instagram {
  background: linear-gradient(135deg, #f58529, #dd2a7b 58%, #515bd4);
}

.post-avatar.linkedin {
  background: #0a66c2;
}

.post-avatar.tiktok {
  background: #111111;
}

.post-avatar.youtube {
  background: #ff0000;
}

.post-avatar.pinterest {
  background: #e60023;
}

.post-account-copy {
  display: grid;
  gap: 2px;
}

.post-account-copy strong,
.preview-meta-card strong,
.channel-preview-head strong {
  display: block;
}

.post-account-copy span,
.post-card-footer,
.channel-preview-head span,
.preview-meta-card span {
  color: var(--muted);
  font-size: 12px;
}

.post-body-copy {
  display: grid;
  gap: 8px;
}

.post-row-title {
  color: var(--ink);
  font-size: 14px;
  line-height: 1.5;
}

.post-excerpt {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.65;
}

.post-card-footer {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status-pill[data-tone="success"] {
  background: rgba(127, 162, 147, 0.18);
  color: var(--brand-strong);
}

.status-pill[data-tone="amber"] {
  background: rgba(230, 126, 34, 0.16);
  color: #ad5c16;
}

.status-pill[data-tone="brand"] {
  background: rgba(95, 127, 114, 0.16);
  color: #4d665c;
}

.status-pill[data-tone="danger"] {
  background: rgba(192, 57, 43, 0.14);
  color: #a02e22;
}

.status-pill[data-tone="muted"] {
  background: rgba(107, 118, 111, 0.16);
  color: #58625c;
}

.mini-btn,
.pill-btn,
.media-icon-btn,
.icon-btn {
  border: 1px solid var(--line);
  background: var(--control-bg);
  color: var(--ink);
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  padding: 8px 10px;
  cursor: pointer;
  box-shadow: var(--shadow-soft);
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease, box-shadow 0.14s ease, transform 0.14s ease;
}

.mini-btn {
  min-width: 120px;
}

.timeline-actions .mini-btn {
  padding-inline: 14px;
}

.mini-btn.danger,
.media-icon-btn.danger,
.icon-btn.danger {
  border-color: rgba(138, 39, 28, 0.28);
  background: linear-gradient(180deg, #fff4f1 0%, #f7ded8 100%);
  color: #a02e22;
}

.mini-btn:hover:not(:disabled),
.pill-btn:hover:not(:disabled),
.media-icon-btn:hover:not(:disabled),
.icon-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: var(--brand-outline);
  box-shadow: var(--shadow-panel);
}

.mini-btn.danger:hover:not(:disabled),
.media-icon-btn.danger:hover:not(:disabled),
.icon-btn.danger:hover:not(:disabled) {
  border-color: rgba(138, 39, 28, 0.4);
  background: linear-gradient(180deg, #ffe9e3 0%, #f1cfc6 100%);
}

.mini-btn:disabled,
.media-icon-btn:disabled,
.icon-btn:disabled {
  opacity: 1;
  background: #ece6db;
  border-color: #d6ccbd;
  color: #90887b;
  cursor: not-allowed;
  box-shadow: none;
}

.timeline-media {
  width: 190px;
  flex-shrink: 0;
}

.timeline-media img {
  width: 100%;
  height: 140px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid rgba(19, 38, 27, 0.08);
}

.timeline-media video {
  width: 100%;
  height: 140px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid rgba(19, 38, 27, 0.08);
  background: #111;
}

.timeline-actions,
.media-toolbar,
.editor-footer,
.preview-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 16px 16px;
}

.timeline-actions {
  align-items: flex-end;
  padding-top: 4px;
  border-top: 1px solid rgba(19, 38, 27, 0.06);
}

.timeline-actions-primary,
.timeline-actions-secondary {
  display: grid;
  gap: 8px;
}

.timeline-actions-primary {
  justify-items: start;
}

.timeline-actions-secondary {
  justify-items: end;
}

.action-label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.action-cluster {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px;
  border-radius: 14px;
  border: 1px solid var(--line-soft);
  background: var(--surface-muted);
}

.action-cluster .icon-btn {
  border-color: transparent;
  background: transparent;
}

.action-cluster .icon-btn:hover:not(:disabled) {
  background: var(--surface);
  border-color: var(--line);
}

.posts-empty {
  margin: 0;
  display: grid;
  gap: 10px;
  justify-items: center;
  text-align: center;
  color: var(--muted);
  padding: 60px 24px;
  background: var(--panel);
}

.editor-panel {
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  border-radius: 28px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-panel);
}

.editor-panel.drag-active {
  outline: 2px dashed rgba(127, 162, 147, 0.34);
  outline-offset: -10px;
}

.editor-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.editor-header h2 {
  margin: 0;
  font-size: 28px;
  letter-spacing: -0.03em;
}

.editor-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 18px;
  font-size: 13px;
  line-height: 1.5;
}

.editor-alert.warning {
  background: rgba(230, 126, 34, 0.1);
  color: #8f4d14;
}

.editor-alert.danger {
  background: rgba(192, 57, 43, 0.1);
  color: #a02e22;
}

.editor-link {
  font-weight: 800;
}

.editor-block {
  display: grid;
  gap: 4px;
}

.editor-block.grow {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
}

.editor-block.grow .caption-input {
  flex: 1;
  min-height: 120px;
}

.editor-label {
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--muted);
}

.channel-rail {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border-radius: 20px;
  border: 1px solid var(--line-soft);
  background: var(--panel);
}

.channel-rail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.channel-rail-head strong {
  color: var(--ink);
  font-size: 14px;
}

.channel-rail-count {
  align-self: center;
  padding: 5px 8px;
  border-radius: 999px;
  background: rgba(127, 162, 147, 0.12);
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}

.channel-search-input {
  width: 100%;
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 9px 10px;
  background: var(--input-bg);
  color: var(--ink);
  font-size: 13px;
  outline: none;
}

.channel-search-input:focus {
  border-color: rgba(127, 162, 147, 0.56);
  box-shadow: 0 0 0 3px rgba(127, 162, 147, 0.12);
}

.channel-rail-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: grid;
  align-content: start;
  gap: 12px;
  padding-right: 2px;
  scrollbar-width: thin;
  scrollbar-color: rgba(19, 38, 27, 0.15) transparent;
}

.channel-pill-row {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.channel-pill-row.vertical {
  display: grid;
  gap: 8px;
  overflow: visible;
  padding-bottom: 0;
}

.channel-pill {
  position: relative;
  width: 54px;
  min-width: 54px;
  height: 54px;
  border: 1px solid var(--line-soft);
  background: var(--surface);
  border-radius: 16px;
  padding: 0;
  text-align: center;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.14s ease, background-color 0.14s ease, transform 0.14s ease;
}

.channel-pill-row.vertical .channel-pill {
  width: 100%;
  min-width: 0;
  height: 46px;
  justify-content: flex-start;
  gap: 8px;
  padding: 7px 34px 7px 7px;
  text-align: left;
  border-radius: 13px;
}

.channel-pill:hover {
  transform: translateY(-1px);
}

.channel-pill.selected {
  border-color: rgba(127, 162, 147, 0.48);
  background: rgba(127, 162, 147, 0.14);
}

.channel-pill.selected::after {
  content: "";
  position: absolute;
  right: 10px;
  top: 50%;
  width: 7px;
  height: 12px;
  border-right: 2px solid var(--brand-strong);
  border-bottom: 2px solid var(--brand-strong);
  transform: translateY(-58%) rotate(45deg);
}

.channel-pill-avatar {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: #1877f2;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 800;
}

.channel-pill-avatar.instagram {
  background: linear-gradient(135deg, #f58529, #dd2a7b 58%, #515bd4);
}

.channel-pill-avatar.linkedin {
  background: #0a66c2;
}

.channel-pill-avatar.tiktok {
  background: #111111;
}

.channel-pill-avatar.youtube {
  background: #ff0000;
}

.channel-pill-avatar.pinterest {
  background: #e60023;
}

.channel-pill-meta {
  display: none;
}

.channel-pill-row.vertical .channel-pill-meta {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.channel-pill-row.vertical .channel-pill-meta strong,
.channel-pill-row.vertical .channel-pill-meta small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.channel-pill-row.vertical .channel-pill-meta strong {
  color: var(--ink);
  font-size: 13px;
  line-height: 1.2;
}

.channel-pill-row.vertical .channel-pill-meta small {
  color: var(--muted);
  font-size: 11px;
}

.channel-pill-badge {
  position: absolute;
  right: -4px;
  bottom: -4px;
  padding: 3px 5px;
  border-radius: 999px;
  background: rgba(24, 119, 242, 0.1);
  color: #1877f2;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.08em;
  border: 1px solid rgba(255, 255, 255, 0.96);
}

.channel-pill-badge.instagram {
  background: rgba(221, 42, 123, 0.1);
  color: #c0347a;
}

.channel-pill-badge.linkedin {
  background: rgba(10, 102, 194, 0.1);
  color: #0a66c2;
}

.channel-pill-badge.tiktok {
  background: rgba(17, 17, 17, 0.08);
  color: #111111;
}

.channel-pill-badge.youtube {
  background: rgba(255, 0, 0, 0.1);
  color: #cc0000;
}

.channel-pill-badge.pinterest {
  background: rgba(230, 0, 35, 0.1);
  color: #b5001c;
}

.page-grid,
.post-mode-grid {
  display: grid;
  gap: 10px;
}

.page-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.page-card,
.strategy-card {
  border: 1px solid var(--line-soft);
  background: var(--surface);
  border-radius: 18px;
  padding: 14px;
  text-align: left;
  cursor: pointer;
  display: flex;
  gap: 12px;
  transition: border-color 0.14s ease, transform 0.14s ease;
}

.page-card.selected,
.strategy-card.selected {
  border-color: rgba(127, 162, 147, 0.24);
  background: rgba(127, 162, 147, 0.12);
}

.page-card-avatar {
  width: 38px;
  height: 38px;
  border-radius: 14px;
  background: linear-gradient(180deg, #6f8c80, #7fa293);
  color: #fff8ec;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-weight: 800;
}

.page-card strong,
.strategy-card strong {
  display: block;
  color: var(--ink);
}

.page-card span,
.strategy-card span,
.schedule-note,
.editor-footnote span {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}

.ig-type-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ig-type-toggle {
  display: flex;
  gap: 2px;
  padding: 3px;
  background: var(--surface-muted);
  border-radius: 10px;
}

.ig-type-opt {
  padding: 5px 11px;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease, box-shadow 0.12s ease;
  white-space: nowrap;
}

.ig-type-opt.active {
  background: var(--surface);
  color: var(--ink);
  box-shadow: 0 1px 3px rgba(19, 38, 27, 0.1);
  border-color: rgba(221, 42, 123, 0.14);
}

.ig-type-req {
  font-size: 12px;
  color: var(--muted);
}

.strategy-card {
  display: grid;
  gap: 8px;
}

.schedule-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.schedule-input {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 7px 10px;
  font-size: 12px;
  background: var(--input-bg);
  color: var(--ink);
}

.caption-input {
  width: 100%;
  min-height: 220px;
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 16px 18px;
  background: var(--input-bg);
  color: var(--ink);
  line-height: 1.7;
  resize: none;
  outline: none;
}

.media-strip {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: thin;
  scrollbar-color: rgba(19, 38, 27, 0.15) transparent;
}

.media-thumb {
  position: relative;
  flex-shrink: 0;
  width: 96px;
  height: 96px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--line-soft);
  background: var(--surface-muted);
}

.media-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.media-thumb video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  background: #111;
}

.media-thumb-actions {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: rgba(16, 30, 25, 0.48);
  opacity: 0;
  transition: opacity 0.14s ease;
}

.media-thumb:hover .media-thumb-actions {
  opacity: 1;
}

.media-thumb-actions .media-icon-btn {
  padding: 5px 7px;
  font-size: 11px;
  background: var(--panel);
  border-color: transparent;
  border-radius: 8px;
}

.media-add-btn {
  flex-shrink: 0;
  width: 96px;
  height: 96px;
  border-radius: 12px;
  border: 1.5px dashed rgba(19, 38, 27, 0.2);
  background: var(--surface);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--muted);
  transition: border-color 0.14s ease, background 0.14s ease;
  white-space: pre-line;
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
  padding: 8px;
}

.media-add-btn.empty {
  width: 160px;
}

.media-add-btn:hover,
.media-add-btn.drag-active {
  border-color: rgba(127, 162, 147, 0.6);
  background: rgba(127, 162, 147, 0.08);
}

.media-add-icon {
  font-size: 20px;
  line-height: 1;
  color: var(--muted);
}

.facebook-media img {
  width: 100%;
  object-fit: cover;
}

.editor-footer {
  align-items: flex-end;
}

.editor-footnote {
  display: grid;
  gap: 6px;
  max-width: 320px;
}

.editor-footnote strong {
  color: var(--ink);
  font-size: 13px;
}

.editor-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.next-action-group {
  position: relative;
}

.next-action-trigger {
  min-width: 150px;
  gap: 10px;
}

.next-action-trigger span {
  font-size: 11px;
  line-height: 1;
  opacity: 0.78;
}

.next-action-menu {
  position: absolute;
  right: 0;
  bottom: calc(100% + 10px);
  z-index: 20;
  width: 240px;
  display: grid;
  gap: 6px;
  padding: 8px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-strong);
}

.next-action-wrap {
  position: relative;
}

.next-action-wrap[data-tooltip]::after {
  content: attr(data-tooltip);
  position: absolute;
  right: calc(100% + 10px);
  top: 50%;
  width: max-content;
  max-width: 220px;
  transform: translateY(-50%);
  padding: 8px 10px;
  border-radius: 10px;
  background: #13261b;
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.35;
  box-shadow: 0 10px 24px rgba(19, 38, 27, 0.18);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s ease, transform 0.12s ease;
}

.next-action-wrap[data-tooltip]::before {
  content: "";
  position: absolute;
  right: calc(100% + 4px);
  top: 50%;
  border: 6px solid transparent;
  border-left-color: #13261b;
  transform: translateY(-50%);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s ease;
}

.next-action-wrap[data-tooltip]:hover::after,
.next-action-wrap[data-tooltip]:hover::before {
  opacity: 1;
}

.next-action-wrap[data-tooltip]:hover::after {
  transform: translateY(-50%) translateX(-2px);
}

.next-action-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid transparent;
  border-radius: 12px;
  padding: 10px;
  background: transparent;
  color: var(--ink);
  text-align: left;
  cursor: pointer;
}

.next-action-item:hover:not(:disabled) {
  background: rgba(127, 162, 147, 0.1);
  border-color: rgba(127, 162, 147, 0.18);
}

.next-action-icon {
  width: 28px;
  height: 28px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(127, 162, 147, 0.14);
  color: var(--brand-strong);
  font-size: 12px;
  font-weight: 900;
}

.next-action-copy {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.next-action-item strong {
  font-size: 13px;
}

.next-action-copy span {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.35;
}

.next-action-item:disabled {
  opacity: 0.58;
  cursor: not-allowed;
  pointer-events: none;
}

.next-action-item:disabled .next-action-icon {
  background: rgba(19, 38, 27, 0.06);
  color: rgba(70, 82, 76, 0.62);
}

.preview-panel {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border-radius: 28px;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--ink);
  box-shadow: var(--shadow-panel);
  height: 100%;
  overflow: hidden;
}

.preview-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 16px;
  scrollbar-width: thin;
  scrollbar-color: rgba(19, 38, 27, 0.15) transparent;
}

.preview-summary {
  display: grid;
  gap: 8px;
}

.preview-summary strong {
  font-size: 20px;
}

.preview-summary small {
  color: var(--muted);
}

.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(16, 30, 25, 0.3);
  backdrop-filter: blur(6px);
}

.confirm-modal {
  width: min(460px, 100%);
  display: grid;
  gap: 14px;
  padding: 22px;
  border-radius: 24px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-strong);
}

.confirm-kicker {
  margin: 0;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}

.confirm-modal h3 {
  margin: 0;
  font-size: 24px;
  letter-spacing: -0.03em;
  color: var(--ink);
}

.confirm-copy {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.6;
}

.confirm-copy strong {
  color: var(--ink);
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.confirm-delete-btn {
  border-color: rgba(160, 46, 34, 0.14);
  background: rgba(160, 46, 34, 0.08);
}

.confirm-delete-btn:hover:not(:disabled) {
  background: rgba(160, 46, 34, 0.12);
  border-color: rgba(160, 46, 34, 0.18);
}

.confirm-duplicate-btn {
  min-width: 138px;
}

.channel-preview-card,
.preview-meta-card {
  border-radius: 22px;
  background: var(--surface-muted);
  color: var(--ink);
  border: 1px solid var(--line-soft);
}

.channel-preview-card {
  padding: 18px;
}

.channel-preview-head {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
}

.channel-preview-avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #1877f2;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  flex-shrink: 0;
}

.channel-preview-avatar.instagram {
  background: linear-gradient(135deg, #f58529, #dd2a7b 58%, #515bd4);
}

.channel-preview-avatar.linkedin {
  background: #0a66c2;
}

.channel-preview-avatar.tiktok {
  background: #111111;
}

.channel-preview-avatar.youtube {
  background: #ff0000;
}

.channel-preview-avatar.pinterest {
  background: #e60023;
}

.channel-preview-text {
  margin: 0 0 14px;
  white-space: pre-wrap;
  line-height: 1.65;
  font-size: 14px;
}

.channel-preview-media {
  display: grid;
  gap: 6px;
  margin-bottom: 14px;
}

.channel-preview-media.count-1 {
  grid-template-columns: 1fr;
}

.channel-preview-media.count-2 {
  grid-template-columns: 1fr 1fr;
}

.channel-preview-media.count-3 {
  grid-template-columns: 1.2fr 0.8fr;
}

.channel-preview-media img {
  border-radius: 14px;
  min-height: 140px;
  max-height: 220px;
}

.channel-preview-media video {
  width: 100%;
  min-height: 140px;
  max-height: 220px;
  object-fit: cover;
  border-radius: 14px;
  background: #111;
}

.channel-preview-actions {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid rgba(19, 38, 27, 0.08);
  padding-top: 12px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

.preview-meta-card {
  display: grid;
  gap: 14px;
  padding: 18px;
}

.toast-stack {
  position: fixed;
  right: 28px;
  bottom: 28px;
  display: grid;
  gap: 10px;
  z-index: 9999;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 220px;
  max-width: 360px;
  padding: 12px 16px;
  border-radius: 14px;
  color: #13261b;
  border: 1px solid rgba(19, 38, 27, 0.12);
  background: linear-gradient(180deg, rgba(224, 237, 231, 0.96), rgba(216, 230, 223, 0.98));
  box-shadow: 0 12px 28px rgba(19, 38, 27, 0.12);
}

.toast.success {
  background: linear-gradient(180deg, rgba(224, 237, 231, 0.96), rgba(216, 230, 223, 0.98));
}

.toast.error {
  background: linear-gradient(180deg, rgba(224, 237, 231, 0.96), rgba(216, 230, 223, 0.98));
  border-color: rgba(160, 46, 34, 0.18);
}

.toast-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(19, 38, 27, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@media (max-width: 1280px) {
  .composer-modal,
  .composer-modal.has-channels {
    grid-template-columns: minmax(0, 1fr);
  }

  .composer-channels {
    max-height: 280px;
  }
}

@media (max-width: 960px) {
  .posts-workspace {
    padding: 20px;
  }

  .posts-header,
  .posts-toolbar,
  .editor-footer,
  .schedule-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .timeline-row {
    grid-template-columns: 1fr;
  }

  .group-label {
    padding-left: 0;
  }

  .timeline-time {
    padding-top: 0;
    text-align: left;
  }

  .timeline-card-body {
    flex-direction: column;
  }

  .timeline-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .timeline-actions-secondary {
    justify-items: stretch;
  }

  .action-cluster {
    flex-wrap: wrap;
  }

  .timeline-media {
    width: 100%;
  }

  .channel-rail-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .page-grid,
  .post-mode-grid {
    grid-template-columns: 1fr;
  }

  .composer-overlay {
    padding: 12px;
  }

  .editor-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .next-action-group,
  .next-action-trigger,
  .next-action-menu {
    width: 100%;
  }

  .next-action-menu {
    right: auto;
    left: 0;
  }

  .confirm-overlay {
    padding: 16px;
  }

  .confirm-actions {
    flex-direction: column-reverse;
    align-items: stretch;
  }
}

.channel-group {
  display: grid;
  gap: 8px;
}

.channel-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2px;
}

.channel-group-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
}

.channel-group-count {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  opacity: 0.7;
}

.channel-group-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.channel-group-action,
.channel-show-more {
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink);
  border-radius: 9px;
  padding: 6px 9px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.12s ease, border-color 0.12s ease;
}

.channel-group-action:hover,
.channel-show-more:hover {
  border-color: var(--brand-outline);
  background: var(--surface-muted);
}

.channel-show-more {
  width: 100%;
  margin-top: 2px;
}

.channel-empty-search {
  padding: 14px;
  border-radius: 14px;
  background: rgba(19, 38, 27, 0.04);
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

.channel-group-compact {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid var(--line-soft);
  background: var(--surface-muted);
}

.channel-group-select-all {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ink);
  cursor: pointer;
}

.channel-group-select-btn {
  margin-left: auto;
  padding: 6px 14px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--control-bg);
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}

.channel-group-select-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.channel-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(16, 30, 25, 0.45);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 80;
}

.channel-modal {
  width: min(480px, 100%);
  max-height: min(70vh, 560px);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  box-shadow: var(--shadow-strong);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.channel-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(19, 38, 27, 0.08);
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
}

.channel-modal-close {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid rgba(19, 38, 27, 0.16);
  background: transparent;
  color: var(--muted);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.channel-modal-search {
  margin: 12px 20px 0;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--input-bg);
  font-size: 13px;
  color: var(--ink);
  width: calc(100% - 40px);
}

.channel-modal-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 20px;
  display: grid;
  gap: 4px;
}

.channel-modal-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  font-size: 13px;
  color: var(--ink);
  cursor: pointer;
}

.channel-modal-item:hover {
  background: rgba(19, 38, 27, 0.04);
}

.channel-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid rgba(19, 38, 27, 0.08);
}
</style>
