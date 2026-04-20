<script setup lang="ts">
definePageMeta({ middleware: "auth" })

type Idea = {
  id: number
  title: string
  note: string
  column: string
  tags: string[]
  image_urls: string[]
}

const columns = ["unassigned", "todo", "in_progress", "done"] as const
const labels: Record<(typeof columns)[number], string> = {
  unassigned: "Unassigned",
  todo: "Todo",
  in_progress: "In Progress",
  done: "Done",
}

const showModal = ref(false)
const saving = ref(false)
const deletingId = ref<number | null>(null)
const submitError = ref("")
const loading = ref(false)
const modalMode = ref<"create" | "edit">("create")
const editingIdeaId = ref<number | null>(null)
const openMenuId = ref<number | null>(null)
const moveExpandedId = ref<number | null>(null)
const modalForm = reactive({ title: "", note: "", tags: "", column: "unassigned" })
const ideas = ref<Idea[]>([])

const convertingId = ref<number | null>(null)
const draggingIdea = ref<Idea | null>(null)
const dragOverCol = ref<string | null>(null)

async function loadIdeas() {
  loading.value = true
  submitError.value = ""
  try {
    ideas.value = await apiFetch<Idea[]>("/ideas/")
  } catch (error: any) {
    submitError.value = extractApiError(error, "Could not load ideas.")
  } finally {
    loading.value = false
  }
}

const byColumn = computed(() => {
  const map: Record<string, Idea[]> = Object.fromEntries(columns.map((c) => [c, []]))
  for (const idea of ideas.value) {
    const col = idea.column in map ? idea.column : "unassigned"
    map[col].push(idea)
  }
  return map
})

onMounted(loadIdeas)

function resetForm() {
  modalForm.title = ""
  modalForm.note = ""
  modalForm.tags = ""
  modalForm.column = "unassigned"
  editingIdeaId.value = null
  submitError.value = ""
}

function openCreateModal(column = "unassigned") {
  resetForm()
  modalMode.value = "create"
  modalForm.column = columns.includes(column as (typeof columns)[number]) ? column : "unassigned"
  showModal.value = true
}

function openEditModal(idea: Idea) {
  resetForm()
  modalMode.value = "edit"
  editingIdeaId.value = idea.id
  modalForm.title = idea.title
  modalForm.note = idea.note || ""
  modalForm.tags = (idea.tags || []).join(", ")
  modalForm.column = columns.includes(idea.column as (typeof columns)[number]) ? idea.column : "unassigned"
  openMenuId.value = null
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  resetForm()
}

function toggleMenu(ideaId: number) {
  if (openMenuId.value === ideaId) {
    openMenuId.value = null
    moveExpandedId.value = null
  } else {
    openMenuId.value = ideaId
    moveExpandedId.value = null
  }
}

function findIdeaById(ideaId: number) {
  return ideas.value.find((idea) => idea.id === ideaId) || null
}

async function saveIdea() {
  if (!modalForm.title.trim() || saving.value) return
  saving.value = true
  submitError.value = ""

  const body = {
    title: modalForm.title.trim(),
    note: modalForm.note.trim(),
    column: modalForm.column,
    tags: modalForm.tags ? modalForm.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
    image_urls: [],
  }

  try {
    if (modalMode.value === "edit" && editingIdeaId.value) {
      await apiFetch(`/ideas/${editingIdeaId.value}/`, { method: "PATCH", body })
    } else {
      await apiFetch("/ideas/", { method: "POST", body })
    }
    closeModal()
    await loadIdeas()
  } catch (error: any) {
    submitError.value = extractApiError(error, "Could not save idea.")
  } finally {
    saving.value = false
  }
}

async function deleteIdea(idea: Idea) {
  if (deletingId.value === idea.id) return
  if (!confirm(`Delete "${idea.title}"?`)) return

  deletingId.value = idea.id
  openMenuId.value = null
  try {
    await apiFetch(`/ideas/${idea.id}/`, { method: "DELETE" })
    await loadIdeas()
  } catch (error: any) {
    submitError.value = extractApiError(error, "Could not delete idea.")
  } finally {
    deletingId.value = null
  }
}

