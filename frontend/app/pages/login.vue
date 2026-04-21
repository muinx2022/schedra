<script setup lang="ts">
const session = useSessionState()
const form = reactive({ email: "", password: "" })
const error = ref("")
const loading = ref(false)
const showPassword = ref(false)
const emailInputRef = ref<HTMLInputElement | null>(null)
const passwordInputRef = ref<HTMLInputElement | null>(null)

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

const canSubmit = computed(() => !!form.email.trim() && !!form.password.trim() && !loading.value)

function syncAutofillValues() {
  const emailValue = emailInputRef.value?.value || ""
  const passwordValue = passwordInputRef.value?.value || ""
  if (emailValue && emailValue !== form.email) form.email = emailValue
  if (passwordValue && passwordValue !== form.password) form.password = passwordValue
}

onMounted(() => {
  syncAutofillValues()
  window.setTimeout(syncAutofillValues, 120)
  window.setTimeout(syncAutofillValues, 500)
})

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
  <div class="login-page">
    <div class="login-shell">
      <section class="login-console">
        <div class="console-main">
          <div class="console-brand">
            <span class="console-mark">S</span>
            <div>
              <div class="console-label">Social workflow</div>
              <div class="console-name">Schedra workspace</div>
            </div>
          </div>

          <div class="console-copy">
            <p class="console-kicker">Operator console</p>
            <h1>Start where the team left off.</h1>
            <p>
              Move from inbox triage to queued publishing without losing the state of campaigns, approvals, or connected
              channels.
            </p>
          </div>

          <div class="console-stats">
            <article v-for="item in quickStats" :key="item.label" class="console-stat">
              <p class="console-stat-label">{{ item.label }}</p>
              <p class="console-stat-value">{{ item.value }}</p>
              <p class="console-stat-note">{{ item.note }}</p>
            </article>
          </div>
        </div>

        <div class="console-panel">
          <div class="console-panel-head">
            <div>
              <p class="console-panel-label">Today</p>
              <h2>Publishing desk</h2>
            </div>
            <div class="console-live">
              <span />
              Live
            </div>
          </div>

          <div class="console-timeline">
            <article v-for="item in timeline" :key="item.time + item.title" class="timeline-item">
              <div class="timeline-time">
                <div>{{ item.time }}</div>
                <small>slot</small>
              </div>
              <div class="timeline-copy">
                <div class="timeline-title">
                  <span />
                  <p>{{ item.title }}</p>
                </div>
                <p class="timeline-detail">{{ item.detail }}</p>
              </div>
            </article>
          </div>

          <div class="console-health">
            <div class="health-card">
              <div class="health-head">
                <span>Review queue</span>
                <strong>14 items</strong>
              </div>
              <div class="health-bar">
                <div class="health-bar-fill" />
              </div>
              <p>Approvals are mostly cleared before the afternoon batch.</p>
            </div>

            <div class="health-card">
              <div class="health-head">
                <span>Connected pages</span>
                <strong>8 healthy</strong>
              </div>
              <div class="health-grid">
                <span v-for="index in 8" :key="index" />
              </div>
              <p>No token refresh issues detected across active channels.</p>
            </div>
          </div>
        </div>
      </section>

      <section class="login-card">
        <div class="login-card-inner">
          <div class="login-head">
            <div>
              <p class="login-kicker">Login</p>
              <h2>Welcome back</h2>
              <p class="login-subtitle">
                Sign in to resume approvals, queue management, and campaign scheduling.
              </p>
            </div>

            <NuxtLink to="/" class="login-home-link" title="Back to home">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </NuxtLink>
          </div>

          <div class="login-actions">
            <NuxtLink to="/forgot-password" class="login-action-link">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="9" />
                <path d="M9.09 9a3 3 0 0 1 5.82 1c0 2-3 3-3 3" />
                <path d="M12 17h.01" />
              </svg>
              Forgot password
            </NuxtLink>

            <NuxtLink to="/register" class="login-action-link login-action-link-muted">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M12 5l7 7-7 7" />
                <path d="M5 12h13" />
              </svg>
              Create workspace
            </NuxtLink>
          </div>

          <form class="login-form" @submit.prevent="submit">
            <label class="login-field">
              <span>Email</span>
              <div class="login-input-wrap">
                <svg class="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <rect x="3" y="5" width="18" height="14" rx="3" />
                  <path d="M4 7l8 6 8-6" />
                </svg>
                <input
                  ref="emailInputRef"
                  v-model="form.email"
                  type="email"
                  autocomplete="email"
                  placeholder="you@company.com"
                  @input="syncAutofillValues"
                />
              </div>
            </label>

            <label class="login-field">
              <span>Password</span>
              <div class="login-input-wrap">
                <svg class="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <rect x="4" y="11" width="16" height="9" rx="2" />
                  <path d="M8 11V8a4 4 0 0 1 8 0v3" />
                </svg>
                <input
                  ref="passwordInputRef"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  autocomplete="current-password"
                  placeholder="Enter your password"
                  @input="syncAutofillValues"
                />
                <button
                  type="button"
                  class="login-input-toggle"
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

            <div class="login-note">
              <div class="login-note-title">Session-backed workspace access</div>
              <div class="login-note-copy">
                <div>Sign in uses Django session cookies through the app BFF.</div>
                <div>Password reset links are sent to the account email configured for this workspace.</div>
              </div>
            </div>

            <p v-if="error" class="login-error">
              {{ error }}
            </p>

            <button
              type="submit"
              class="login-submit"
              :disabled="!canSubmit"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M5 12h14" />
                <path d="M13 6l6 6-6 6" />
              </svg>
              {{ loading ? "Signing in..." : "Enter workspace" }}
            </button>
          </form>

          <div class="login-footer">
            <span>Need access for a new team?</span>
            <NuxtLink to="/register">Create workspace</NuxtLink>
          </div>

          <div class="login-meta">
            <div class="login-meta-card">
              <div class="login-meta-label">Session</div>
              <div class="login-meta-value">Cookie auth</div>
            </div>
            <div class="login-meta-card">
              <div class="login-meta-label">Security</div>
              <div class="login-meta-value">CSRF protected</div>
            </div>
            <div class="login-meta-card">
              <div class="login-meta-label">Access</div>
              <div class="login-meta-value">Single workspace</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  --login-page-bg:
    radial-gradient(circle at top left, rgba(98, 108, 122, 0.12), transparent 28%),
    linear-gradient(180deg, #f8f9fb 0%, #edf1f4 100%);
  --login-card-bg: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 253, 0.98));
  --login-card-shadow: 0 24px 70px rgba(19, 38, 27, 0.08);
  --login-control-bg: #ffffff;
  --login-control-border: var(--line);
  --login-control-hover: #8a95a3;
  --login-soft-bg: var(--bg);
  --login-soft-text: #6d7783;
  --login-placeholder: #a1acb8;
  --login-link: #49515d;
  --login-error-bg: #fef2f2;
  --login-error-border: #fecaca;
  --login-error-text: #b91c1c;
  min-height: calc(100vh - 88px);
  background: var(--login-page-bg);
  padding: 24px 20px;
}

