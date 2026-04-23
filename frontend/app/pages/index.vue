<template>
  <div class="buf-home">
    <!-- Hero (Buffer-style: bold headline, supportive line, dual CTA, product visual) -->
    <section class="buf-hero">
      <div class="buf-hero-grid">
        <div class="buf-hero-copy">
          <p class="buf-eyebrow">Social media publishing — simplified</p>
          <h1 class="buf-h1">Your social media workspace</h1>
          <p class="buf-lede">
            Plan content, schedule posts, and grow your audience — without the chaos.
          </p>
          <div class="buf-emoji-strip" aria-hidden="true">
            <span>👏</span><span>🚀</span><span>❤️</span><span>📈</span><span>📣</span><span>💬</span><span>🗓️</span><span>🙌</span>
          </div>
          <div class="buf-hero-cta">
            <NuxtLink class="btn buf-btn-brand" :to="localePath('/register')">Get started free</NuxtLink>
            <NuxtLink class="btn secondary" :to="localePath('/login')">Sign in</NuxtLink>
          </div>
          <p class="buf-trust-micro">No credit card needed · Free to get started</p>
        </div>
        <div class="buf-hero-visual">
          <div class="buf-mock-shell">
            <div class="buf-mock-topbar">
              <span class="buf-dot r" /><span class="buf-dot y" /><span class="buf-dot g" />
            </div>
            <div class="buf-mock-body">
              <div class="buf-mock-side">
                <span class="buf-nav-pill on" />
                <span class="buf-nav-pill" />
                <span class="buf-nav-pill" />
                <span class="buf-nav-pill" />
              </div>
              <div class="buf-mock-main">
                <div class="buf-mock-toolbar">
                  <span class="buf-pill">Queue</span>
                  <span class="buf-pill ghost">Calendar</span>
                </div>
                <div class="buf-mock-row" />
                <div class="buf-mock-row short" />
                <div class="buf-mock-row" />
                <div class="buf-mock-cal">
                  <span v-for="n in 12" :key="n" class="buf-cal-cell" :class="{ hot: n === 5 || n === 9 }" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Trust strip -->
    <section class="buf-trust" aria-label="Highlights">
      <p class="buf-trust-heading">Built for teams who ship content on a rhythm, not a rush</p>
      <div class="buf-trust-grid">
        <div class="buf-trust-cell">
          <div class="buf-trust-num">6</div>
          <div class="buf-trust-label">major networks</div>
        </div>
        <div class="buf-trust-cell">
          <div class="buf-trust-num">1</div>
          <div class="buf-trust-label">unified queue &amp; calendar</div>
        </div>
        <div class="buf-trust-cell">
          <div class="buf-trust-num">0</div>
          <div class="buf-trust-label">credit cards to try it</div>
        </div>
      </div>
    </section>

    <!-- Core features -->
    <section id="buf-features" class="buf-block">
      <div class="buf-section-head">
        <h2 class="buf-h2">Core features</h2>
        <p class="buf-subdeck muted">
          Capture ideas, fill your queue, and publish — with a workspace that stays out of your way.
        </p>
      </div>

      <article class="buf-feature-split">
        <div class="buf-feature-copy">
          <span class="buf-tag">Ideas</span>
          <h3 class="buf-h3">Turn sparks into a pipeline</h3>
          <p class="muted">
            A simple board from Inbox to Planned to Ready — so nothing good disappears into a notes app.
          </p>
          <NuxtLink :to="localePath('/register')" class="buf-text-link">Start capturing ideas →</NuxtLink>
        </div>
        <div class="buf-feature-shot buf-shot-green">
          <div class="buf-cards">
            <div class="buf-mini-card"><span class="buf-dot-s" /><div class="buf-lines"><i /><i class="dim" /></div><em>Inbox</em></div>
            <div class="buf-mini-card"><span class="buf-dot-s" /><div class="buf-lines"><i /><i class="dim" /></div><em>Planned</em></div>
            <div class="buf-mini-card"><span class="buf-dot-s" /><div class="buf-lines"><i /><i class="dim" /></div><em class="ok">Ready</em></div>
          </div>
        </div>
      </article>

      <article class="buf-feature-split rev">
        <div class="buf-feature-copy">
          <span class="buf-tag">Publish</span>
          <h3 class="buf-h3">The most practical publishing flow</h3>
          <p class="muted">
            Draft with previews, drop into channel queues, and schedule or publish now — without tab sprawl.
          </p>
          <NuxtLink :to="localePath('/register')" class="buf-text-link">Explore publishing →</NuxtLink>
        </div>
        <div class="buf-feature-shot buf-shot-blue">
          <div class="buf-queue">
            <div class="buf-q-row"><time>9:00</time><span class="buf-badge ok">Scheduled</span><div class="buf-bar" /></div>
            <div class="buf-q-row"><time>12:30</time><span class="buf-badge">Draft</span><div class="buf-bar sm" /></div>
            <div class="buf-q-row"><time>4:15</time><span class="buf-badge ok">Scheduled</span><div class="buf-bar" /></div>
          </div>
        </div>
      </article>

      <article class="buf-feature-split">
        <div class="buf-feature-copy">
          <span class="buf-tag">Workspace</span>
          <h3 class="buf-h3">One calm surface for the whole team</h3>
          <p class="muted">
            Media, campaigns, analytics, and inbox — connected to the same posts your channels will receive.
          </p>
          <NuxtLink :to="localePath('/register')" class="buf-text-link">Open a workspace →</NuxtLink>
        </div>
        <div class="buf-feature-shot buf-shot-warm">
          <div class="buf-editor">
            <div class="buf-editor-lines"><i /><i /><i class="dim" /></div>
            <div class="buf-editor-actions">
              <span class="buf-faux">Save draft</span>
              <span class="buf-faux primary">Publish now</span>
            </div>
          </div>
        </div>
      </article>
    </section>

    <!-- More modules -->
    <section class="buf-more-wrap">
      <div class="buf-section-head tight">
        <h2 class="buf-h2">…and so much more</h2>
        <p class="buf-subdeck muted">Lightweight modules that match how small teams actually work.</p>
      </div>
      <div class="buf-more-grid">
        <div class="buf-more-card">
          <h4>Calendar</h4>
          <p class="muted">See scheduled work across channels in one glance.</p>
        </div>
        <div class="buf-more-card">
          <h4>Campaigns</h4>
          <p class="muted">Group assets and fan out drafts from a single brief.</p>
        </div>
        <div class="buf-more-card">
          <h4>Analytics</h4>
          <p class="muted">Understand what shipped — and what needs attention.</p>
        </div>
        <div class="buf-more-card">
          <h4>Inbox</h4>
          <p class="muted">Triage comments without jumping between native apps.</p>
        </div>
      </div>
    </section>

    <!-- Channels -->
    <section id="buf-channels" class="buf-channels-wrap">
      <div class="buf-section-head">
        <h2 class="buf-h2">Connect your favourite accounts</h2>
        <p class="buf-subdeck muted">
          Facebook, Instagram, LinkedIn, TikTok, YouTube, and Pinterest — from one Schedra workspace.
        </p>
      </div>
      <div class="buf-channel-row">
        <div v-for="c in channelList" :key="c.name" class="buf-ch-pill" :class="c.cls">
          <span class="buf-ch-ico">{{ c.abbr }}</span>
          {{ c.name }}
        </div>
      </div>
    </section>

    <!-- Audiences -->
    <section class="buf-audiences">
      <h2 class="buf-h2 buf-center">Whoever you are, we’ve got you covered</h2>
      <div class="buf-aud-grid">
        <div class="buf-aud-card">
          <h4>Creators</h4>
          <p class="muted">Stay consistent, batch ideas, and keep queues full without burning out.</p>
        </div>
        <div class="buf-aud-card">
          <h4>Small business</h4>
          <p class="muted">One place for promos, hours, and stories — scheduled ahead of busy weeks.</p>
        </div>
        <div class="buf-aud-card">
          <h4>Agencies</h4>
          <p class="muted">A focused stack for delivery: fewer tools, clearer handoffs, reliable publishing.</p>
        </div>
      </div>
    </section>

    <!-- Testimonials -->
    <section class="buf-quotes">
      <h2 class="buf-h2 buf-center">Loved by teams who prefer signal over noise</h2>
      <div class="buf-quote-grid">
        <figure class="buf-quote">
          <blockquote>“Finally a publishing tool that doesn’t get in the way. I go from idea to post in under two minutes.”</blockquote>
          <figcaption><span class="buf-av">S</span><div><strong>Sarah K.</strong><span class="muted">Freelance creator</span></div></figcaption>
        </figure>
        <figure class="buf-quote">
          <blockquote>“The kanban idea board alone is worth it. My calendar has never been this organised.”</blockquote>
          <figcaption><span class="buf-av">M</span><div><strong>Marcus T.</strong><span class="muted">Small business owner</span></div></figcaption>
        </figure>
        <figure class="buf-quote">
          <blockquote>“Exactly the lightweight Buffer alternative I was looking for — clean, fast, focused.”</blockquote>
          <figcaption><span class="buf-av">L</span><div><strong>Linh N.</strong><span class="muted">Social media manager</span></div></figcaption>
        </figure>
      </div>
    </section>

    <!-- Pricing / CTA -->
    <section id="buf-pricing" class="buf-pricing">
      <div class="buf-pricing-inner">
        <h2 class="buf-h2 light">Grow your social presence with confidence</h2>
        <p class="buf-pricing-lede">
          Start free, invite your team when you’re ready, and scale publishing without the enterprise bloat.
        </p>
        <div class="buf-pricing-row">
          <NuxtLink class="btn buf-btn-brand buf-btn-lg" :to="localePath('/register')">Create your free workspace</NuxtLink>
          <NuxtLink class="btn secondary buf-btn-ghost-light" :to="localePath('/login')">Sign in</NuxtLink>
        </div>
        <p class="buf-pricing-foot">No credit card · Cancel anytime</p>
        <ul class="buf-pricing-points">
          <li>Free workspace to get started</li>
          <li>Per-channel queues &amp; slots</li>
          <li>Ideas board &amp; publishing in one app</li>
        </ul>
      </div>
    </section>

    <footer class="buf-footer">
      <div class="buf-footer-grid">
        <div>
          <NuxtLink :to="localePath('/')" class="buf-footer-brand">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.15"/>
              <circle cx="7" cy="12" r="2.2" fill="currentColor"/>
              <circle cx="17" cy="7" r="2.2" fill="currentColor"/>
              <circle cx="17" cy="17" r="2.2" fill="currentColor"/>
              <line x1="9" y1="11" x2="15" y2="8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              <line x1="9" y1="13" x2="15" y2="16" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
            Schedra
          </NuxtLink>
          <p class="muted buf-footer-tag">Plan, schedule, publish — in one calm workspace.</p>
        </div>
        <div>
          <h5 class="buf-foot-h">Product</h5>
          <NuxtLink :to="localePath('/') + '#buf-features'">Features</NuxtLink>
          <NuxtLink :to="localePath('/') + '#buf-channels'">Channels</NuxtLink>
          <NuxtLink :to="localePath('/') + '#buf-pricing'">Pricing</NuxtLink>
        </div>
        <div>
          <h5 class="buf-foot-h">Legal</h5>
          <NuxtLink :to="localePath('/chinh-sach-rieng-tu')">Chính sách quyền riêng tư</NuxtLink>
          <NuxtLink :to="localePath('/quy-dinh-su-dung')">Quy định sử dụng</NuxtLink>
          <NuxtLink :to="localePath('/tiktok-review')">TikTok integration</NuxtLink>
        </div>
        <div>
          <h5 class="buf-foot-h">Account</h5>
          <NuxtLink :to="localePath('/register')">Bắt đầu miễn phí</NuxtLink>
          <NuxtLink :to="localePath('/login')">Đăng nhập</NuxtLink>
        </div>
      </div>
      <p class="buf-copy">&copy; {{ new Date().getFullYear() }} Schedra. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