async function convertToPost(idea: Idea) {
  if (convertingId.value === idea.id) return
  convertingId.value = idea.id
  openMenuId.value = null
  try {
    const post = await apiFetch<{ id: string }>(`/posts/from-idea/${idea.id}/`, { method: "POST" })
    await navigateTo(`/app/posts?tab=drafts&post=${post.id}`)
  } catch (error: any) {
    submitError.value = extractApiError(error, "Could not convert idea to post.")
  } finally {
    convertingId.value = null
  }
}

async function moveIdea(idea: Idea, column: string) {
  if (idea.column === column) return
  const previousColumn = idea.column
  idea.column = column
  openMenuId.value = null
  try {
    await apiFetch(`/ideas/${idea.id}/`, { method: "PATCH", body: { column } })
    await loadIdeas()
  } catch (error: any) {
    idea.column = previousColumn
    submitError.value = extractApiError(error, "Could not move idea.")
  }
}

function onDragStart(e: DragEvent, idea: Idea) {
  draggingIdea.value = idea
  openMenuId.value = null
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = "move"
    e.dataTransfer.setData("text/plain", String(idea.id))
  }
}

function onDragEnd() {
  draggingIdea.value = null
  dragOverCol.value = null
}

function onDragOver(e: DragEvent, col: string) {
  e.preventDefault()
  dragOverCol.value = col
}

async function onDrop(e: DragEvent, col: string) {
  e.preventDefault()
  dragOverCol.value = null
  const draggedId = Number(e.dataTransfer?.getData("text/plain") || "0")
  const idea = draggingIdea.value || (draggedId ? findIdeaById(draggedId) : null)
  draggingIdea.value = null
  if (!idea) return
  await moveIdea(idea, col)
}
</script>

