<template>
  <div class="home">

    <!-- ── HERO ─────────────────────────────────────── -->
    <section class="hp-hero">
      <div class="hp-hero-inner">
        <span class="hp-eyebrow">Social media publishing — simplified</span>
        <h1 class="hp-headline">Your social media workspace</h1>
        <p class="hp-subline">
          Plan content, schedule posts, and grow your audience —
          without the chaos.
        </p>
        <div class="hp-cta-row">
          <NuxtLink class="btn hp-cta-primary" to="/register">Get started free</NuxtLink>
          <NuxtLink class="btn secondary" to="/login">Sign in</NuxtLink>
        </div>
        <p class="hp-trust">No credit card needed · Free to get started</p>
      </div>

      <div class="hp-hero-visual">
        <div class="hp-mock-shell">
          <div class="hp-mock-topbar">
            <div class="hp-mock-dot r"></div>
            <div class="hp-mock-dot y"></div>
            <div class="hp-mock-dot g"></div>
          </div>
          <div class="hp-mock-body">
            <div class="hp-mock-sidebar">
              <div class="hp-mock-nav-item active"></div>
              <div class="hp-mock-nav-item"></div>
              <div class="hp-mock-nav-item"></div>
              <div class="hp-mock-nav-item"></div>
              <div class="hp-mock-nav-item"></div>
            </div>
            <div class="hp-mock-content">
              <div class="hp-mock-card"></div>
              <div class="hp-mock-card short"></div>
              <div class="hp-mock-card"></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── FEATURE 1 — IDEAS ─────────────────────────── -->
    <section class="hp-feature">
      <div class="hp-feature-text">
        <span class="hp-feature-label">Ideas</span>
        <h2>Capture ideas before they slip away</h2>
        <p class="muted">
          Keep a running board of content ideas organised by status —
          Inbox, Planned, and Ready. Move cards through your workflow
          as ideas become posts.
        </p>
        <NuxtLink to="/register" class="hp-link">Start capturing ideas &rarr;</NuxtLink>
      </div>

      <div class="hp-feature-visual accent-green">
        <div class="hp-feature-card-group">
          <div class="hp-fcard">
            <div class="hp-fcard-dot"></div>
            <div class="hp-fcard-lines">
              <div class="hp-line w80"></div>
              <div class="hp-line w55 muted-line"></div>
            </div>
            <div class="hp-fcard-tag">Planned</div>
          </div>
          <div class="hp-fcard">
            <div class="hp-fcard-dot"></div>
            <div class="hp-fcard-lines">
              <div class="hp-line w65"></div>
              <div class="hp-line w40 muted-line"></div>
            </div>
            <div class="hp-fcard-tag ready">Ready</div>
          </div>
          <div class="hp-fcard">
            <div class="hp-fcard-dot"></div>
            <div class="hp-fcard-lines">
              <div class="hp-line w90"></div>
              <div class="hp-line w50 muted-line"></div>
            </div>
            <div class="hp-fcard-tag">Inbox</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── FEATURE 2 — QUEUE (reversed) ─────────────── -->
    <section class="hp-feature reverse">
      <div class="hp-feature-text">
        <span class="hp-feature-label">Queue</span>
        <h2>Schedule posts with a click</h2>
        <p class="muted">
          Fill your queue with scheduled content across channels.
          Each channel runs on its own publishing rhythm — set it
          up once and let it run.
        </p>
        <NuxtLink to="/register" class="hp-link">Set up your queue &rarr;</NuxtLink>
      </div>

      <div class="hp-feature-visual accent-blue">
        <div class="hp-queue-mock">
          <div class="hp-queue-row">
            <div class="hp-queue-time">9:00 AM</div>
            <div class="hp-queue-pill green">Scheduled</div>
            <div class="hp-queue-bar"></div>
          </div>
          <div class="hp-queue-row">
            <div class="hp-queue-time">12:00 PM</div>
            <div class="hp-queue-pill">Draft</div>
            <div class="hp-queue-bar short"></div>
          </div>
          <div class="hp-queue-row">
            <div class="hp-queue-time">3:30 PM</div>
            <div class="hp-queue-pill green">Scheduled</div>
            <div class="hp-queue-bar"></div>
          </div>
          <div class="hp-queue-row">
            <div class="hp-queue-time">6:00 PM</div>
            <div class="hp-queue-pill">Draft</div>
            <div class="hp-queue-bar short"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── FEATURE 3 — PUBLISH ──────────────────────── -->
    <section class="hp-feature">
      <div class="hp-feature-text">
        <span class="hp-feature-label">Publish</span>
        <h2>Go from draft to live in seconds</h2>
        <p class="muted">
          Write, preview, and publish to Meta channels directly from
          your workspace. Schedule for later or hit publish right now
          — your call.
        </p>
        <NuxtLink to="/register" class="hp-link">Start publishing &rarr;</NuxtLink>
      </div>

      <div class="hp-feature-visual accent-orange">
        <div class="hp-publish-mock">
          <div class="hp-publish-editor">
            <div class="hp-line w90"></div>
            <div class="hp-line w70 mt8"></div>
            <div class="hp-line w50 mt8 muted-line"></div>
          </div>
          <div class="hp-publish-actions">
            <div class="hp-publish-btn-ghost">Save draft</div>
            <div class="hp-publish-btn-primary">Publish now</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── STATS ─────────────────────────────────────── -->
    <section class="hp-stats">
      <div class="hp-stat">
        <div class="hp-stat-number">3</div>
        <div class="hp-stat-label">core workflows</div>
      </div>
      <div class="hp-stat">
        <div class="hp-stat-number">1</div>
        <div class="hp-stat-label">unified workspace</div>
      </div>
      <div class="hp-stat">
        <div class="hp-stat-number">0</div>
        <div class="hp-stat-label">credit cards needed</div>
      </div>
    </section>

    <!-- ── CHANNELS ───────────────────────────────────── -->
    <section class="hp-channels">
      <h2 class="hp-section-title">Built for Meta channels</h2>
      <p class="hp-section-sub muted">
        Connect your Facebook Pages and manage everything from one place.
      </p>
      <div class="hp-channel-badges">
        <div class="hp-channel-badge facebook">
          <span class="hp-channel-icon">f</span>
          Facebook Pages
        </div>
        <div class="hp-channel-badge instagram">
          <span class="hp-channel-icon">ig</span>
          Instagram
        </div>
      </div>
    </section>

    <!-- ── TESTIMONIALS ───────────────────────────────── -->
    <section class="hp-testimonials">
      <h2 class="hp-section-title">Built for small teams who want more signal, less noise</h2>
      <div class="hp-testimonial-grid">
        <div class="hp-testimonial-card">
          <p class="hp-testimonial-quote">
            "Finally a publishing tool that doesn't get in the way.
            I go from idea to post in under 2 minutes."
          </p>
          <div class="hp-testimonial-author">
            <div class="hp-testimonial-avatar">S</div>
            <div>
              <div class="hp-testimonial-name">Sarah K.</div>
              <div class="hp-testimonial-role muted">Freelance Content Creator</div>
            </div>
          </div>
        </div>
        <div class="hp-testimonial-card">
          <p class="hp-testimonial-quote">
            "The kanban idea board alone is worth it. My content
            calendar has never been this organised."
          </p>
          <div class="hp-testimonial-author">
            <div class="hp-testimonial-avatar">M</div>
            <div>
              <div class="hp-testimonial-name">Marcus T.</div>
              <div class="hp-testimonial-role muted">Small Business Owner</div>
            </div>
          </div>
        </div>
        <div class="hp-testimonial-card">
          <p class="hp-testimonial-quote">
            "Exactly the lightweight Buffer alternative I was looking
            for. Clean, fast, focused."
          </p>
          <div class="hp-testimonial-author">
            <div class="hp-testimonial-avatar">L</div>
            <div>
              <div class="hp-testimonial-name">Linh N.</div>
              <div class="hp-testimonial-role muted">Social Media Manager</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── FINAL CTA ──────────────────────────────────── -->
    <section class="hp-final-cta">
      <h2 class="hp-cta-headline">Ready to simplify your social media?</h2>
      <p class="muted">
        Join teams using Schedra to plan, schedule, and publish content
        — without the overhead.
      </p>
      <div class="hp-cta-row center">
        <NuxtLink class="btn hp-cta-primary large" to="/register">
          Create your free workspace
        </NuxtLink>
      </div>
      <p class="hp-trust">No credit card. Cancel anytime.</p>
    </section>

    <!-- ── FOOTER ─────────────────────────────────────── -->
    <footer class="hp-footer">
      <div class="hp-footer-inner">
        <NuxtLink to="/" class="hp-footer-brand">
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
        <nav class="hp-footer-links">
          <NuxtLink to="/chinh-sach-rieng-tu">Chính sách quyền riêng tư</NuxtLink>
          <NuxtLink to="/quy-dinh-su-dung">Quy định sử dụng</NuxtLink>
          <NuxtLink to="/register">Bắt đầu miễn phí</NuxtLink>
          <NuxtLink to="/login">Đăng nhập</NuxtLink>
        </nav>
        <p class="hp-footer-copy">&copy; {{ new Date().getFullYear() }} Schedra. All rights reserved.</p>
      </div>
    </footer>

  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
}