.login-shell {
  max-width: 1280px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}

.login-console {
  overflow: hidden;
  border: 1px solid #222831;
  border-radius: 32px;
  background: #111418;
  color: #ffffff;
  box-shadow: 0 30px 80px rgba(15, 18, 24, 0.3);
  display: grid;
}

.console-main {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 32px;
  padding: 28px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.console-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.74);
}

.console-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.08);
  font-size: 16px;
  font-weight: 600;
}

.console-label,
.console-kicker,
.console-panel-label,
.console-stat-label,
.health-head span,
.timeline-time small {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
}

.console-label,
.console-panel-label {
  color: rgba(255, 255, 255, 0.42);
}

.console-name,
.console-copy h1,
.console-panel-head h2,
.timeline-title p,
.console-stat-value {
  color: #ffffff;
}

.console-name {
  margin-top: 4px;
  font-size: 16px;
  font-weight: 600;
}

.console-copy h1 {
  margin: 16px 0 0;
  max-width: 18ch;
  font-size: clamp(34px, 4vw, 44px);
  line-height: 1.08;
  letter-spacing: -0.02em;
}

.console-copy p,
.console-stat-note,
.timeline-detail,
.health-card p {
  color: rgba(255, 255, 255, 0.6);
}

.console-copy > p:last-child {
  margin: 16px 0 0;
  max-width: 56ch;
  font-size: 14px;
  line-height: 1.8;
}

.console-kicker {
  margin: 0;
  color: rgba(255, 255, 255, 0.58);
  font-weight: 700;
}

.console-stats {
  display: grid;
  gap: 12px;
}

.console-stat {
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
  padding: 16px;
}

.console-stat-label {
  margin: 0;
  color: rgba(255, 255, 255, 0.48);
}