<template>
  <div class="px-5 py-5 md:px-8 md:py-8" @click="openMenuId = null; moveExpandedId = null">
    <div class="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div class="space-y-1">
        <p class="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--brand)]">Content pipeline</p>
        <h1 class="m-0 text-3xl font-semibold tracking-tight text-[var(--ink)] md:text-4xl">Ideas</h1>
        <p class="max-w-2xl text-sm leading-6 text-[var(--muted)]">
          Capture ideas, move them across stages, and manage them inline.
        </p>
      </div>
      <button
        type="button"
        class="action-btn inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-semibold shadow-sm transition"
        @click.stop="openCreateModal()"
      >
        New idea
      </button>
    </div>

    <p
      v-if="submitError"
      class="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
    >
      {{ submitError }}
    </p>

    <div
      v-if="loading"
      class="mb-4 rounded-2xl border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-sm text-[var(--muted)]"
    >
      Loading ideas...
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <div
        v-for="col in columns"
        :key="col"
        class="flex min-h-[24rem] flex-col rounded-[24px] border border-[var(--line)] bg-[var(--surface-muted)] p-4 shadow-[0_18px_48px_rgba(19,38,27,0.06)] backdrop-blur-sm transition"
        :class="dragOverCol === col ? 'border-[var(--brand)] bg-[rgba(13,122,95,0.07)]' : ''"
        @dragover="onDragOver($event, col)"
        @dragleave="dragOverCol = null"
        @drop="onDrop($event, col)"
      >
        <div class="mb-4 flex items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <strong class="text-sm font-semibold text-[var(--ink)]">{{ labels[col] }}</strong>
            <span
              class="inline-flex min-w-7 items-center justify-center rounded-full border border-[var(--line-soft)] bg-[rgba(127,162,147,0.18)] px-2.5 py-1 text-xs font-semibold text-[var(--ink)]"
            >
              {{ byColumn[col].length }}
            </span>
          </div>
          <button
            type="button"
            class="inline-flex items-center justify-center rounded-full border border-[var(--line)] bg-[var(--panel)] px-3.5 py-1.5 text-xs font-semibold text-[var(--ink)] shadow-[var(--shadow-soft)] transition hover:-translate-y-[1px] hover:bg-[var(--surface)]"
            @click.stop="openCreateModal(col)"
          >
            + New
          </button>
        </div>

        <article
          v-for="idea in byColumn[col]"
          :key="idea.id"
          class="group relative mb-3 flex cursor-grab flex-col gap-3 rounded-[18px] border border-[var(--line)] bg-[var(--panel)] p-4 shadow-[0_10px_30px_rgba(19,38,27,0.05)] transition active:cursor-grabbing"
          :class="draggingIdea?.id === idea.id ? 'opacity-40' : ''"
          draggable="true"
          @dragstart="onDragStart($event, idea)"
          @dragend="onDragEnd"
          @click.stop
        >
          <div class="flex items-start justify-between gap-3">
            <strong class="text-sm leading-5 font-semibold text-[var(--ink)]">{{ idea.title }}</strong>
            <div class="relative">
              <button
                type="button"
                class="inline-flex h-8 w-8 items-center justify-center rounded-full text-lg leading-none text-[var(--muted)] opacity-0 transition hover:bg-[var(--bg)] hover:text-[var(--ink)] group-hover:opacity-100"
                :class="openMenuId === idea.id ? 'opacity-100 bg-[var(--bg)] text-[var(--ink)]' : ''"
                @click.stop="toggleMenu(idea.id)"
              >
                ...
              </button>
              <div
                v-if="openMenuId === idea.id"
                class="absolute right-0 z-20 mt-2 w-44 rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-1 shadow-[var(--shadow-strong)]"
              >
                <button
                  type="button"
                  class="block w-full rounded-xl px-3 py-2 text-left text-sm text-[var(--ink)] transition hover:bg-[var(--bg)]"
                  @click.stop="openEditModal(idea)"
                >
                  Edit
                </button>
                <div class="my-1 border-t border-[var(--line)]"></div>
                <button
                  type="button"
                  class="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm text-[var(--ink)] transition hover:bg-[var(--bg)]"
                  @click.stop="moveExpandedId = moveExpandedId === idea.id ? null : idea.id"
                >
                  <span>Move to</span>
                  <span
                    class="text-[var(--muted)] transition-transform duration-150"
                    :class="moveExpandedId === idea.id ? 'rotate-90' : ''"
                  >›</span>
                </button>
                <div v-if="moveExpandedId === idea.id" class="mt-0.5 flex flex-col pl-2">
                  <button
                    v-for="targetCol in columns.filter((c) => c !== idea.column)"
                    :key="targetCol"
                    type="button"
                    class="block w-full rounded-xl px-3 py-1.5 text-left text-sm text-[var(--muted)] transition hover:bg-[var(--bg)] hover:text-[var(--ink)]"
                    @click.stop="moveIdea(idea, targetCol)"
                  >
                    {{ labels[targetCol] }}
                  </button>
                </div>
                <div class="my-1 border-t border-[var(--line)]"></div>
                <button
                  type="button"
                  class="block w-full rounded-xl px-3 py-2 text-left text-sm text-[var(--ink)] transition hover:bg-[var(--bg)]"
                  @click.stop="convertToPost(idea)"
                >
                  {{ convertingId === idea.id ? "Converting..." : "Convert to post" }}
                </button>
                <div class="my-1 border-t border-[var(--line)]"></div>
                <button
                  type="button"
                  class="block w-full rounded-xl px-3 py-2 text-left text-sm text-red-600 transition hover:bg-red-50"
                  @click.stop="deleteIdea(idea)"
                >
                  {{ deletingId === idea.id ? "Deleting..." : "Delete" }}
                </button>
              </div>
            </div>
          </div>

          <p v-if="idea.note" class="m-0 line-clamp-3 text-sm leading-6 text-[var(--muted)]">
            {{ idea.note }}
          </p>

          <div v-if="idea.tags?.length" class="flex flex-wrap gap-2">
            <span
              v-for="tag in idea.tags"
              :key="tag"
              class="rounded-full bg-[rgba(13,122,95,0.1)] px-2.5 py-1 text-xs font-medium text-[var(--brand-strong)]"
            >
              {{ tag }}
            </span>
          </div>
        </article>

        <p
          v-if="!byColumn[col].length"
          class="mt-6 rounded-2xl border border-dashed border-[var(--line)] px-4 py-10 text-center text-sm text-[var(--muted)]"
        >
          No ideas yet
        </p>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="showModal"
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/45 p-4"
        @click.self="closeModal"
      >
        <div
          class="w-full max-w-2xl overflow-hidden rounded-[28px] bg-[var(--panel)] shadow-[var(--shadow-strong)]"
          role="dialog"
          aria-modal="true"
          @click.stop
        >
          <div class="flex items-center gap-3 border-b border-[var(--line)] px-6 py-5">
            <span class="flex-1 text-base font-semibold text-[var(--ink)]">
              {{ modalMode === "edit" ? "Edit idea" : "Create idea" }}
            </span>
            <button
              type="button"
              class="rounded-full p-2 text-sm text-[var(--muted)] transition hover:bg-[var(--bg)]"
              aria-label="Close"
              @click="closeModal"
            >
              x
            </button>
          </div>

          <div class="flex flex-col gap-4 px-6 py-5">
            <label class="text-lg font-semibold text-[var(--ink)]">Title</label>
            <input
              v-model="modalForm.title"
              class="w-full rounded-2xl border border-[var(--line)] bg-[var(--input-bg)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition placeholder:text-[var(--muted)] focus:border-[var(--brand)]"
              placeholder="Ready, set, flow..."
              @keydown.enter.ctrl.prevent="saveIdea"
            />

            <label class="text-sm font-medium text-[var(--ink)]">Note</label>
            <textarea
              v-model="modalForm.note"
              class="min-h-36 w-full rounded-2xl border border-[var(--line)] bg-[var(--input-bg)] px-4 py-3 text-sm leading-6 text-[var(--ink)] outline-none transition placeholder:text-[var(--muted)] focus:border-[var(--brand)]"
              placeholder="Add a note..."
              rows="6"
            />

            <label class="text-sm font-medium text-[var(--ink)]">Tags</label>
            <input
              v-model="modalForm.tags"
              class="w-full rounded-2xl border border-[var(--line)] bg-[var(--input-bg)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition placeholder:text-[var(--muted)] focus:border-[var(--brand)]"
              placeholder="Tags, comma separated..."
            />

            <p
              v-if="submitError"
              class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {{ submitError }}
            </p>
          </div>

          <div class="flex items-center justify-between gap-3 border-t border-[var(--line)] px-6 py-4">
            <p class="text-sm text-[var(--muted)]">Ctrl + Enter to save</p>
            <div class="flex items-center gap-3">
              <button
                type="button"
                class="inline-flex items-center justify-center rounded-full border border-[var(--line)] px-5 py-2 text-sm font-semibold text-[var(--ink)] transition hover:bg-[var(--bg)]"
                @click="closeModal"
              >
                Cancel
              </button>
              <button
                type="button"
                class="action-btn inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-45"
                :disabled="!modalForm.title.trim() || saving"
                @click="saveIdea"
              >
                {{ saving ? "Saving..." : modalMode === "edit" ? "Save changes" : "Save idea" }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.action-btn {
  border: 1px solid var(--action-border);
  background: linear-gradient(180deg, var(--action-fill-start) 0%, var(--action-fill-end) 100%);
  color: var(--action-ink);
}

.action-btn:hover:not(:disabled) {
  background: linear-gradient(180deg, var(--action-fill-hover-start) 0%, var(--action-fill-hover-end) 100%);
}

.action-btn:active:not(:disabled) {
  background: linear-gradient(180deg, var(--action-fill-active-start) 0%, var(--action-fill-active-end) 100%);
}
</style>
