<script setup lang="ts">
import type { CommunityPost } from '@/services/community'

defineProps<{ post: CommunityPost }>()
</script>

<template>
  <article class="community-card card">
    <div class="cover" :class="post.accent"><span>{{ post.type === 'plan' ? '✦ 行程' : '✎ 游记' }}</span><strong>{{ post.destination }}</strong></div>
    <div class="card-body"><p class="content-kind">{{ post.type === 'plan' ? '推荐行程' : '旅行故事' }}</p><h3>{{ post.title }}</h3><p class="excerpt">{{ post.excerpt }}</p><div class="tags"><span v-for="tag in post.tags" :key="tag"># {{ tag }}</span></div><div class="post-footer"><span>{{ post.author }} · {{ post.readMinutes }} 分钟阅读</span><span>♡ {{ post.likes }} / ⌑ {{ post.saves }}</span></div></div>
  </article>
</template>

<style scoped>
.community-card { overflow: hidden; transition: transform .2s, box-shadow .2s; }.community-card:hover { transform: translateY(-3px); box-shadow: 0 18px 33px rgba(35,81,58,.11); }.cover { position: relative; height: 128px; padding: 16px; color: #fff; overflow: hidden; }.cover::after { position: absolute; width: 170px; height: 170px; right: -48px; bottom: -93px; border: 1px solid rgba(255,255,255,.48); border-radius: 50%; box-shadow: 0 0 0 25px rgba(255,255,255,.1); content: ''; }.cover span { position: relative; z-index: 1; display: inline-block; padding: 4px 7px; border: 1px solid rgba(255,255,255,.4); border-radius: 10px; font-size: 10px; background: rgba(255,255,255,.14); }.cover strong { position: absolute; right: 17px; bottom: 16px; z-index: 1; font: 700 29px 'Noto Serif SC','Microsoft YaHei',serif; }.lake { background: linear-gradient(135deg,#3d91a1,#8ac7bc); }.sunset { background: linear-gradient(135deg,#db8763,#e7bc82); }.pepper { background: linear-gradient(135deg,#b65450,#e2936d); }.ocean { background: linear-gradient(135deg,#397f9d,#77b9c1); }.card-body { padding: 17px; }.content-kind { margin: 0; color: #37957a; font-size: 10px; font-weight: 700; letter-spacing: .7px; }.card-body h3 { min-height: 44px; margin: 7px 0; color: #2a4439; font-size: 16px; line-height: 1.45; }.excerpt { min-height: 42px; margin: 0; color: #718078; font-size: 12px; line-height: 1.7; }.tags { display: flex; flex-wrap: wrap; gap: 5px; margin: 13px 0; }.tags span { padding: 3px 6px; border-radius: 7px; color: #668278; background: #f0f6f1; font-size: 10px; }.post-footer { display: flex; justify-content: space-between; gap: 6px; padding-top: 11px; border-top: 1px solid #edf1ed; color: #85938c; font-size: 10px; }
</style>
