import type { RouterConfig } from "@nuxt/schema"

export default <RouterConfig>{
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) {
      return { el: to.hash, top: 80, behavior: "smooth" }
    }
    return { top: 0 }
  },
}