/* ── HERO ────────────────────────────────────────────── */
.hp-hero {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  align-items: center;
  max-width: 1160px;
  margin: 0 auto;
  padding: 80px 32px 96px;
}

.hp-hero-inner {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hp-eyebrow {
  display: inline-block;
  border: 1px solid var(--brand-outline);
  border-radius: 999px;
  padding: 4px 14px;
  color: var(--brand);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.02em;
  width: fit-content;
}

.hp-headline {
  margin: 0;
  font-size: clamp(36px, 5vw, 58px);
  font-weight: 900;
  line-height: 1.06;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.hp-subline {
  margin: 0;
  font-size: 18px;
  line-height: 1.6;
  color: var(--muted);
  max-width: 480px;
}

.hp-cta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.hp-cta-row.center {
  justify-content: center;
}

.hp-cta-primary {
  background: var(--brand-fill) !important;
  border-color: var(--brand-fill) !important;
  color: #fff !important;
  padding: 12px 24px;
  font-size: 15px;
}

.hp-cta-primary:hover:not(:disabled) {
  background: var(--brand-fill-hover) !important;
  border-color: var(--brand-fill-hover) !important;
}

.hp-cta-primary.large {
  padding: 14px 32px;
  font-size: 16px;
}

.hp-trust {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

/* ── HERO VISUAL (mock UI) ───────────────────────────── */
.hp-hero-visual {
  display: flex;
  justify-content: center;
}

.hp-mock-shell {
  width: 100%;
  max-width: 460px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: var(--panel);
  box-shadow: var(--shadow-strong);
  overflow: hidden;
}

.hp-mock-topbar {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--surface-muted);
}

.hp-mock-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.hp-mock-dot.r { background: #ff5f57; }
.hp-mock-dot.y { background: #febc2e; }
.hp-mock-dot.g { background: #28c840; }

.hp-mock-body {
  display: flex;
  min-height: 220px;
}

.hp-mock-sidebar {
  width: 64px;
  border-right: 1px solid var(--line);
  padding: 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.hp-mock-nav-item {
  height: 8px;
  border-radius: 4px;
  background: var(--line);
}

.hp-mock-nav-item.active {
  background: var(--brand-fill);
  width: 70%;
}

.hp-mock-content {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hp-mock-card {
  height: 52px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--surface-muted);
}

.hp-mock-card.short {
  height: 36px;
}

/* ── FEATURES ────────────────────────────────────────── */
.hp-feature {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 80px;
  align-items: center;
  max-width: 1160px;
  margin: 0 auto;
  padding: 80px 32px;
  border-top: 1px solid var(--line-soft);
  width: 100%;
}

.hp-feature.reverse {
  direction: rtl;
}

.hp-feature.reverse > * {
  direction: ltr;
}

.hp-feature-label {
  display: inline-block;
  margin-bottom: 8px;
  border-radius: 999px;
  padding: 3px 12px;
  background: rgba(127, 162, 147, 0.14);
  color: var(--brand);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hp-feature-text {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hp-feature-text h2 {
  margin: 0;
  font-size: clamp(26px, 3.5vw, 38px);
  font-weight: 800;
  line-height: 1.12;
  letter-spacing: -0.015em;
  color: var(--ink);
}

.hp-feature-text p {
  margin: 0;
  font-size: 16px;
  line-height: 1.65;
}

.hp-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--brand-fill);
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
  transition: color 0.12s;
}

.hp-link:hover {
  color: var(--brand-fill-hover);
}

/* ── FEATURE VISUALS ─────────────────────────────────── */
.hp-feature-visual {
  border-radius: 24px;
  padding: 36px;
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hp-feature-visual.accent-green {
  background: linear-gradient(140deg, rgba(127, 162, 147, 0.12), rgba(63, 139, 110, 0.08));
  border: 1px solid rgba(127, 162, 147, 0.2);
}

.hp-feature-visual.accent-blue {
  background: linear-gradient(140deg, rgba(59, 130, 246, 0.08), rgba(29, 78, 216, 0.05));
  border: 1px solid rgba(59, 130, 246, 0.15);
}

.hp-feature-visual.accent-orange {
  background: linear-gradient(140deg, rgba(230, 126, 34, 0.1), rgba(180, 90, 15, 0.06));
  border: 1px solid rgba(230, 126, 34, 0.18);
}

/* Idea cards mock */
.hp-feature-card-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  max-width: 320px;
}

.hp-fcard {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
  box-shadow: var(--shadow-soft);
}

.hp-fcard-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--brand);
  flex-shrink: 0;
}

.hp-fcard-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hp-line {
  height: 7px;
  border-radius: 4px;
  background: var(--line);
}

.hp-line.muted-line { opacity: 0.5; }
.hp-line.w90 { width: 90%; }
.hp-line.w80 { width: 80%; }
.hp-line.w70 { width: 70%; }
.hp-line.w65 { width: 65%; }
.hp-line.w55 { width: 55%; }
.hp-line.w50 { width: 50%; }
.hp-line.w40 { width: 40%; }
.hp-line.mt8 { margin-top: 8px; }

.hp-fcard-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-muted);
  color: var(--muted);
  white-space: nowrap;
}

.hp-fcard-tag.ready {
  background: rgba(127, 162, 147, 0.18);
  color: var(--brand-fill);
}

/* Queue mock */
.hp-queue-mock {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  max-width: 340px;
}

.hp-queue-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hp-queue-time {
  font-size: 12px;
  color: var(--muted);
  width: 64px;
  flex-shrink: 0;
}

.hp-queue-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--surface-muted);
  color: var(--muted);
  white-space: nowrap;
}

