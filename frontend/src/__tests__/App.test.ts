import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia } from 'pinia'
import App from '@/App.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/plan', component: { template: '<div>Plan</div>' } },
    { path: '/companion', component: { template: '<div>Companion</div>' } },
    { path: '/blog', component: { template: '<div>Blog</div>' } },
  ],
})

describe('App', () => {
  it('renders the brand name', async () => {
    router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
      },
    })

    expect(wrapper.text()).toContain('AgenticTour')
    expect(wrapper.find('header').exists()).toBe(true)
  })

  it('has navigation links', async () => {
    router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
      },
    })

    const links = wrapper.findAll('nav a')
    expect(links.length).toBeGreaterThanOrEqual(3)
  })
})
