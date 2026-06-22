<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  msg: string
}>()

const count = ref(0)
</script>

<template>
  <div class="hello-world">
    <h2>{{ msg }}</h2>

    <div class="card">
      <button
        type="button"
        @click="count++"
      >
        Count is {{ count }}
      </button>
      <p>
        Edit <code>src/components/HelloWorld.vue</code> to test HMR
      </p>
    </div>

    <p class="read-the-docs">
      Click the buttons above to learn more
    </p>
  </div>
</template>

<style scoped>
.hello-world {
  margin-top: 2rem;
}

h2 {
  font-size: 1.3rem;
  margin-bottom: 1rem;
}

.card {
  padding: 1.5rem;
}

button {
  padding: 0.5rem 1.5rem;
  border: 1px solid #42b883;
  border-radius: 8px;
  background: transparent;
  color: #42b883;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

button:hover {
  background: #42b883;
  color: #fff;
}

code {
  background: #1a1a2e;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.read-the-docs {
  color: #888;
  margin-top: 1rem;
}
</style>
