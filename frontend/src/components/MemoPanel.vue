<script setup lang="ts">
import type { Memo } from '@/services/api'

defineProps<{
  memos: Memo[]
  items: Memo[]
  filter: 'all' | 'pending' | 'sent' | 'unscheduled'
  disabled: boolean
  formatDate: (value?: string | null) => string
}>()

const emit = defineEmits<{
  'update:filter': [value: 'all' | 'pending' | 'sent' | 'unscheduled']
  create: []
  edit: [item: Memo]
  remove: [item: Memo]
}>()
</script>

<template>
  <section class="card memo-panel">
    <header>
      <div>
        <p class="eyebrow">MEMOS</p>
        <h2>旅途备忘</h2>
      </div>
      <div class="header-tools">
        <label>
          筛选
          <select
            :value="filter"
            @change="emit('update:filter', ($event.target as HTMLSelectElement).value as typeof filter)"
          >
            <option value="all">全部</option>
            <option value="pending">待提醒</option>
            <option value="sent">已发送</option>
            <option value="unscheduled">无定时</option>
          </select>
        </label>
        <button
          class="header-action"
          :disabled="disabled"
          @click="emit('create')"
        >
          添加备忘
        </button>
      </div>
    </header>

    <div class="memo-list">
      <div
        v-for="item in items"
        :key="item.memo_id"
        class="data-row"
      >
        <div>
          <b>{{ item.memo_text }}</b>
          <small>
            提醒：{{ formatDate(item.reminder_time) }}
            <i v-if="item.reminded_at"> · 已发送</i>
          </small>
        </div>
        <div class="row-actions">
          <button
            class="quiet"
            @click="emit('edit', item)"
          >
            编辑
          </button>
          <button
            class="delete-button"
            @click="emit('remove', item)"
          >
            删除
          </button>
        </div>
      </div>
      <p
        v-if="!items.length"
        class="muted"
      >
        {{ memos.length ? '当前筛选下没有备忘。' : '暂无备忘。' }}
      </p>
    </div>
  </section>
</template>

<style scoped>
.memo-panel {
  display: flex;
  min-height: 0;
  flex-direction: column;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid #edf2ee;
}

.eyebrow {
  margin: 0 0 7px;
  color: #579379;
  letter-spacing: .13em;
  font-size: 11px;
  font-weight: 700;
}

h2 {
  margin: 0;
  color: #345344;
  font-size: 17px;
}

.header-tools,
.header-tools label,
.row-actions {
  display: flex;
  align-items: center;
  gap: 7px;
}

.header-tools label {
  color: #849188;
  font-size: 11px;
}

select {
  border: 1px solid #dce8df;
  border-radius: 8px;
  padding: 7px;
  background: #fff;
  color: #52675c;
}

.header-action,
.quiet,
.delete-button {
  border: 1px solid #dce8df;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
  color: #4f7563;
  cursor: pointer;
}

.header-action {
  border: 0;
  background: #2f8063;
  color: #fff;
  font-weight: 700;
}

.header-action:disabled {
  cursor: not-allowed;
  opacity: .55;
}

.delete-button {
  border: 0;
  color: #ae6262;
}

.memo-list {
  min-height: 0;
  flex: 1;
  overflow: auto;
}

.data-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin: 0 14px;
  padding: 12px 2px;
  border-top: 1px solid #edf2ee;
  color: #566b60;
  font-size: 13px;
}

.data-row:first-child {
  border-top: 0;
}

.data-row > div:first-child {
  display: grid;
  gap: 5px;
}

small {
  color: #89958e;
  font-size: 10px;
  line-height: 1.55;
}

small i {
  color: #4f876d;
  font-style: normal;
}

.muted {
  margin: 14px;
  color: #728178;
  font-size: 13px;
  line-height: 1.7;
}

@media (max-width: 520px) {
  header,
  .data-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .header-tools {
    width: 100%;
    justify-content: space-between;
  }

  .row-actions {
    align-self: flex-end;
  }
}
</style>
