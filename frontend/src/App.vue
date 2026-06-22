<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header>
    <nav>
      <RouterLink to="/">
        Home
      </RouterLink>
      <RouterLink to="/about">
        About
      </RouterLink>
    </nav>
  </header>

  <main>
    <RouterView />
  </main>
</template>

<style scoped>
header {
  padding: 1rem 2rem;
  background: #1a1a2e;
}

nav {
  display: flex;
  gap: 1.5rem;
}

nav a {
  color: #e0e0e0;
  text-decoration: none;
  font-weight: 500;
  padding: 0.3rem 0;
  border-bottom: 2px solid transparent;
  transition: border-color 0.2s;
}

nav a:hover,
nav a.router-link-active {
  border-bottom-color: #42b883;
}

main {
  min-height: calc(100vh - 60px);
  padding: 2rem;
}
</style>
