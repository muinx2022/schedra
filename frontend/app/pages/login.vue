<script setup lang="ts">
const session = useSessionState()
const form = reactive({ email: "demo@example.com", password: "demo12345" })
const error = ref("")
const loading = ref(false)

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
  <div class="mx-auto grid min-h-[calc(100vh-88px)] max-w-6xl grid-cols-1 gap-6 px-5 py-8 md:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
    <section class="rounded-[32px] border border-[var(--line)] bg-[linear-gradient(160deg,rgba(13,122,95,0.98),rgba(6,79,63,0.92))] p-8 text-white shadow-[0_30px_80px_rgba(6,79,63,0.2)] md:p-10">
      <p class="mb-3 text-xs font-semibold uppercase tracking-[0.28em] text-white/70">Workspace access</p>
      <h1 class="m-0 max-w-md text-4xl leading-tight font-semibold tracking-tight">
        Sign in and get back to your content pipeline.
      </h1>
      <p class="mt-4 max-w-xl text-sm leading-7 text-white/78">
        Review ideas, move work across stages, and manage posts without digging through a cluttered dashboard.
      </p>

      <div class="mt-8 grid gap-4 sm:grid-cols-2">
        <div class="rounded-[24px] border border-white/15 bg-white/8 p-5 backdrop-blur-sm">
          <p class="text-sm font-semibold">Fast resume</p>
          <p class="mt-2 text-sm leading-6 text-white/72">Open the workspace and continue exactly where your team left off.</p>
        </div>
        <div class="rounded-[24px] border border-white/15 bg-white/8 p-5 backdrop-blur-sm">
          <p class="text-sm font-semibold">Demo access</p>
          <p class="mt-2 text-sm leading-6 text-white/72">The form is prefilled with the seeded demo account so you can test immediately.</p>
        </div>
      </div>
    </section>

    <section class="rounded-[32px] border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[0_24px_70px_rgba(19,38,27,0.08)] md:p-8">
      <div class="mb-6">
        <p class="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-[var(--brand)]">Login</p>
        <h2 class="m-0 text-3xl font-semibold tracking-tight text-[var(--ink)]">Welcome back</h2>
        <p class="mt-3 text-sm leading-6 text-[var(--muted)]">
          Use your workspace account to continue managing ideas and publishing flow.
        </p>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <label class="block">
          <span class="mb-2 block text-sm font-medium text-[var(--ink)]">Email</span>
          <input
            v-model="form.email"
            type="email"
            autocomplete="email"
            class="w-full rounded-2xl border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition placeholder:text-[#b7b0a5] focus:border-[var(--brand)]"
            placeholder="you@company.com"
          />
        </label>

        <label class="block">
          <span class="mb-2 block text-sm font-medium text-[var(--ink)]">Password</span>
          <input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            class="w-full rounded-2xl border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition placeholder:text-[#b7b0a5] focus:border-[var(--brand)]"
            placeholder="Enter your password"
          />
        </label>

        <div class="rounded-2xl border border-[var(--line)] bg-[var(--bg)] px-4 py-3 text-sm text-[var(--muted)]">
          Demo account: <strong class="text-[var(--ink)]">demo@example.com</strong> / <strong class="text-[var(--ink)]">demo12345</strong>
        </div>

        <p v-if="error" class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {{ error }}
        </p>

        <button
          type="submit"
          class="inline-flex w-full items-center justify-center rounded-full bg-[var(--brand)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[var(--brand-strong)] disabled:cursor-not-allowed disabled:opacity-45"
          :disabled="loading || !form.email.trim() || !form.password.trim()"
        >
          {{ loading ? "Signing in..." : "Sign in" }}
        </button>
      </form>

      <div class="mt-6 flex items-center justify-between gap-4 border-t border-[var(--line)] pt-5 text-sm text-[var(--muted)]">
        <span>No workspace yet?</span>
        <NuxtLink to="/register" class="font-semibold text-[var(--brand)] hover:text-[var(--brand-strong)]">
          Create one
        </NuxtLink>
      </div>
    </section>
  </div>
</template>
