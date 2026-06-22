<script setup lang="ts">
import { useCounterStore } from '@/stores/counter'

const counter = useCounterStore()
</script>

<template>
  <div class="about">
    <h1>About Page</h1>
    <p>This is a Vue 3 project with:</p>
    <ul>
      <li>Vite — build tool</li>
      <li>Vue Router — routing</li>
      <li>Pinia — state management</li>
      <li>TypeScript — type safety</li>
    </ul>

    <div class="counter-demo">
      <h2>Pinia Counter Demo</h2>
      <p class="count">
        Count: {{ counter.count }}
      </p>
      <p class="double">
        Double: {{ counter.doubleCount }}
      </p>
      <div class="buttons">
        <button @click="counter.decrement">
          −
        </button>
        <button @click="counter.increment">
          +
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.about {
  max-width: 600px;
  margin: 0 auto;
  padding-top: 2rem;
}

h1 {
  color: #42b883;
}

ul {
  text-align: left;
  margin: 1rem 0;
  padding-left: 1.5rem;
}

li {
  margin: 0.3rem 0;
}

.counter-demo {
  margin-top: 2rem;
  padding: 1.5rem;
  background: #1a1a2e;
  border-radius: 8px;
}

.count {
  font-size: 1.5rem;
  font-weight: bold;
}

.double {
  color: #42b883;
  margin-bottom: 1rem;
}

.buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

button {
  width: 48px;
  height: 48px;
  border: none;
  border-radius: 8px;
  background: #42b883;
  color: #fff;
  font-size: 1.5rem;
  cursor: pointer;
  transition: background 0.2s;
}

button:hover {
  background: #35a06b;
}
</style>