const localePath = useLocalePath()
const channelList = [
  { name: "Facebook", abbr: "f", cls: "facebook" },
  { name: "Instagram", abbr: "ig", cls: "instagram" },
  { name: "LinkedIn", abbr: "in", cls: "linkedin" },
  { name: "TikTok", abbr: "tt", cls: "tiktok" },
  { name: "YouTube", abbr: "yt", cls: "youtube" },
  { name: "Pinterest", abbr: "p", cls: "pinterest" },
]
</script>

<style scoped>
.buf-home {
  --buf-max: 1180px;
  --buf-pad: 32px;
  background:
    radial-gradient(1200px 520px at 50% -8%, rgba(127, 162, 147, 0.14), transparent 55%),
    radial-gradient(900px 400px at 100% 20%, rgba(230, 126, 34, 0.06), transparent 45%),
    var(--bg);
}

.muted {
  color: var(--muted);
}

/* Hero */
.buf-hero {
  max-width: var(--buf-max);
  margin: 0 auto;
  padding: 56px var(--buf-pad) 72px;
}

.buf-hero-grid {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 56px;
  align-items: center;
}

.buf-eyebrow {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 700;
  color: var(--brand-fill);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.buf-h1 {
  margin: 0;
  font-size: clamp(38px, 5.2vw, 64px);
  font-weight: 900;
  line-height: 1.04;
  letter-spacing: -0.03em;
  color: var(--ink);
}

.buf-lede {
  margin: 16px 0 0;
  font-size: clamp(17px, 2vw, 20px);
  line-height: 1.55;
  color: var(--muted);
  max-width: 520px;
}

.buf-emoji-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin-top: 20px;
  font-size: 22px;
  opacity: 0.92;
}