.console-stat-value {
  margin: 12px 0 0;
  font-size: 30px;
  font-weight: 600;
  letter-spacing: -0.03em;
}

.console-stat-note {
  margin: 4px 0 0;
  font-size: 12px;
}

.console-panel {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
  padding: 20px;
}

.console-panel-head,
.health-head,
.timeline-title,
.login-head,
.login-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.console-panel-head {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 16px;
}

.console-panel-head h2 {
  margin: 8px 0 0;
  font-size: 18px;
}

.console-live {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  padding: 6px 12px;
  color: rgba(255, 255, 255, 0.74);
  font-size: 12px;
  font-weight: 500;
}

.console-live span,
.timeline-title span {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
}

.console-timeline,
.login-form,
.login-note-copy {
  display: grid;
  gap: 12px;
}

.console-timeline {
  margin-top: 16px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  gap: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.035);
  padding: 12px;
}

.timeline-time {
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  padding: 12px 8px;
  text-align: center;
}

.timeline-time div {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.timeline-time small {
  display: block;
  margin-top: 4px;
  color: rgba(255, 255, 255, 0.38);
}

.timeline-title p,
.timeline-detail,
.health-card p,
.login-subtitle,
.login-note,
.login-footer,
.login-meta-label {
  margin: 0;
}

.timeline-title p {
  min-width: 0;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timeline-detail,
.health-card p {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.7;
}

.console-health {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.health-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.035);
  padding: 16px;
}

.health-head strong {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  padding: 4px 8px;
  color: rgba(255, 255, 255, 0.62);
  font-size: 11px;
  font-weight: 500;
}

.health-bar {
  margin-top: 16px;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
}

.health-bar-fill {
  width: 72%;
  height: 100%;
  border-radius: inherit;
  background: #aab4c2;
}

.health-grid {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.health-grid span {
  flex: 1 1 0;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(196, 204, 214, 0.42), rgba(112, 121, 132, 0.2));
}

.login-card {
  border: 1px solid var(--line);
  border-radius: 32px;
  background: var(--panel);
  box-shadow: var(--login-card-shadow);
  padding: 16px;
}

.login-card-inner {
  width: 100%;
  border-radius: 28px;
  background: var(--login-card-bg);
  padding: 24px;
}

.login-head {
  align-items: flex-start;
}

.login-kicker {
  margin: 0;
  color: var(--brand);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.24em;
}

.login-head h2 {
  margin: 12px 0 0;
  color: var(--ink);
  font-size: 32px;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.login-subtitle {
  margin-top: 12px;
  max-width: 42ch;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.7;
}

.login-home-link,
.login-input-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--login-control-border);
  background: var(--login-control-bg);
  color: var(--muted);
  transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
}

.login-home-link {
  width: 44px;
  height: 44px;
  border-radius: 16px;
}

.login-home-link:hover,
.login-input-toggle:hover {
  border-color: var(--login-control-hover);
  color: var(--ink);
}

.login-actions,
.login-meta {
  display: grid;
  gap: 12px;
}

.login-actions {
  margin-top: 24px;
}

.login-action-link,
.login-field span,
.login-note-title,
.login-footer a,
.login-meta-value {
  color: var(--ink);
}

.login-action-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 48px;
  border: 1px solid var(--login-control-border);
  border-radius: 16px;
  background: var(--login-control-bg);
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
}

.login-action-link:hover {
  border-color: var(--login-control-hover);
  background: var(--surface-muted);
}

.login-action-link-muted {
  background: var(--surface);
  color: var(--muted);
}

.login-form {
  margin-top: 24px;
}

.login-field {
  display: grid;
  gap: 8px;
}

.login-field span {
  font-size: 14px;
  font-weight: 500;
}

.login-input-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid var(--login-control-border);
  border-radius: 16px;
  background: var(--login-control-bg);
  padding: 0 16px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.login-input-wrap:focus-within {
  border-color: var(--login-control-hover);
}

.login-input-icon {
  flex: 0 0 auto;
  color: var(--muted);
}

.login-input-wrap input {
  width: 100%;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--ink);
  padding: 14px 0;
  font-size: 14px;
  outline: none;
}

.login-input-wrap input::placeholder {
  color: var(--login-placeholder);
}

.login-input-toggle {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  cursor: pointer;
}

.login-note {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--login-soft-bg);
  padding: 16px;
  color: var(--muted);
  font-size: 14px;
}

.login-note-title {
  font-weight: 500;
}

.login-note-copy {
  margin-top: 12px;
  line-height: 1.7;
}

