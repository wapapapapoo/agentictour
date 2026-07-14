<script setup lang="ts">
import { computed, ref } from 'vue'
import { api, type KnowledgeSearchResult } from '@/services/api'

const keyword = ref('')
const loading = ref(false)
const searched = ref(false)
const error = ref('')
const results = ref<KnowledgeSearchResult[]>([])
const suggestions = ['杭州三日慢游', '北京人文街巷', '上海到成都美食', '周末自然风光']

const resultLabel = computed(() => searched.value ? `找到 ${results.value.length} 条相关行程` : '输入目的地、主题或玩法开始检索')

function scoreLabel(score: number) {
  return `${Math.max(0, Math.min(100, Math.round(score * 100)))}% 匹配`
}

async function search(value = keyword.value) {
  const query = value.trim()
  if (!query || loading.value) return
  keyword.value = query
  loading.value = true
  searched.value = true
  error.value = ''
  try {
    results.value = (await api.searchKnowledge(query)).results
  } catch (cause) {
    results.value = []
    error.value = cause instanceof Error ? cause.message : '暂时无法检索行程，请稍后重试。'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="search-page">
    <section class="search-hero">
      <p class="eyebrow">TRIP LIBRARY · EXPLORE</p>
      <h1>从别人的旅程里，找到你的下一站。</h1>
      <p>检索已同步到旅行知识库的真实行程，按城市、兴趣、玩法或关键词发现灵感。</p>
      <form class="search-box" @submit.prevent="search()">
        <span aria-hidden="true">⌕</span>
        <input v-model="keyword" maxlength="100" placeholder="例如：杭州咖啡、人文街巷、三天两晚" aria-label="搜索行程关键词">
        <button :disabled="loading || !keyword.trim()">{{ loading ? '正在检索…' : '搜索行程' }}</button>
      </form>
      <div class="suggestions">
        <span>试试搜索</span>
        <button v-for="item in suggestions" :key="item" type="button" @click="search(item)">{{ item }}</button>
      </div>
    </section>

    <section class="results-section" aria-live="polite">
      <div class="results-head"><div><p class="eyebrow">KNOWLEDGE RESULTS</p><h2>{{ resultLabel }}</h2></div><span v-if="searched" class="result-note">来源：旅行知识库</span></div>
      <p v-if="error" class="error">{{ error }}</p>
      <div v-else-if="loading" class="result-grid"><div v-for="item in 3" :key="item" class="skeleton"><i /><i /><i /></div></div>
      <div v-else-if="results.length" class="result-grid">
        <article v-for="(item, index) in results" :key="`${item.document_id}-${index}`" class="result-card">
          <div class="card-top"><span class="rank">{{ String(index + 1).padStart(2, '0') }}</span><span class="score">{{ scoreLabel(item.score) }}</span></div>
          <h3>{{ item.plan_title || '旅行行程片段' }}</h3>
          <p class="content">{{ item.chunk_content }}</p>
          <footer><span v-if="item.plan_id">行程编号 #{{ item.plan_id }}</span><span v-else>知识库行程</span><span>·</span><span>内容匹配结果</span></footer>
        </article>
      </div>
      <div v-else-if="searched" class="empty"><div>⌁</div><h3>没有找到匹配行程</h3><p>换一个更具体的城市、天数或旅行偏好试试。</p></div>
      <div v-else class="empty initial"><div>✦</div><h3>旅行灵感，等你发现</h3><p>知识库会依据行程内容而不是固定标签，为你匹配相关旅行经验。</p></div>
    </section>
  </div>
</template>

<style scoped>
.search-page{max-width:1180px;margin:0 auto;padding:42px 26px 74px}.search-hero{padding:48px clamp(22px,6vw,72px);border:1px solid #dcebdd;border-radius:28px;background:radial-gradient(circle at 83% 18%,rgba(156,217,177,.3),transparent 28%),linear-gradient(120deg,#fffdf8,#edf8f0);text-align:center}.eyebrow{margin:0 0 9px;color:#579379;font-size:11px;font-weight:800;letter-spacing:.14em}.search-hero h1{max-width:700px;margin:0 auto;color:#264a3a;font:700 clamp(29px,4.2vw,45px)/1.3 'Noto Serif SC','Microsoft YaHei',serif}.search-hero>p:last-of-type{max-width:590px;margin:14px auto 26px;color:#6c8075;font-size:14px;line-height:1.8}.search-box{display:flex;max-width:720px;margin:auto;align-items:center;gap:10px;border:1px solid #d7e8dc;border-radius:15px;padding:7px 8px 7px 17px;background:#fff;box-shadow:0 15px 28px rgba(40,92,65,.1)}.search-box>span{color:#4b8c6b;font-size:25px;line-height:1}.search-box input{width:100%;border:0;outline:0;color:#2e493d;font:14px 'Microsoft YaHei',sans-serif}.search-box input::placeholder{color:#a5b2aa}.search-box button{flex:none;border:0;border-radius:10px;padding:11px 17px;background:#2e7b5d;color:#fff;font-weight:700;cursor:pointer}.search-box button:disabled{opacity:.6;cursor:wait}.suggestions{display:flex;justify-content:center;flex-wrap:wrap;gap:8px;margin-top:17px;color:#76877e;font-size:12px}.suggestions button{border:1px solid #d7e7db;border-radius:999px;padding:5px 9px;background:rgba(255,255,255,.72);color:#4f7662;cursor:pointer}.suggestions button:hover{border-color:#93c4a4;background:#fff}.results-section{padding-top:34px}.results-head{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:17px}.results-head .eyebrow{margin-bottom:5px}.results-head h2{margin:0;color:#315143;font-size:20px}.result-note{color:#8a9a91;font-size:12px}.result-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.result-card{display:flex;min-height:255px;flex-direction:column;border:1px solid #e0eae2;border-radius:17px;padding:19px;background:#fff;box-shadow:0 10px 28px rgba(39,91,66,.055);transition:transform .2s,box-shadow .2s}.result-card:hover{transform:translateY(-3px);box-shadow:0 16px 34px rgba(39,91,66,.11)}.card-top{display:flex;justify-content:space-between;align-items:center}.rank{color:#91a99a;font:700 12px monospace;letter-spacing:.06em}.score{border-radius:999px;padding:5px 8px;background:#eef8f0;color:#4c8a67;font-size:11px;font-weight:700}.result-card h3{margin:16px 0 10px;color:#2f5141;font-size:17px}.content{display:-webkit-box;overflow:hidden;margin:0;color:#66796e;font-size:13px;line-height:1.8;-webkit-box-orient:vertical;-webkit-line-clamp:6;white-space:pre-line}.result-card footer{display:flex;gap:5px;margin-top:auto;padding-top:15px;color:#96a49d;font-size:11px}.empty{padding:62px 20px;border:1px dashed #d7e7dc;border-radius:18px;background:#fbfdfb;text-align:center}.empty>div{color:#75a68a;font-size:32px}.empty h3{margin:10px 0 6px;color:#456354;font-size:17px}.empty p{margin:0;color:#819087;font-size:13px}.initial{background:linear-gradient(135deg,#fbfefb,#f1faf3)}.error{border:1px solid #f2d7d3;border-radius:12px;padding:12px;background:#fff7f5;color:#ab4f4f;font-size:13px}.skeleton{min-height:255px;border-radius:17px;padding:20px;background:linear-gradient(100deg,#f2f6f3 25%,#fafcfb 40%,#f2f6f3 55%);background-size:200% 100%;animation:loading 1.2s infinite}.skeleton i{display:block;width:75%;height:13px;margin-bottom:15px;border-radius:999px;background:#e6eee8}.skeleton i:nth-child(2){width:90%;height:48px}.skeleton i:nth-child(3){width:48%}@keyframes loading{to{background-position:-200% 0}}@media(max-width:850px){.result-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:620px){.search-page{padding:26px 16px 50px}.search-hero{padding:34px 18px}.search-box{flex-wrap:wrap;padding:10px 12px}.search-box input{min-height:30px}.search-box button{width:100%}.results-head{align-items:start;flex-direction:column;gap:7px}.result-grid{grid-template-columns:1fr}}
</style>
