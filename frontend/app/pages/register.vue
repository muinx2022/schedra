<script setup lang="ts">
const form = reactive({
  full_name: "",
  workspace_name: "",
  email: "",
  password: "",
})
const error = ref("")
const loading = ref(false)
const showPassword = ref(false)

async function submit() {
  if (loading.value) return
  error.value = ""
  loading.value = true
  try {
    await apiFetch("/auth/register/", { method: "POST", body: form })
    await navigateTo("/app")
  } catch (err: any) {
    error.value = extractApiError(err, "Registration failed.")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-88px)] bg-[radial-gradient(circle_at_top_left,rgba(98,108,122,0.12),transparent_28%),linear-gradient(180deg,#f8f9fb_0%,#edf1f4_100%)] px-5 py-6 md:px-8 md:py-8">
    <div class="mx-auto grid max-w-7xl grid-cols-1 gap-6 lg:grid-cols-[1.08fr_0.92fr] lg:items-stretch">
      <section class="overflow-hidden rounded-[32px] border border-[#222831] bg-[#111418] p-7 text-white shadow-[0_30px_80px_rgba(15,18,24,0.3)] md:p-9">
        <div class="flex h-full flex-col justify-between gap-8">
          <div>
            <div class="text-[11px] uppercase tracking-[0.26em] text-white/42">Workspace onboarding</div>
            <h1 class="mt-5 max-w-lg text-4xl leading-tight font-semibold tracking-tight md:text-[44px]">
              Launch a new publishing workspace without admin friction.
            </h1>
            <p class="mt-4 max-w-xl text-sm leading-7 text-white/68">
              Create the owner account, name the workspace, and get straight into scheduling, inbox review, and provider setup.
            </p>
          </div>

          <div class="grid gap-3 sm:grid-cols-3">
            <article class="rounded-2xl border border-white/10 bg-white/6 p-4">
              <div class="text-[11px] uppercase tracking-[0.16em] text-white/42">Setup</div>
              <div class="mt-3 text-2xl font-semibold">1 flow</div>
              <p class="mt-2 text-sm text-white/58">Owner account and workspace are provisioned together.</p>
            </article>
            <article class="rounded-2xl border border-white/10 bg-white/6 p-4">
              <div class="text-[11px] uppercase tracking-[0.16em] text-white/42">Mail</div>
              <div class="mt-3 text-2xl font-semibold">Editable</div>
              <p class="mt-2 text-sm text-white/58">Welcome emails can be tuned later from Django staff.</p>
            </article>
            <article class="rounded-2xl border border-white/10 bg-white/6 p-4">
              <div class="text-[11px] uppercase tracking-[0.16em] text-white/42">Access</div>
              <div class="mt-3 text-2xl font-semibold">Instant</div>
              <p class="mt-2 text-sm text-white/58">The owner lands in the app right after signup succeeds.</p>
            </article>
          </div>
        </div>
      </section>

      <section class="flex rounded-[32px] border border-[var(--line)] bg-[var(--panel)] p-4 shadow-[0_24px_70px_rgba(19,38,27,0.08)] md:p-6">
        <div class="flex w-full flex-col rounded-[28px] bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(247,250,253,0.98))] p-5 md:p-7">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-[#6d7783]">Register</p>
              <h2 class="mt-3 text-3xl font-semibold tracking-tight text-[var(--ink)]">Create workspace</h2>
              <p class="mt-3 max-w-md text-sm leading-6 text-[var(--muted)]">
                This account becomes the first workspace owner and can access Django staff tooling later.
              </p>
            </div>
            <NuxtLink
              to="/login"
              class="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--line)] bg-white text-[var(--muted)] transition hover:border-[#8a95a3] hover:text-[var(--ink)]"
              title="Back to login"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </NuxtLink>
          </div>

          <form class="mt-6 space-y-4" @submit.prevent="submit">
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-[var(--ink)]">Full name</span>
              <input
                v-model="form.full_name"
                class="w-full rounded-2xl border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[#8a95a3]"
                autocomplete="name"
                placeholder="Nguyen Xuan Mui"
              />
            </label>

            <label class="block">
              <span class="mb-2 block text-sm font-medium text-[var(--ink)]">Workspace name</span>
              <input
                v-model="form.workspace_name"
                class="w-full rounded-2xl border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[#8a95a3]"
                autocomplete="organization"
                placeholder="Schedra"
              />
            </label>

            <label class="block">
              <span class="mb-2 block text-sm font-medium text-[var(--ink)]">Email</span>
              <input
                v-model="form.email"
                type="email"
                class="w-full rounded-2xl border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[#8a95a3]"
                autocomplete="email"
                placeholder="you@company.com"
              />
            </label>

            <label class="block">
              <span class="mb-2 block text-sm font-medium text-[var(--ink)]">Password</span>
              <div class="flex items-center gap-3 rounded-2xl border border-[var(--line)] bg-white px-4 py-3 transition focus-within:border-[#8a95a3]">
                <input
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  class="w-full border-0 bg-transparent p-0 text-sm text-[var(--ink)] outline-none"
                  autocomplete="new-password"
                  placeholder="At least 8 characters"
                />
                <button
                  type="button"
                  class="inline-flex h-9 w-9 items-center justify-center rounded-xl text-[var(--muted)] transition hover:bg-[var(--surface-muted)] hover:text-[var(--ink)]"
                  @click="showPassword = !showPassword"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path v-if="showPassword" d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z" />
                    <circle v-if="showPassword" cx="12" cy="12" r="3" />
                    <template v-else>
                      <path d="M3 3l18 18" />
                      <path d="M10.6 10.6A3 3 0 0 0 13.4 13.4" />
                      <path d="M9.9 5.1A10.9 10.9 0 0 1 12 5c6.5 0 10 7 10 7a19.6 19.6 0 0 1-4.2 4.8" />
                      <path d="M6.7 6.7C4.1 8.3 2 12 2 12a19.8 19.8 0 0 0 7.7 5.8" />
                    </template>
                  </svg>
                </button>
              </div>
            </label>

            <div class="rounded-2xl border border-[var(--line)] bg-[var(--bg)] px-4 py-4 text-sm text-[var(--muted)]">
              A welcome email is sent after signup if mail delivery is enabled in Django staff settings.
            </div>

            <p v-if="error" class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {{ error }}
            </p>

            <button
              type="submit"
              class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[#1d232b] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#2a313b] active:bg-[#151a20] disabled:cursor-not-allowed disabled:opacity-45"
              :disabled="loading || !form.full_name.trim() || !form.workspace_name.trim() || !form.email.trim() || !form.password.trim()"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M12 5v14" />
                <path d="M5 12h14" />
              </svg>
              {{ loading ? "Creating workspace..." : "Create workspace" }}
            </button>
          </form>

          <div class="mt-5 border-t border-[var(--line)] pt-5 text-sm text-[var(--muted)]">
            Already have an account?
            <NuxtLink to="/login" class="font-semibold text-[#49515d] hover:text-[var(--ink)]">Sign in</NuxtLink>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