.login-error {
  border: 1px solid var(--login-error-border);
  border-radius: 16px;
  background: var(--login-error-bg);
  padding: 12px 16px;
  color: var(--login-error-text);
  font-size: 14px;
}

.login-submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  border: 0;
  border-radius: 16px;
  background: #1d232b;
  padding: 14px 20px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, opacity 0.15s ease;
}

.login-submit:hover:not(:disabled) {
  background: #2a313b;
}

.login-submit:active:not(:disabled) {
  background: #151a20;
}

.login-submit:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.login-footer {
  margin-top: 16px;
  color: var(--muted);
  font-size: 14px;
}

.login-footer a {
  font-weight: 600;
  color: var(--login-link);
}

.login-footer a:hover {
  color: var(--ink);
}

.login-meta {
  margin-top: 24px;
  border-top: 1px solid var(--line);
  padding-top: 20px;
}

.login-meta-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--login-control-bg);
  padding: 14px 16px;
}

.login-meta-label {
  color: var(--login-soft-text);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
}

.login-meta-value {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 500;
}

@media (min-width: 1024px) {
  .login-page {
    padding: 32px;
  }

  .login-shell {
    grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
    align-items: stretch;
  }

  .login-console {
    grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
  }

  .console-main {
    border-right: 1px solid rgba(255, 255, 255, 0.1);
    border-bottom: 0;
    padding: 36px;
  }

  .console-panel {
    padding: 28px;
  }
}

@media (min-width: 640px) {
  .console-stats,
  .console-health,
  .login-actions,
  .login-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1280px) {
  .console-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 639px) {
  .login-page {
    padding: 16px;
  }

  .console-main,
  .console-panel,
  .login-card,
  .login-card-inner {
    padding: 20px;
  }

  .login-head,
  .login-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .timeline-item {
    grid-template-columns: 1fr;
  }

  .timeline-time {
    display: inline-grid;
    width: fit-content;
    min-width: 54px;
  }
}
</style>

<style>
:root[data-theme="dark"] .login-page {
  --login-page-bg:
    radial-gradient(circle at top left, rgba(137, 148, 165, 0.14), transparent 26%),
    linear-gradient(180deg, #10141a 0%, #0b1015 100%);
  --login-card-bg: linear-gradient(180deg, rgba(19, 24, 31, 0.98), rgba(14, 19, 26, 0.98));
  --login-card-shadow: 0 24px 70px rgba(0, 0, 0, 0.34);
  --login-control-bg: #121821;
  --login-control-border: #27313d;
  --login-control-hover: #6f7b89;
  --login-soft-bg: rgba(255, 255, 255, 0.03);
  --login-soft-text: #8a96a4;
  --login-placeholder: #748190;
  --login-link: #cbd3db;
  --login-error-bg: rgba(185, 28, 28, 0.16);
  --login-error-border: rgba(248, 113, 113, 0.28);
  --login-error-text: #fca5a5;
}

:root[data-theme="dark"] .login-card {
  border-color: #27313d;
  background: #0f141b;
}

:root[data-theme="dark"] .login-home-link,
:root[data-theme="dark"] .login-action-link,
:root[data-theme="dark"] .login-input-wrap,
:root[data-theme="dark"] .login-meta-card {
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) .login-page {
    --login-page-bg:
      radial-gradient(circle at top left, rgba(137, 148, 165, 0.14), transparent 26%),
      linear-gradient(180deg, #10141a 0%, #0b1015 100%);
    --login-card-bg: linear-gradient(180deg, rgba(19, 24, 31, 0.98), rgba(14, 19, 26, 0.98));
    --login-card-shadow: 0 24px 70px rgba(0, 0, 0, 0.34);
    --login-control-bg: #121821;
    --login-control-border: #27313d;
    --login-control-hover: #6f7b89;
    --login-soft-bg: rgba(255, 255, 255, 0.03);
    --login-soft-text: #8a96a4;
    --login-placeholder: #748190;
    --login-link: #cbd3db;
    --login-error-bg: rgba(185, 28, 28, 0.16);
    --login-error-border: rgba(248, 113, 113, 0.28);
    --login-error-text: #fca5a5;
  }

  :root:not([data-theme]) .login-card {
    border-color: #27313d;
    background: #0f141b;
  }

  :root:not([data-theme]) .login-home-link,
  :root:not([data-theme]) .login-action-link,
  :root:not([data-theme]) .login-input-wrap,
  :root:not([data-theme]) .login-meta-card {
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
  }
}
</style>