.buf-hero-cta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.buf-btn-brand {
  background: var(--brand-fill) !important;
  border-color: var(--brand-fill) !important;
  color: #fff !important;
  padding: 12px 22px !important;
  font-size: 15px !important;
  box-shadow: 0 10px 28px rgba(31, 75, 57, 0.28);
}

.buf-btn-brand:hover:not(:disabled) {
  background: var(--brand-fill-hover) !important;
  border-color: var(--brand-fill-hover) !important;
}

.buf-trust-micro {
  margin: 14px 0 0;
  font-size: 13px;
  color: var(--muted);
}

.buf-hero-visual {
  display: flex;
  justify-content: center;
}

.buf-mock-shell {
  width: 100%;
  max-width: 440px;
  border-radius: 22px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-strong);
  overflow: hidden;
}

.buf-mock-topbar {
  display: flex;
  gap: 7px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--surface-muted);
}

.buf-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.buf-dot.r { background: #ff5f57; }
.buf-dot.y { background: #febc2e; }
.buf-dot.g { background: #28c840; }

.buf-mock-body {
  display: flex;
  min-height: 240px;
}

.buf-mock-side {
  width: 56px;
  border-right: 1px solid var(--line);
  padding: 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.buf-nav-pill {
  height: 8px;
  border-radius: 4px;
  background: var(--line);
}
.buf-nav-pill.on {
  background: var(--brand-fill);
  width: 80%;
}

.buf-mock-main {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.buf-mock-toolbar {
  display: flex;
  gap: 8px;
}

.buf-pill {
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(127, 162, 147, 0.2);
  color: var(--brand-fill);
}
.buf-pill.ghost {
  background: var(--surface-muted);
  color: var(--muted);
}

.buf-mock-row {
  height: 48px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: var(--surface-muted);
}
.buf-mock-row.short {
  height: 36px;
  width: 72%;
}

.buf-mock-cal {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 6px;
  margin-top: 4px;
}

.buf-cal-cell {
  aspect-ratio: 1;
  border-radius: 8px;
  background: var(--surface-muted);
  border: 1px solid var(--line-soft);
}
.buf-cal-cell.hot {
  border-color: rgba(127, 162, 147, 0.45);
  background: rgba(127, 162, 147, 0.12);
}

/* Trust */
.buf-trust {
  border-top: 1px solid var(--line-soft);
  border-bottom: 1px solid var(--line-soft);
  background: var(--surface-muted);
  padding: 48px var(--buf-pad);
  text-align: center;
}

.buf-trust-heading {
  margin: 0 auto 28px;
  max-width: 640px;
  font-size: clamp(18px, 2.2vw, 22px);
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.02em;
}

.buf-trust-grid {
  max-width: 900px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
}

.buf-trust-cell {
  padding: 20px 16px;
  border-right: 1px solid var(--line-soft);
}
.buf-trust-cell:last-child {
  border-right: 0;
}

.buf-trust-num {
  font-size: clamp(40px, 5vw, 56px);
  font-weight: 900;
  letter-spacing: -0.04em;
  color: var(--brand-fill);
  line-height: 1;
}

.buf-trust-label {
  margin-top: 8px;
  font-size: 14px;
  color: var(--muted);
}

/* Sections */
.buf-block {
  max-width: var(--buf-max);
  margin: 0 auto;
  padding: 88px var(--buf-pad) 40px;
}

.buf-section-head {
  text-align: center;
  max-width: 720px;
  margin: 0 auto 56px;
}
.buf-section-head.tight {
  margin-bottom: 32px;
}

.buf-h2 {
  margin: 0;
  font-size: clamp(28px, 3.5vw, 44px);
  font-weight: 900;
  letter-spacing: -0.03em;
  line-height: 1.1;
  color: var(--ink);
}

.buf-h2.light {
  color: #f8fffb;
}

.buf-h2.buf-center {
  text-align: center;
  margin-left: auto;
  margin-right: auto;
}

.buf-subdeck {
  margin: 14px 0 0;
  font-size: 17px;
  line-height: 1.55;
}

.buf-feature-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  align-items: center;
  padding: 72px 0;
  border-top: 1px solid var(--line-soft);
}

.buf-feature-split.rev {
  direction: rtl;
}
.buf-feature-split.rev > * {
  direction: ltr;
}

.buf-tag {
  display: inline-block;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--brand-fill);
  margin-bottom: 10px;
}

.buf-h3 {
  margin: 0;
  font-size: clamp(24px, 2.8vw, 34px);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.15;
  color: var(--ink);
}

.buf-feature-copy p {
  margin: 14px 0 0;
  font-size: 16px;
  line-height: 1.65;
}

.buf-text-link {
  display: inline-block;
  margin-top: 18px;
  font-weight: 700;
  font-size: 15px;
  color: var(--brand-fill);
  text-decoration: none;
}
.buf-text-link:hover {
  color: var(--brand-fill-hover);
}

.buf-feature-shot {
  border-radius: 24px;
  padding: 40px 36px;
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.buf-shot-green {
  background: linear-gradient(145deg, rgba(127, 162, 147, 0.14), rgba(31, 75, 57, 0.06));
  border: 1px solid rgba(127, 162, 147, 0.22);
}

.buf-shot-blue {
  background: linear-gradient(145deg, rgba(59, 130, 246, 0.1), rgba(29, 78, 216, 0.05));
  border: 1px solid rgba(59, 130, 246, 0.18);
}

.buf-shot-warm {
  background: linear-gradient(145deg, rgba(230, 126, 34, 0.12), rgba(180, 90, 15, 0.05));
  border: 1px solid rgba(230, 126, 34, 0.2);
}

.buf-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  max-width: 300px;
}

.buf-mini-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-soft);
}

.buf-dot-s {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--brand-fill);
  flex-shrink: 0;
}

