<script setup lang="ts">
const localePath = useLocalePath()
const form = reactive({ email: "" })
const error = ref("")
const message = ref("")
const loading = ref(false)

async function submit() {
  if (loading.value) return
  error.value = ""
  message.value = ""
  loading.value = true
  try {
    const response = await apiFetch<{ detail: string }>("/auth/password-reset/request/", {
      method: "POST",
      body: form,
    })
    message.value = response.detail
  } catch (err: any) {
    error.value = extractApiError(err, "Could not start password reset.")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-88px)] bg-[radial-gradient(circle_at_top_left,rgba(98,108,122,0.12),transparent_28%),linear-gradient(180deg,#f8f9fb_0%,#edf1f4_100%)] px-5 py-6 md:px-8 md:py-8">
    <div class="mx-auto grid max-w-6xl grid-cols-1 gap-6 lg:grid-cols-[1fr_0.92fr]">
      <section class="rounded-[32px] border border-[#222831] bg-[#111418] p-7 text-white shadow-[0_30px_80px_rgba(15,18,24,0.3)] md:p-9">
        <p class="text-[11px] uppercase tracking-[0.26em] text-white/42">Account recovery</p>
        <h1 class="mt-5 max-w-lg text-4xl leading-tight font-semibold tracking-tight md:text-[44px]">
          Reset access without opening Django admin.
        </h1>
        <p class="mt-4 max-w-xl text-sm leading-7 text-white/68">
          Enter the workspace email address and the system will send a reset link if the account exists.
        </p>

        <div class="mt-8 grid gap-3 sm:grid-cols-2">
          <article class="rounded-2xl border border-white/10 bg-white/6 p-4">
            <div class="text-[11px] uppercase tracking-[0.16em] text-white/42">Security</div>
            <p class="mt-3 text-sm leading-6 text-white/68">Unknown emails receive the same response, so the endpoint does not leak account presence.</p>
          </article>
          <article class="rounded-2xl border border-white/10 bg-white/6 p-4">
            <div class="text-[11px] uppercase tracking-[0.16em] text-white/42">Template</div>
            <p class="mt-3 text-sm leading-6 text-white/68">The reset email subject and body are editable from Django staff settings.</p>
          </article>
        </div>
      </section>

      <section class="flex rounded-[32px] border border-[var(--line)] bg-[var(--panel)] p-4 shadow-[0_24px_70px_rgba(19,38,27,0.08)] md:p-6">
        <div class="flex w-full flex-col rounded-[28px] bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(247,250,253,0.98))] p-5 md:p-7">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-[#6d7783]">Forgot password</p>
              <h2 class="mt-3 text-3xl font-semibold tracking-tight text-[var(--ink)]">Send reset link</h2>
              <p class="mt-3 max-w-md text-sm leading-6 text-[var(--muted)]">
                Use the account email that signs into your workspace.
              </p>
            </div>
            <NuxtLink
              :to="localePath('/login')"
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
              <span class="mb-2 block text-sm font-medium text-[var(--ink)]">Email</span>
              <input
                v-model="form.email"
                type="email"
                autocomplete="email"
                class="w-full rounded-2xl border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[#8a95a3]"
                placeholder="you@company.com"
              />
            </label>

            <div class="rounded-2xl border border-[var(--line)] bg-[var(--bg)] px-4 py-4 text-sm text-[var(--muted)]">
              If the address exists, the email will include a secure link to `/reset-password`.
            </div>

            <p v-if="message" class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {{ message }}
            </p>
            <p v-if="error" class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {{ error }}
            </p>

            <button
              type="submit"
              class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[#1d232b] px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-[#2a313b] active:bg-[#151a20] disabled:cursor-not-allowed disabled:opacity-45"
              :disabled="loading || !form.email.trim()"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M22 2L11 13" />
                <path d="M22 2L15 22l-4-9-9-4 20-7z" />
              </svg>
              {{ loading ? "Sending..." : "Send reset email" }}
            </button>
          </form>
        </div>
      </section>
    </div>
  </div>
</template>
