<script setup lang="ts">
import { computed, ref } from 'vue'
import CommunityCard from '@/components/CommunityCard.vue'
import { searchCommunityPosts, type CommunityContentType } from '@/services/community'

const currentType = ref<'all' | CommunityContentType>('all')
const query = ref('')
const posts = computed(() => searchCommunityPosts(query.value, currentType.value))
</script>

<template>
  <div class="page discover-page"><section class="discover-hero"><div><p class="eyebrow">AgenticTour community</p><h1 class="page-title">从别人的旅程里，发现下一次出发。</h1><p class="page-intro">浏览真实发布接口接入前的展示样例，看看一份好行程和一篇好游记可以是什么样子。</p></div><RouterLink to="/search" class="search-link">⌕ 搜索目的地、主题或作者</RouterLink></section><div class="community-notice">社区接口预留中 · 当前展示为界面样例，接入后将替换为公开发布内容。</div><section class="feed-toolbar"><div class="filters"><button v-for="item in [{value:'all',label:'全部内容'},{value:'plan',label:'推荐行程'},{value:'blog',label:'旅行游记'}]" :key="item.value" type="button" :class="{ active: currentType === item.value }" @click="currentType = item.value as 'all' | CommunityContentType">{{ item.label }}</button></div><input v-model="query" placeholder="在当前内容中筛选" /></section><section v-if="posts.length" class="post-grid"><CommunityCard v-for="post in posts" :key="post.id" :post="post" /></section><div v-else class="empty-state card">没有找到匹配内容，换个关键词试试。</div></div>
</template>

<style scoped>
.discover-hero { display: flex; align-items: end; justify-content: space-between; gap: 30px; min-height: 188px; padding: 29px 32px; border: 1px solid #dcebdd; border-radius: 23px; background: linear-gradient(115deg,rgba(255,255,255,.94),rgba(230,246,236,.86)); }.discover-hero .page-title { max-width: 650px; font-size: 34px; }.search-link { flex: 0 0 auto; padding: 12px 15px; border: 1px solid #cce4d5; border-radius: 10px; color: #247a63; background: rgba(255,255,255,.72); font-size: 13px; font-weight: 700; }.community-notice { margin: 17px 0; padding: 10px 13px; border: 1px solid #d7eadc; border-radius: 10px; color: #5c8675; background: #eef8f1; font-size: 12px; }.feed-toolbar { display: flex; justify-content: space-between; gap: 16px; margin: 25px 0 16px; }.filters { display: flex; gap: 7px; }.filters button { padding: 8px 12px; border: 1px solid #dbe8df; border-radius: 18px; color: #657a70; background: #fff; font-size: 12px; }.filters button.active { border-color: #65b797; color: #187d63; background: #eaf8ef; font-weight: 700; }.feed-toolbar input { width: 210px; padding: 8px 11px; border: 1px solid #dbe8df; border-radius: 9px; outline: none; background: #fff; font-size: 12px; }.feed-toolbar input:focus { border-color: #6ab99b; box-shadow: 0 0 0 3px #e7f5ec; }.post-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 17px; }@media(max-width:680px){.discover-hero{align-items:start;flex-direction:column;padding:24px 20px}.discover-hero .page-title{font-size:29px}.feed-toolbar{align-items:stretch;flex-direction:column}.feed-toolbar input{width:100%}.filters{overflow:auto}.post-grid{grid-template-columns:1fr}}
</style>