.buf-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.buf-lines i {
  display: block;
  height: 7px;
  border-radius: 4px;
  background: var(--line);
  width: 88%;
}
.buf-lines i.dim {
  width: 55%;
  opacity: 0.55;
}

.buf-mini-card em {
  font-style: normal;
  font-size: 11px;
  font-weight: 800;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--surface-muted);
  color: var(--muted);
}
.buf-mini-card em.ok {
  background: rgba(127, 162, 147, 0.2);
  color: var(--brand-fill);
}

.buf-queue {
  width: 100%;
  max-width: 320px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.buf-q-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.buf-q-row time {
  width: 52px;
  font-size: 12px;
  color: var(--muted);
  flex-shrink: 0;
}
.buf-badge {
  font-size: 11px;
  font-weight: 800;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--surface-muted);
  color: var(--muted);
}
.buf-badge.ok {
  background: rgba(127, 162, 147, 0.2);
  color: var(--brand-fill);
}
.buf-bar {
  flex: 1;
  height: 28px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--panel);
}
.buf-bar.sm {
  flex: 0.55;
}

.buf-editor {
  width: 100%;
  max-width: 300px;
  padding: 20px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-soft);
}

.buf-editor-lines {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.buf-editor-lines i {
  display: block;
  height: 8px;
  border-radius: 4px;
  background: var(--line);
}
.buf-editor-lines i:nth-child(1) { width: 100%; }
.buf-editor-lines i:nth-child(2) { width: 78%; }
.buf-editor-lines i:nth-child(3) { width: 52%; opacity: 0.5; }

.buf-editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 18px;
  align-items: center;
}
.buf-faux {
  font-size: 13px;
  color: var(--muted);
}
.buf-faux.primary {
  font-weight: 800;
  color: #fff;
  background: var(--brand-fill);
  padding: 8px 16px;
  border-radius: 999px;
}

