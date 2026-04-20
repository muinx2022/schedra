<template>
  <div class="page stack">
    <section class="hero">
      <div class="stack">
        <p class="muted">Meta-first publishing for small teams.</p>
        <h1>Plan ideas, queue posts, and ship a lighter Buffer workflow.</h1>
        <p class="muted">
          Buffer-lite v1 combines a basic public site with one authenticated workspace, a kanban idea board,
          image-first posting, and Meta channel connection.
        </p>
        <div class="nav">
          <NuxtLink class="btn" to="/register">Create workspace</NuxtLink>
          <NuxtLink class="btn secondary" to="/login">Sign in</NuxtLink>
        </div>
      </div>
      <div class="card stack">
        <strong>V1 includes</strong>
        <span>Ideas board with Inbox / Planned / Ready</span>
        <span>Meta channel connection flow</span>
        <span>Draft, queue, schedule, publish now</span>
        <span>Image-first media support</span>
      </div>
    </section>

    <section class="grid three">
      <article class="card stack">
        <strong>Ideas</strong>
        <span class="muted">Capture rough content before it becomes a post.</span>
      </article>
      <article class="card stack">
        <strong>Queue</strong>
        <span class="muted">Per-channel slots keep each channel on its own publishing rhythm.</span>
      </article>
      <article class="card stack">
        <strong>Publish</strong>
        <span class="muted">Go from draft to scheduled or immediate publish without leaving the workspace.</span>
      </article>
    </section>
  </div>
</template>