.hp-queue-pill.green {
  background: rgba(127, 162, 147, 0.18);
  color: var(--brand-fill);
}

.hp-queue-bar {
  flex: 1;
  height: 28px;
  border-radius: 8px;
  background: var(--panel);
  border: 1px solid var(--line);
}

.hp-queue-bar.short {
  flex: 0.5;
}

/* Publish mock */
.hp-publish-mock {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
  max-width: 320px;
  padding: 20px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--panel);
  box-shadow: var(--shadow-soft);
}

.hp-publish-editor {
  display: flex;
  flex-direction: column;
}

.hp-publish-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
}

.hp-publish-btn-ghost {
  font-size: 13px;
  color: var(--muted);
  cursor: default;
}

.hp-publish-btn-primary {
  font-size: 13px;
  font-weight: 700;
  padding: 8px 16px;
  border-radius: 999px;
  background: var(--brand-fill);
  color: #fff;
  cursor: default;
}

/* ── STATS ───────────────────────────────────────────── */
.hp-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  border-top: 1px solid var(--line-soft);
  border-bottom: 1px solid var(--line-soft);
  background: var(--surface-muted);
  width: 100%;
}

.hp-stat {
  padding: 52px 32px;
  text-align: center;
  border-right: 1px solid var(--line-soft);
}