/* More grid */
.buf-more-wrap {
  max-width: var(--buf-max);
  margin: 0 auto;
  padding: 40px var(--buf-pad) 80px;
}

.buf-more-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
}

.buf-more-card {
  padding: 22px 20px;
  border-radius: 18px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-soft);
}

.buf-more-card h4 {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 800;
  color: var(--ink);
}

.buf-more-card p {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
}

/* Channels */
.buf-channels-wrap {
  max-width: var(--buf-max);
  margin: 0 auto;
  padding: 0 var(--buf-pad) 88px;
  text-align: center;
}

.buf-channel-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 14px;
  margin-top: 8px;
}

.buf-ch-pill {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: var(--panel);
  font-weight: 700;
  font-size: 14px;
  color: var(--ink);
  box-shadow: var(--shadow-soft);
}

.buf-ch-ico {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 900;
  color: #fff;
}

.buf-ch-pill.facebook .buf-ch-ico { background: #1877f2; }
.buf-ch-pill.instagram .buf-ch-ico {
  background: linear-gradient(135deg, #f09433, #e6683c, #dc2743, #bc1888);
}
.buf-ch-pill.linkedin .buf-ch-ico { background: #0a66c2; }
.buf-ch-pill.tiktok .buf-ch-ico { background: #111; }
.buf-ch-pill.youtube .buf-ch-ico { background: #f00; }
.buf-ch-pill.pinterest .buf-ch-ico { background: #e60023; }

/* Audiences */
.buf-audiences {
  max-width: var(--buf-max);
  margin: 0 auto;
  padding: 0 var(--buf-pad) 88px;
}

.buf-aud-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-top: 36px;
}

.buf-aud-card {
  padding: 28px 24px;
  border-radius: 20px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-soft);
}

.buf-aud-card h4 {
  margin: 0 0 10px;
  font-size: 18px;
  font-weight: 800;
}

.buf-aud-card p {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
}

/* Quotes */
.buf-quotes {
  max-width: var(--buf-max);
  margin: 0 auto;
  padding: 0 var(--buf-pad) 88px;
}

.buf-quote-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
  margin-top: 36px;
}

.buf-quote {
  margin: 0;
  padding: 26px 22px;
  border-radius: 20px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow-soft);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.buf-quote blockquote {
  margin: 0;
  font-size: 15px;
  line-height: 1.65;
  color: var(--ink);
}

.buf-quote figcaption {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.buf-quote figcaption strong {
  display: block;
  color: var(--ink);
}

.buf-av {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--brand-fill);
  color: #fff;
  font-weight: 900;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

/* Pricing CTA */
.buf-pricing {
  padding: 88px var(--buf-pad);
  background: linear-gradient(135deg, #1a4d3a 0%, #13261b 48%, #1f4b39 100%);
}

.buf-pricing-inner {
  max-width: 720px;
  margin: 0 auto;
  text-align: center;
}

.buf-pricing-lede {
  margin: 16px 0 0;
  font-size: 17px;
  line-height: 1.6;
  color: rgba(248, 255, 251, 0.82);
}

.buf-pricing-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
  margin-top: 28px;
}

.buf-btn-lg {
  padding: 14px 28px !important;
  font-size: 16px !important;
}

.buf-btn-ghost-light {
  background: rgba(255, 255, 255, 0.1) !important;
  border-color: rgba(255, 255, 255, 0.28) !important;
  color: #f0faf5 !important;
}

.buf-btn-ghost-light:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.16) !important;
  border-color: rgba(255, 255, 255, 0.4) !important;
}

.buf-pricing-foot {
  margin: 16px 0 0;
  font-size: 14px;
  color: rgba(248, 255, 251, 0.65);
}

.buf-pricing-points {
  list-style: none;
  padding: 28px 0 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 10px 20px;
  justify-content: center;
  color: rgba(248, 255, 251, 0.78);
  font-size: 14px;
}

.buf-pricing-points li {
  padding-left: 18px;
  position: relative;
}
.buf-pricing-points li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.55em;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(127, 162, 147, 0.95);
}

/* Footer */
.buf-footer {
  border-top: 1px solid var(--line-soft);
  background: var(--panel);
  padding: 48px var(--buf-pad) 28px;
}

.buf-footer-grid {
  max-width: var(--buf-max);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr 1fr;
  gap: 32px;
}

.buf-footer-brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 900;
  font-size: 17px;
  color: var(--ink);
  text-decoration: none;
}

