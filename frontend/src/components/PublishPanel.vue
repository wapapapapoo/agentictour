<script setup lang="ts">
import { ref } from 'vue'
import { publishContent, type PublishVisibility } from '@/services/publishing'

const props = defineProps<{ title: string; contentType: 'plan' | 'blog' }>()
const open = ref(false)
const submitted = ref(false)
const visibility = ref<PublishVisibility>('public')
const publishing = ref(false)

async function publish() {
  publishing.value = true
  await publishContent({
    contentType: props.contentType,
    title: props.title,
    visibility: visibility.value,
  })
  submitted.value = true
  publishing.value = false
}
</script>

<template>
  <div class="publish-panel">
    <button
      class="publish-trigger"
      type="button"
      @click="open = !open"
    >
      ↗ {{ contentType === 'plan' ? '发布这份行程' : '发布这篇作品' }}
    </button>
    <div
      v-if="open"
      class="publish-drawer"
    >
      <template v-if="!submitted">
        <b>分享至旅行社区</b>
        <p>发布后将展示给其他旅行者。你可随时修改或下架。</p>
        <label>可见范围
          <select v-model="visibility">
            <option value="public">
              公开推荐
            </option>
            <option value="unlisted">
              仅链接可见
            </option>
          </select>
        </label>
        <button
          class="primary-button"
          :disabled="publishing"
          type="button"
          @click="publish"
        >
          {{ publishing ? '正在提交…' : '确认发布' }}
        </button>
      </template>
      <template v-else>
        <b>已保存发布意图</b>
        <p>社区发布接口尚未接入；接入后将把"{{ props.title }}"提交为 {{ contentType === 'plan' ? '推荐行程' : '旅行内容' }}。</p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.publish-panel { position: relative; }.publish-trigger { border: 1px solid #b9dcc8; border-radius: 10px; padding: 10px 14px; color: #187c63; background: #f0faf4; font-size: 13px; font-weight: 700; }.publish-drawer { position: absolute; right: 0; bottom: calc(100% + 9px); z-index: 4; width: 275px; padding: 17px; border: 1px solid #d7e9dd; border-radius: 14px; color: #456257; background: #fff; box-shadow: 0 15px 32px rgba(33,75,52,.15); }.publish-drawer b { font-size: 13px; }.publish-drawer p { margin: 6px 0 12px; color: #75827c; font-size: 11px; line-height: 1.6; }.publish-drawer label { display: block; color: #66756e; font-size: 11px; font-weight: 700; }.publish-drawer select { width: 100%; margin: 4px 0 11px; padding: 8px; border: 1px solid #dce7df; border-radius: 8px; color: #385147; background: #fbfdfb; }.publish-drawer .primary-button { width: 100%; padding: 9px; font-size: 12px; }
</style>