.hp-stat:last-child {
  border-right: 0;
}

.hp-stat-number {
  font-size: 56px;
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.03em;
  color: var(--brand-fill);
}

.hp-stat-label {
  margin-top: 6px;
  font-size: 14px;
  color: var(--muted);
}

/* ── CHANNELS ────────────────────────────────────────── */
.hp-channels {
  max-width: 800px;
  margin: 0 auto;
  padding: 80px 32px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  width: 100%;
}

.hp-section-title {
  margin: 0;
  font-size: clamp(24px, 3vw, 36px);
  font-weight: 800;
  letter-spacing: -0.015em;
  line-height: 1.15;
  color: var(--ink);
}

.hp-section-sub {
  margin: -8px 0 0;
  font-size: 16px;
  line-height: 1.6;
}

.hp-channel-badges {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  justify-content: center;
}

.hp-channel-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--panel);
  box-shadow: var(--shadow-soft);
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
}

.hp-channel-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 900;
  color: #fff;
}

.hp-channel-badge.facebook .hp-channel-icon {
  background: #1877f2;
}

.hp-channel-badge.instagram .hp-channel-icon {
  background: linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
}

/* ── TESTIMONIALS ────────────────────────────────────── */
.hp-testimonials {
  max-width: 1160px;
  margin: 0 auto;
  padding: 80px 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 40px;
  border-top: 1px solid var(--line-soft);
  text-align: center;
  width: 100%;
}

