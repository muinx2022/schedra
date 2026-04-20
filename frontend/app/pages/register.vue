<script setup lang="ts">
const form = reactive({
  full_name: "",
  workspace_name: "",
  email: "",
  password: "",
})
const error = ref("")

async function submit() {
  error.value = ""
  try {
    await apiFetch("/auth/register/", { method: "POST", body: form })
    await navigateTo("/app")
  } catch (err: any) {
    error.value = extractApiError(err, "Registration failed.")
  }
}
</script>

<template>
  <div class="page">
    <div class="card stack" style="max-width: 560px; margin: 0 auto">
      <h1>Create workspace</h1>
      <div class="field">
        <label>Full name</label>
        <input v-model="form.full_name" />
      </div>
      <div class="field">
        <label>Workspace name</label>
        <input v-model="form.workspace_name" />
      </div>
      <div class="field">
        <label>Email</label>
        <input v-model="form.email" type="email" />
      </div>
      <div class="field">
        <label>Password</label>
        <input v-model="form.password" type="password" />
      </div>
      <button class="btn" @click="submit">Create account</button>
      <p v-if="error" class="muted">{{ error }}</p>
    </div>
  </div>
</template>
