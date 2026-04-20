<script setup lang="ts">
const session = useSessionState()
const form = reactive({ email: "demo@example.com", password: "demo12345" })
const error = ref("")
const loading = ref(false)
const showPassword = ref(false)

const quickStats = [
  { label: "Queued this week", value: "148", note: "+12% vs last week" },
  { label: "Channels online", value: "08", note: "Meta and workspace sync" },
  { label: "Median review time", value: "14m", note: "From draft to approval" },
]

const timeline = [
  { time: "08:30", title: "Campaign brief approved", detail: "Spring launch assets moved into Ready." },
  { time: "11:10", title: "Queue filled for tomorrow", detail: "Six posts distributed across three channels." },
  { time: "15:40", title: "Comments sweep complete", detail: "Inbox triage closed with no pending escalations." },
]

async function submit() {
  if (loading.value) return
  error.value = ""
  loading.value = true
  try {
    const user = await apiFetch<any>("/auth/login/", { method: "POST", body: form })
    session.value = { authenticated: true, hydrated: true, user }
    await navigateTo("/app")
  } catch (err: any) {
    error.value = extractApiError(err, "Login failed.")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-88px)] bg-[radial-gradient(circle_at_top_left,rgba(98,108,122,0.12),transparent_28%),linear-gradient(180deg,#f8f9fb_0%,#edf1f4_100%)] px-5 py-6 md:px-8 md:py-8">
    <div class="mx-auto grid max-w-7xl grid-cols-1 gap-6 lg:grid-cols-[1.15fr_0.85fr] lg:items-stretch">
      <section class="overflow-hidden rounded-[32px] border border-[#222831] bg-[#111418] text-white shadow-[0_30px_80px_rgba(15,18,24,0.3)]">
        <div class="grid h-full grid-cols-1 lg:grid-cols-[0.95fr_1.05fr]">
          <div class="flex flex-col justify-between border-b border-white/10 p-7 md:p-9 lg:border-r lg:border-b-0">
            <div>
              <div class="flex items-center gap-3 text-sm font-medium text-white/74">
                <span class="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-white/12 bg-white/8 text-base font-semibold">S</span>
                <div>
                  <div class="text-[11px] uppercase tracking-[0.26em] text-white/42">Social workflow</div>
                  <div class="mt-1 text-base font-semibold text-white">Schedra workspace</div>
                </div>
              </div>

              <div class="mt-10">
                <p class="text-xs font-semibold uppercase tracking-[0.28em] text-white/58">Operator console</p>
                <h1 class="mt-4 max-w-md text-4xl leading-tight font-semibold tracking-tight md:text-[44px]">
                  Start where the team left off.
                </h1>
                <p class="mt-4 max-w-lg text-sm leading-7 text-white/70">
                  Move from inbox triage to queued publishing without losing the state of campaigns, approvals, or connected channels.
                </p>
              </div>
            </div>

            <div class="mt-8 grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
              <article
                v-for="item in quickStats"
                :key="item.label"
                class="rounded-2xl border border-white/10 bg-white/6 px-4 py-4 backdrop-blur-sm"
              >
                <p class="text-[11px] uppercase tracking-[0.16em] text-white/48">{{ item.label }}</p>
                <p class="mt-3 text-3xl font-semibold tracking-tight text-white">{{ item.value }}</p>
                <p class="mt-1 text-xs text-white/58">{{ item.note }}</p>
              </article>
            </div>
          </div>

            <div class="bg-[linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))] p-5 md:p-7">
            <div class="rounded-[28px] border border-white/10 bg-[#171b21] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] md:p-5">
              <div class="flex items-center justify-between border-b border-white/8 pb-4">
                <div>
                  <p class="text-[11px] uppercase tracking-[0.2em] text-white/42">Today</p>
                  <h2 class="mt-2 text-lg font-semibold text-white">Publishing desk</h2>
                </div>
                <div class="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/6 px-3 py-1 text-xs font-medium text-white/74">
                  <span class="h-2 w-2 rounded-full bg-white/70" />
                  Live
                </div>
              </div>

              <div class="mt-4 grid gap-3">
                <article
                  v-for="item in timeline"
                  :key="item.time + item.title"
                  class="grid grid-cols-[54px_minmax(0,1fr)] gap-3 rounded-2xl border border-white/8 bg-white/[0.035] p-3"
                >
                  <div class="rounded-xl bg-white/6 px-2 py-3 text-center">
                    <div class="text-sm font-semibold text-white">{{ item.time }}</div>
                    <div class="mt-1 text-[10px] uppercase tracking-[0.18em] text-white/38">slot</div>
                  </div>
                  <div class="min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="h-2 w-2 rounded-full bg-white/70" />
                      <p class="truncate text-sm font-medium text-white">{{ item.title }}</p>
                    </div>
                    <p class="mt-2 text-sm leading-6 text-white/60">{{ item.detail }}</p>
                  </div>
                </article>
              </div>

              <div class="mt-4 grid gap-3 sm:grid-cols-2">
                <div class="rounded-2xl border border-white/8 bg-white/[0.035] p-4">
                  <div class="flex items-center justify-between">
                    <span class="text-xs uppercase tracking-[0.16em] text-white/42">Review queue</span>
                    <span class="rounded-full bg-white/8 px-2 py-1 text-[11px] text-white/62">14 items</span>
                  </div>
                  <div class="mt-4 h-2 overflow-hidden rounded-full bg-white/8">
                    <div class="h-full w-[72%] rounded-full bg-[#aab4c2]" />
                  </div>
                  <p class="mt-3 text-sm text-white/58">Approvals are mostly cleared before the afternoon batch.</p>
                </div>
                <div class="rounded-2xl border border-white/8 bg-white/[0.035] p-4">
                  <div class="flex items-center justify-between">
                    <span class="text-xs uppercase tracking-[0.16em] text-white/42">Connected pages</span>
                    <span class="rounded-full bg-white/8 px-2 py-1 text-[11px] text-white/62">8 healthy</span>
                  </div>
                  <div class="mt-4 flex gap-2">
                    <span v-for="index in 8" :key="index" class="h-8 flex-1 rounded-lg bg-[linear-gradient(180deg,rgba(196,204,214,0.42),rgba(112,121,132,0.2))]" />
                  </div>
                  <p class="mt-3 text-sm text-white/58">No token refresh issues detected across active channels.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="flex rounded-[32px] border border-[var(--line)] bg-[var(--panel)] p-4 shadow-[0_24px_70px_rgba(19,38,27,0.08)] md:p-6">
        <div class="flex w-full flex-col rounded-[28px] bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(247,250,253,0.98))] p-5 md:p-7">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--brand)]">Login</p>
              <h2 class="mt-3 text-3xl font-semibold tracking-tight text-[var(--ink)]">Welcome back</h2>
              <p class="mt-3 max-w-md text-sm leading-6 text-[var(--muted)]">
                Sign in to resume approvals, queue management, and campaign scheduling.
              </p>
            </div>
            <NuxtLink
              to="/"
              class="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--line)] bg-white text-[var(--muted)] transition hover:border-[var(--brand)] hover:text-[var(--ink)]"
              title="Back to home"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </NuxtLink>
          </div>

          <div class="mt-6 grid gap-3 sm:grid-cols-2">
            <NuxtLink
              to="/forgot-password"
              class="inline-flex items-center justify-center gap-2 rounded-2xl border border-[var(--line)] bg-white px-4 py-3 text-sm font-medium text-[var(--ink)] transition hover:border-[#8a95a3] hover:bg-[var(--surface-muted)]"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="9" />
                <path d="M9.09 9a3 3 0 0 1 5.82 1c0 2-3 3-3 3" />
                <path d="M12 17h.01" />
              </svg>
              Forgot password
            </NuxtLink>
            <NuxtLink
              to="/register"
              class="inline-flex items-center justify-center gap-2 rounded-2xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3 text-sm font-medium text-[var(--muted)] transition hover:border-[#8a95a3] hover:text-[var(--ink)]"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M12 5l7 7-7 7" />
                <path d="M5 12h13" />
              </svg>
              Create workspace
            </NuxtLink>
          </div>

          <form class="mt-6 space-y-4" @submit.prevent="submit">
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-[var(--ink)]">Email</span>
              <div class="flex items-center gap-3 rounded-2xl border border-[var(--line)] bg-white px-4 py-3 transition focus-within:border-[#8a95a3]">
                <svg class="shrink-0 text-[var(--muted)]" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <rect x="3" y="5" width="18" height="14" rx="3" />
                  <path d="M4 7l8 6 8-6" />
                </svg>
                <input
                  v-model="form.email"
                  type="email"
                  autocomplete="email"
                  class="w-full border-0 bg-transparent p-0 text-sm text-[var(--ink)] outline-none placeholder:text-[#a1acb8]"
                  placeholder="you@company.com"
                />
              </div>
            </label>

            <label class="block">
              <span class="mb-2 block text-sm font-medium text-[var(--ink)]">Password</span>
              <div class="flex items-center gap-3 rounded-2xl border border-[var(--line)] bg-white px-4 py-3 transition focus-within:border-[#8a95a3]">
                <svg class="shrink-0 text-[var(--muted)]" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <rect x="4" y="11" width="16" height="9" rx="2" />
                  <path d="M8 11V8a4 4 0 0 1 8 0v3" />
                </svg>
                <input
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  autocomplete="current-password"
                  class="w-full border-0 bg-transparent p-0 text-sm text-[var(--ink)] outline-none placeholder:text-[#a1acb8]"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-[var(--muted)] transition hover:bg-[var(--surface-muted)] hover:text-[var(--ink)]"
                  :title="showPassword ? 'Hide password' : 'Show password'"
                  @click="showPassword = !showPassword"
                >
                  <svg v-if="showPassword" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M3 3l18 18" />
                    <path d="M10.6 10.6A3 3 0 0 0 13.4 13.4" />
                    <path d="M9.9 5.1A10.9 10.9 0 0 1 12 5c6.5 0 10 7 10 7a19.6 19.6 0 0 1-4.2 4.8" />
                    <path d="M6.7 6.7C4.1 8.3 2 12 2 12a19.8 19.8 0 0 0 7.7 5.8" />
                  </svg>
                </button>
              </div>
            </label>

            <div class="rounded-2xl border border-[var(--line)] bg-[var(--bg)] px-4 py-4 text-sm text-[var(--muted)]">
              <div class="font-medium text-[var(--ink)]">Session-backed workspace access</div>
              <div class="mt-3 space-y-2 leading-6">
                <div>Sign in uses Django session cookies through the app BFF.</div>
                <div>Password reset links are sent to the account email configured for this workspace.</div>
              </div>
            </div>

            <p v-if="error" class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {{ error }}
            </p>

            <button
              type="submit"
              class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[#1d232b] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#2a313b] active:bg-[#151a20] disabled:cursor-not-allowed disabled:opacity-45"
              :disabled="loading || !form.email.trim() || !form.password.trim()"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M5 12h14" />
                <path d="M13 6l6 6-6 6" />
              </svg>
              {{ loading ? "Signing in..." : "Enter workspace" }}
            </button>
          </form>

          <div class="mt-4 flex items-center justify-between gap-4 text-sm text-[var(--muted)]">
            <span>Need access for a new team?</span>
            <NuxtLink to="/register" class="font-semibold text-[#49515d] hover:text-[var(--ink)]">Create workspace</NuxtLink>
          </div>

          <div class="mt-6 grid gap-3 border-t border-[var(--line)] pt-5 text-sm text-[var(--muted)] sm:grid-cols-3">
            <div class="rounded-2xl border border-[var(--line)] bg-white px-4 py-3">
              <div class="text-xs uppercase tracking-[0.16em] text-[#6d7783]">Session</div>
              <div class="mt-2 font-medium text-[var(--ink)]">Cookie auth</div>
            </div>
            <div class="rounded-2xl border border-[var(--line)] bg-white px-4 py-3">
              <div class="text-xs uppercase tracking-[0.16em] text-[#6d7783]">Security</div>
              <div class="mt-2 font-medium text-[var(--ink)]">CSRF protected</div>
            </div>
            <div class="rounded-2xl border border-[var(--line)] bg-white px-4 py-3">
              <div class="text-xs uppercase tracking-[0.16em] text-[#6d7783]">Access</div>
              <div class="mt-2 font-medium text-[var(--ink)]">Single workspace</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