.hp-testimonial-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  width: 100%;
  text-align: left;
}

.hp-testimonial-card {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 28px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: var(--panel);
  box-shadow: var(--shadow-soft);
}

.hp-testimonial-quote {
  margin: 0;
  font-size: 15px;
  line-height: 1.65;
  color: var(--ink);
  flex: 1;
}

.hp-testimonial-author {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hp-testimonial-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--brand-fill);
  color: #fff;
  font-size: 14px;
  font-weight: 800;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.hp-testimonial-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
}

.hp-testimonial-role {
  font-size: 12px;
}

/* ── FINAL CTA ───────────────────────────────────────── */
.hp-final-cta {
  text-align: center;
  padding: 96px 32px 80px;
  border-top: 1px solid var(--line-soft);
  background: var(--surface-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.hp-cta-headline {
  margin: 0;
  font-size: clamp(28px, 4vw, 46px);
  font-weight: 900;
  letter-spacing: -0.02em;
  line-height: 1.1;
  color: var(--ink);
  max-width: 680px;
}

.hp-final-cta p.muted {
  margin: 0;
  font-size: 16px;
  max-width: 480px;
}

/* ── RESPONSIVE ──────────────────────────────────────── */
@media (max-width: 900px) {
  .hp-hero,
  .hp-feature {
    grid-template-columns: 1fr;
    gap: 40px;
    padding: 56px 20px;
  }

  .hp-feature.reverse {
    direction: ltr;
  }

  .hp-feature-visual {
    padding: 28px;
    min-height: auto;
  }

  .hp-stats {
    grid-template-columns: 1fr;
  }

  .hp-stat {
    border-right: 0;
    border-bottom: 1px solid var(--line-soft);
    padding: 36px 24px;
  }

  .hp-stat:last-child {
    border-bottom: 0;
  }

  .hp-channels,
  .hp-testimonials {
    padding: 60px 20px;
  }

  .hp-testimonial-grid {
    grid-template-columns: 1fr;
  }

  .hp-final-cta {
    padding: 72px 20px 60px;
  }
}

@media (max-width: 520px) {
  .hp-hero {
    padding: 40px 16px 56px;
  }

  .hp-cta-row {
    flex-direction: column;
    align-items: stretch;
  }

  .hp-cta-row .btn {
    text-align: center;
  }

  .hp-channel-badges {
    flex-direction: column;
    align-items: stretch;
  }
}

/* ── FOOTER ──────────────────────────────────────────── */
.hp-footer {
  border-top: 1px solid var(--line-soft);
  background: var(--panel);
  width: 100%;
}

.hp-footer-inner {
  max-width: 1160px;
  margin: 0 auto;
  padding: 32px 32px 28px;
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.hp-footer-brand {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 15px;
  font-weight: 800;
  color: var(--ink);
  letter-spacing: -0.01em;
}

.hp-footer-links {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.hp-footer-links a {
  font-size: 13px;
  color: var(--muted);
  transition: color 0.12s;
}

.hp-footer-links a:hover {
  color: var(--ink);
}

.hp-footer-copy {
  margin: 0 0 0 auto;
  font-size: 12px;
  color: var(--muted);
}

@media (max-width: 640px) {
  .hp-footer-inner {
    padding: 24px 16px;
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .hp-footer-copy {
    margin: 0;
  }
}
</style>
