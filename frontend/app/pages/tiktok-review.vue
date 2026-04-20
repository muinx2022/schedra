<script setup lang="ts">
const session = useSessionState()

const isAuthenticated = computed(() => session.value.hydrated && session.value.authenticated)

const products = [
  {
    title: "Creator account connection",
    detail: "The user connects a TikTok creator profile from Workspace Settings through the TikTok OAuth flow.",
  },
  {
    title: "Basic profile read",
    detail: "Schedra uses the returned identity data to show the connected TikTok creator profile inside the workspace.",
  },
  {
    title: "Direct publishing",
    detail: "After connection, the user can create or schedule a post and publish media to the connected TikTok account.",
  },
]

const reviewerSteps = [
  "Open this page on schedra.net to confirm the live website domain used in review.",
  "Create a workspace or sign in with a review account.",
  "Open Workspace Settings and launch the TikTok connection flow.",
  "Authorize the TikTok creator account and return to Schedra.",
  "Verify the connected TikTok account appears in Settings.",
  "Open Posts, create media content, then publish or schedule it to TikTok.",
]

useHead({
  title: "TikTok Integration Review - Schedra",
  meta: [
    {
      name: "description",
      content: "Public review route for the Schedra TikTok integration flow, including account connection and publishing steps.",
    },
  ],
})
</script>

<template>
  <div class="review-page">
    <section class="review-hero">
      <div class="review-copy">
        <p class="review-kicker">TikTok Integration Review</p>
        <h1>Schedra connects TikTok creator accounts for publishing workflows.</h1>
        <p class="review-lead">
          This page is the public walkthrough for TikTok app review. It shows the live website domain, the supported flow,
          and the exact screens used to connect a TikTok account and publish from the workspace.
        </p>

        <div class="review-actions">
          <NuxtLink
            v-if="isAuthenticated"
            to="/app/settings?connect=tiktok"
            class="review-btn review-btn-primary"
          >
            Open TikTok connect flow
          </NuxtLink>
          <NuxtLink v-if="isAuthenticated" to="/app/posts" class="review-btn">
            Open posts
          </NuxtLink>
          <NuxtLink v-if="!isAuthenticated" to="/register" class="review-btn review-btn-primary">
            Create workspace
          </NuxtLink>
          <NuxtLink v-if="!isAuthenticated" to="/login" class="review-btn">
            Sign in
          </NuxtLink>
        </div>

        <div class="review-links">
          <NuxtLink to="/chinh-sach-rieng-tu">Privacy policy</NuxtLink>
          <NuxtLink to="/quy-dinh-su-dung">Terms of service</NuxtLink>
          <NuxtLink to="/">Home</NuxtLink>
        </div>
      </div>

      <div class="review-panel">
        <div class="review-panel-header">
          <span>Live domain</span>
          <strong>schedra.net</strong>
        </div>
        <div class="review-surface">
          <div class="review-surface-row">
            <span>Route</span>
            <strong>/tiktok-review</strong>
          </div>
          <div class="review-surface-row">
            <span>OAuth start</span>
            <strong>/app/settings?connect=tiktok</strong>
          </div>
          <div class="review-surface-row">
            <span>Publishing</span>
            <strong>/app/posts</strong>
          </div>
          <div class="review-surface-row">
            <span>Scopes in use</span>
            <strong>user.info.basic, video.publish</strong>
          </div>
        </div>
      </div>
    </section>

    <section class="review-grid">
      <article class="review-card">
        <p class="review-section-label">What the integration does</p>
        <div class="review-stack">
          <div v-for="item in products" :key="item.title" class="review-item">
            <h2>{{ item.title }}</h2>
            <p>{{ item.detail }}</p>
          </div>
        </div>
      </article>

      <article class="review-card">
        <p class="review-section-label">Review video flow</p>
        <ol class="review-steps">
          <li v-for="step in reviewerSteps" :key="step">{{ step }}</li>
        </ol>
      </article>
    </section>

    <section class="review-card review-note">
      <p class="review-section-label">Important note for reviewers</p>
      <p>
        Schedra does not use TikTok for end-user login. TikTok is used inside an authenticated Schedra workspace to connect
        a creator account, display the connected profile, and publish user-selected media to that TikTok account.
      </p>
    </section>
  </div>
</template>

<style scoped>
.review-page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 56px 24px 80px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.review-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 24px;
}

.review-copy,
.review-card,
.review-panel {
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-soft);
}

.review-copy {
  border-radius: 28px;
  padding: 32px;
}

.review-kicker,
.review-section-label {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 700;
}

.review-copy h1 {
  margin: 12px 0 0;
  font-size: clamp(30px, 4vw, 48px);
  line-height: 1.08;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.review-lead {
  margin: 18px 0 0;
  max-width: 720px;
  font-size: 16px;
  line-height: 1.7;
  color: var(--muted);
}

.review-actions,
.review-links {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.review-actions {
  margin-top: 28px;
}

.review-links {
  margin-top: 18px;
}

.review-links a {
  color: var(--muted);
  font-size: 14px;
}

.review-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 46px;
  padding: 0 18px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink);
  font-weight: 700;
  text-decoration: none;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.review-btn:hover {
  border-color: #8f98a3;
  background: var(--surface-muted);
}

.review-btn-primary {
  background: #171b21;
  border-color: #171b21;
  color: #fff;
}

.review-btn-primary:hover {
  background: #232933;
  border-color: #232933;
  color: #fff;
}

.review-panel {
  border-radius: 28px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.review-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 6px 4px 0;
  color: var(--muted);
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.review-panel-header strong {
  color: var(--ink);
  font-size: 15px;
  letter-spacing: 0;
}

.review-surface {
  display: grid;
  gap: 10px;
  border-radius: 20px;
  background: var(--surface-muted);
  padding: 16px;
}

.review-surface-row {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 12px 14px;
  border-radius: 14px;
  background: var(--panel);
  border: 1px solid var(--line-soft);
  font-size: 14px;
}

.review-surface-row span {
  color: var(--muted);
}

.review-surface-row strong {
  color: var(--ink);
  text-align: right;
}

.review-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.review-card {
  border-radius: 24px;
  padding: 28px;
}

.review-stack {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.review-item {
  border: 1px solid var(--line-soft);
  border-radius: 18px;
  background: var(--surface);
  padding: 18px;
}

.review-item h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.3;
  color: var(--ink);
}

.review-item p,
.review-note p {
  margin: 10px 0 0;
  font-size: 15px;
  line-height: 1.7;
  color: var(--muted);
}

.review-steps {
  margin: 18px 0 0;
  padding-left: 20px;
  display: grid;
  gap: 12px;
  color: var(--ink);
}

.review-steps li {
  line-height: 1.7;
}

.review-note {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(246, 248, 250, 0.96));
}

@media (max-width: 900px) {
  .review-hero,
  .review-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .review-page {
    padding: 32px 16px 56px;
  }

  .review-copy,
  .review-card,
  .review-panel {
    padding: 22px;
    border-radius: 22px;
  }

  .review-surface-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .review-surface-row strong {
    text-align: left;
  }
}
</style>