.buf-footer-tag {
  margin: 12px 0 0;
  font-size: 14px;
  line-height: 1.5;
  max-width: 260px;
}

.buf-foot-h {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.buf-footer-grid a {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--muted);
  text-decoration: none;
}
.buf-footer-grid a:hover {
  color: var(--ink);
}

.buf-copy {
  max-width: var(--buf-max);
  margin: 36px auto 0;
  padding-top: 20px;
  border-top: 1px solid var(--line-soft);
  font-size: 12px;
  color: var(--muted);
  text-align: center;
}

@media (max-width: 960px) {
  .buf-hero-grid {
    grid-template-columns: 1fr;
    gap: 40px;
  }

  .buf-feature-split,
  .buf-feature-split.rev {
    grid-template-columns: 1fr;
    direction: ltr;
    padding: 48px 0;
    gap: 28px;
  }

  .buf-trust-grid {
    grid-template-columns: 1fr;
  }

  .buf-trust-cell {
    border-right: 0;
    border-bottom: 1px solid var(--line-soft);
  }
  .buf-trust-cell:last-child {
    border-bottom: 0;
  }

  .buf-more-grid {
    grid-template-columns: 1fr 1fr;
  }

  .buf-aud-grid,
  .buf-quote-grid {
    grid-template-columns: 1fr;
  }

  .buf-footer-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 560px) {
  .buf-home {
    --buf-pad: 18px;
  }

  .buf-hero-cta,
  .buf-pricing-row {
    flex-direction: column;
    align-items: stretch;
  }

  .buf-more-grid {
    grid-template-columns: 1fr;
  }

  .buf-footer-grid {
    grid-template-columns: 1fr;
  }
}
</style>
