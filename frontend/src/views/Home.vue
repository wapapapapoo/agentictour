<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, type Plan } from '@/services/api'
import PlanHistory from '@/components/PlanHistory.vue'
import PlanPreviewModal from '@/components/PlanPreviewModal.vue'

const form = ref({ origin_city: '上海', destination_city: '杭州', start_date: '', end_date: '', people_count: '2', budget_total: '4000', interests: '人文街巷、咖啡、自然风光', hotel_level: '舒适型', transport_preference: '高铁优先', pace: '适中', special_requirements: '' })
const loading = ref(false); const historyLoading = ref(true); const historyRevisionLoading = ref(false); const historyRevisionError = ref(''); const error = ref(''); const plan = ref<Plan | null>(null); const historyPreview = ref<Plan | null>(null); const histories = ref<Plan[]>([]); const revision = ref(''); const naturalLanguage = ref(''); const editingTrip = ref(false); const tripDraft = ref({ id: 0, title: '', origin_city: '', destination_city: '', start_date: '', end_date: '', status: 'planned' }); const publishing = ref(false); const publishMsg = ref('')
const today = new Date().toISOString().slice(0, 10)
function parseJsonObject(source: string): Record<string, unknown> | null {
  const cleaned = source.replace(/<think>[\s\S]*?<\/think>/gi, '').replace(/```(?:json)?/gi, '').trim()
  for (let start = cleaned.indexOf('{'); start >= 0; start = cleaned.indexOf('{', start + 1)) {
    let depth = 0; let quoted = false; let escaped = false
    for (let end = start; end < cleaned.length; end += 1) {
      const character = cleaned[end]
      if (quoted) { if (escaped) escaped = false; else if (character === '\\') escaped = true; else if (character === '"') quoted = false; continue }
      if (character === '"') { quoted = true; continue }
      if (character === '{') depth += 1
      if (character === '}') { depth -= 1; if (depth === 0) { try { const value = JSON.parse(cleaned.slice(start, end + 1)) as unknown; if (value && typeof value === 'object' && !Array.isArray(value)) { const object = value as Record<string, unknown>; if (Array.isArray(object.days) || typeof object.title === 'string') return object } } catch { /* Try the next JSON object. */ } break } }
    }
  }
  return null
}

function extractPlanData(value: unknown, seen = new Set<object>()): Record<string, unknown> {
  if (typeof value === 'string') return parseJsonObject(value) || {}
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}
  const object = value as Record<string, unknown>
  if (seen.has(object)) return {}
  seen.add(object)
  if (Array.isArray(object.days) || typeof object.title === 'string') return object
  for (const key of ['plan_json', 'result', 'answer', 'output', 'data', 'content']) { const extracted = extractPlanData(object[key], seen); if (Object.keys(extracted).length) return extracted }
  for (const nestedValue of Object.values(object)) { const extracted = extractPlanData(nestedValue, seen); if (Object.keys(extracted).length) return extracted }
  return {}
}

const planData = computed(() => extractPlanData(plan.value?.latest_version?.plan_json))
const planDays = computed(() => Array.isArray(planData.value.days) ? planData.value.days as Array<Record<string, unknown>> : [])
const planFormatInvalid = computed(() => Boolean(plan.value) && !planDays.value.length)
function dayItems(day: Record<string, unknown>) { const source = Array.isArray(day.items) ? day.items : Array.isArray(day.activities) ? day.activities : []; return source.map((item) => typeof item === 'object' && item ? item as Record<string, unknown> : { name: String(item) }) }

async function loadHistory() { historyLoading.value = true; try { histories.value = await api.listPlans() } catch { histories.value = [] } finally { historyLoading.value = false } }
async function generate() { error.value = ''; naturalLanguage.value = ''; if (!form.value.start_date || !form.value.end_date) { error.value = '请先选择出行日期。'; return }; if (form.value.end_date < form.value.start_date) { error.value = '返程日期不能早于出发日期。'; return }; loading.value = true; try { const trip = await api.createTrip({ title: `${form.value.destination_city}旅行`, origin_city: form.value.origin_city, destination_city: form.value.destination_city, start_date: form.value.start_date, end_date: form.value.end_date, timezone: 'Asia/Shanghai', status: 'planned' }); plan.value = await api.generatePlan({ ...form.value, trip_id: trip.id }); await loadHistory() } catch (cause) { error.value = cause instanceof Error ? cause.message : '行程生成失败，请稍后重试。' } finally { loading.value = false } }
async function revise() { if (!plan.value || !revision.value.trim()) return; loading.value = true; try { plan.value = await api.revisePlan(plan.value.id, revision.value); revision.value = '' } catch (cause) { error.value = cause instanceof Error ? cause.message : '调整失败。' } finally { loading.value = false } }
async function humanize() { if (!plan.value) return; loading.value = true; try { naturalLanguage.value = (await api.humanizePlan(plan.value.id)).natural_language } catch (cause) { error.value = cause instanceof Error ? cause.message : '暂时无法生成讲解。' } finally { loading.value = false } }
function printPlan() { globalThis.print() }
async function openHistory(item: Plan) { loading.value = true; error.value = ''; try { historyPreview.value = await api.getPlan(item.id) } catch (cause) { error.value = cause instanceof Error ? cause.message : '读取失败。' } finally { loading.value = false } }
async function reviseHistory(revisionRequest: string) { if (!historyPreview.value || !revisionRequest.trim()) return; historyRevisionLoading.value = true; historyRevisionError.value = ''; try { historyPreview.value = await api.revisePlan(historyPreview.value.id, revisionRequest.trim()); await loadHistory() } catch (cause) { historyRevisionError.value = cause instanceof Error ? cause.message : '调整失败。' } finally { historyRevisionLoading.value = false } }
async function openTripEditor() { if (!plan.value) return; try { const trip = await api.getTrip(plan.value.trip_id); tripDraft.value = { id: trip.id, title: trip.title, origin_city: trip.origin_city, destination_city: trip.destination_city, start_date: trip.start_date, end_date: trip.end_date, status: trip.status === 'cancelled' ? 'cancelled' : 'planned' }; editingTrip.value = true } catch (cause) { error.value = cause instanceof Error ? cause.message : '无法读取行程详情。' } }
async function saveTrip() { try { await api.updateTrip(tripDraft.value.id, { title: tripDraft.value.title, origin_city: tripDraft.value.origin_city, destination_city: tripDraft.value.destination_city, start_date: tripDraft.value.start_date, end_date: tripDraft.value.end_date, status: tripDraft.value.status }); editingTrip.value = false; await loadHistory() } catch (cause) { error.value = cause instanceof Error ? cause.message : '保存行程失败。' } }
async function removePlan() { if (!plan.value || !globalThis.confirm('确定删除这份行程计划吗？')) return; try { await api.deletePlan(plan.value.id); plan.value = null; await loadHistory() } catch (cause) { error.value = cause instanceof Error ? cause.message : '删除失败。' } }
async function publishToKnowledge() { if (!plan.value || publishing.value) return; publishing.value = true; publishMsg.value = ''; try { const res = await api.syncPlanToKnowledge(plan.value.id); publishMsg.value = `已发布：${res.document_name}（状态: ${res.indexing_status || 'waiting'}）` } catch (cause) { publishMsg.value = cause instanceof Error ? cause.message : '发布失败。' } finally { publishing.value = false } }
onMounted(loadHistory)
</script>

<template>
  <div class="page planner-page">
    <PlanPreviewModal v-if="historyPreview" :plan="historyPreview" :revising="historyRevisionLoading" :error="historyRevisionError" @close="historyPreview = null" @revise="reviseHistory" />
    <section class="hero">
      <div>
        <p class="eyebrow">
          PLAN WITH CONFIDENCE
        </p><h1>把旅行的期待，<br>变成可执行的路线。</h1><p>填写真实的行程偏好，系统会先创建行程，再调用规划接口生成可调整的方案。</p>
      </div><div class="hero-mark">
        ✦
      </div>
    </section>
    <div class="planner-grid">
      <section class="card form-card">
        <div class="heading">
          <span>01</span><div><h2>行程信息</h2><p>越具体，建议越贴合。</p></div>
        </div><div class="field-grid">
          <label>出发城市<input v-model="form.origin_city"></label><label>目的地<input v-model="form.destination_city"></label><label>出发日期<input
            v-model="form.start_date"
            :min="today"
            type="date"
          ></label><label>返程日期<input
            v-model="form.end_date"
            :min="form.start_date || today"
            type="date"
          ></label><label>同行人数<select v-model="form.people_count"><option value="1">1 人</option><option value="2">2 人</option><option value="3">3—4 人</option><option value="5">5 人以上</option></select></label><label>总预算（元）<input
            v-model="form.budget_total"
            inputmode="numeric"
          ></label>
        </div><div class="heading compact">
          <span>02</span><h2>旅行偏好</h2>
        </div><label class="wide">想体验什么？<textarea
          v-model="form.interests"
          rows="2"
          placeholder="如：历史人文、亲子、摄影、美食"
        /></label><div class="field-grid">
          <label>住宿标准<select v-model="form.hotel_level"><option>经济实惠</option><option>舒适型</option><option>高品质</option></select></label><label>交通偏好<select v-model="form.transport_preference"><option>高铁优先</option><option>自驾优先</option><option>公共交通</option></select></label><label>旅行节奏<select v-model="form.pace"><option>轻松</option><option>适中</option><option>充实</option></select></label>
        </div><label class="wide">特别需求（可选）<textarea
          v-model="form.special_requirements"
          rows="2"
          placeholder="如：老人同行、避开排队、必须去的景点"
        /></label><button
          class="primary"
          :disabled="loading"
          @click="generate"
        >
          {{ loading ? '正在生成行程…' : '生成我的旅行计划 →' }}
        </button><p
          v-if="error"
          class="error"
        >
          {{ error }}
        </p>
      </section>
      <aside class="side">
        <section class="card">
          <p class="eyebrow">
            SAVED PLANS
          </p><h2>最近行程</h2><p
            v-if="historyLoading"
            class="muted"
          >
            正在读取…
          </p><button
            v-for="item in histories.slice(0, 4)"
            :key="item.id"
            class="history"
            @click="openHistory(item)"
          >
            <b>{{ item.destination_city }} · {{ item.title }}</b><small>{{ item.start_date }} 至 {{ item.end_date }}</small>
          </button><p
            v-if="!historyLoading && !histories.length"
            class="muted"
          >
            还没有已保存的行程。
          </p>
        </section>
        <PlanHistory
          :plans="histories"
          :loading="historyLoading"
          :active-plan-id="plan?.id"
          @select="openHistory"
        />
      </aside>
    </div>
    <section
      v-if="plan"
      class="result"
    >
      <div class="result-head">
        <div>
          <p class="eyebrow">
            YOUR ITINERARY · V{{ plan.latest_version?.version_no || 1 }}
          </p><h2>{{ String(planData.title || `${plan.destination_city}旅行计划`) }}</h2><p>{{ String(planData.summary || '已生成一份可继续调整的旅行建议。') }}</p>
        </div><div>
          <button
            class="secondary"
            :disabled="loading"
            @click="humanize"
          >
            自然讲解
          </button><button
            class="secondary"
            :disabled="loading"
            @click="printPlan"
          >
            打印
          </button><button
            class="secondary publish-btn"
            :disabled="publishing"
            @click="publishToKnowledge"
          >
            {{ publishing ? '发布中…' : '发布到知识库' }}
          </button>
        </div>
      </div>
      <p
        v-if="publishMsg"
        class="publish-msg"
      >
        {{ publishMsg }}
      </p><p
        v-if="naturalLanguage"
        class="narrative"
      >
        {{ naturalLanguage }}
      </p><div
        v-if="planDays.length"
        class="days"
      >
        <article
          v-for="(day, index) in planDays"
          :key="index"
          class="card day"
        >
          <span>DAY {{ index + 1 }}</span><h3>{{ String(day.theme || day.title || `第 ${index + 1} 天`) }}</h3><p>{{ String(day.date || day.summary || day.description || '') }}</p><div
            v-if="dayItems(day).length"
            class="activities"
          >
            <i
              v-for="(item, key) in dayItems(day)"
              :key="key"
            ><b>{{ String(item.time || '待定') }}</b><span>{{ String(item.name || item.title || item.description || '行程安排') }}</span><small v-if="item.tips">{{ String(item.tips) }}</small></i>
          </div>
        </article>
      </div><div
        v-if="planFormatInvalid"
        class="card result-fallback"
      >
        <b>这份行程暂时无法整理</b><p>生成结果不包含可识别的 JSON 行程数据，请使用下方输入框调整后重新生成。为保护体验，AI 原始推理内容不会显示。</p>
      </div><div class="revision">
        <input
          v-model="revision"
          placeholder="例如：把第二天安排得轻松一些"
        ><button
          class="primary"
          :disabled="loading || !revision.trim()"
          @click="revise"
        >
          提交调整
        </button>
      </div>
    </section>
    <section
      v-if="plan"
      class="card plan-management"
    >
      <div>
        <p class="eyebrow">
          PLAN MANAGEMENT
        </p><h2>管理这趟行程</h2><p>可以更新基础信息或删除当前计划。</p>
      </div><div class="management-actions">
        <button
          class="secondary"
          @click="openTripEditor"
        >
          编辑行程
        </button><button
          class="danger"
          @click="removePlan"
        >
          删除计划
        </button>
      </div>
    </section>
    <section
      v-if="editingTrip"
      class="card trip-editor"
    >
      <h2>编辑行程信息</h2><p class="status-hint">
        正常状态会按照出发与返程日期自动切换；这里只需要决定是否取消计划。
      </p><div class="editor-grid">
        <input
          v-model="tripDraft.title"
          placeholder="行程名称"
        ><input
          v-model="tripDraft.origin_city"
          placeholder="出发城市"
        ><input
          v-model="tripDraft.destination_city"
          placeholder="目的地"
        ><input
          v-model="tripDraft.start_date"
          type="date"
        ><input
          v-model="tripDraft.end_date"
          type="date"
        ><select v-model="tripDraft.status">
          <option value="planned">
            按日期自动
          </option><option value="cancelled">
            已取消
          </option>
        </select>
      </div><div class="management-actions">
        <button
          class="secondary"
          @click="editingTrip = false"
        >
          取消
        </button><button
          class="primary editor-save"
          @click="saveTrip"
        >
          保存修改
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.status-hint{margin:7px 0 0;color:#7b8982;font-size:12px;line-height:1.6}
.planner-page{max-width:1180px;margin:auto;padding:42px 26px 70px}.hero{display:flex;justify-content:space-between;align-items:center;min-height:200px;margin-bottom:28px;padding:30px 38px;border:1px solid #dcebdd;border-radius:26px;background:radial-gradient(circle at 88% 35%,#d5f0df 0,transparent 23%),linear-gradient(115deg,#fff,#eef8f0)}.eyebrow{margin:0 0 9px;color:#539177;letter-spacing:.13em;font-size:11px;font-weight:700}.hero h1,.result h2{margin:0;color:#234837;font:700 clamp(29px,4vw,46px)/1.28 'Noto Serif SC','Microsoft YaHei',serif}.hero p:last-child{max-width:550px;color:#718178;line-height:1.8}.hero-mark{display:grid;place-items:center;width:85px;height:85px;border-radius:28px;background:#2d785d;color:white;font-size:38px;box-shadow:0 14px 28px #bdddc7}.planner-grid{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:22px;align-items:stretch}.card{border:1px solid #e2ebe3;border-radius:18px;background:#fff;box-shadow:0 10px 28px rgba(39,91,66,.06)}.form-card{padding:30px}.heading{display:flex;align-items:center;gap:12px;margin-bottom:18px}.heading span{display:grid;place-items:center;width:29px;height:29px;border-radius:9px;background:#e1f3e7;color:#297755;font-size:12px;font-weight:800}.heading h2,.side h2{margin:0;color:#294a3b;font-size:19px}.heading p{margin:4px 0 0;color:#85928a;font-size:12px}.compact{margin-top:26px}.field-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:13px}.form-card label{display:grid;gap:7px;color:#65776d;font-size:12px;font-weight:700}.form-card input,.form-card select,.form-card textarea,.revision input,.editor-grid input,.editor-grid select{box-sizing:border-box;width:100%;border:1px solid #dfe8e1;border-radius:10px;padding:10px 11px;background:#fbfdfb;color:#283e34;outline:0}.form-card textarea{resize:vertical}.form-card input:focus,.form-card select:focus,.form-card textarea:focus,.revision input:focus{border-color:#69b390;box-shadow:0 0 0 3px #e6f4ea}.wide{margin:15px 0}.primary,.secondary,.danger{border:0;border-radius:10px;padding:11px 16px;font-weight:700;cursor:pointer}.primary{margin-top:20px;background:#2c775b;color:#fff}.primary:disabled{opacity:.6;cursor:wait}.danger{background:#fff0ee;color:#ae5050}.error{margin:13px 0 0;color:#b74c4c;font-size:13px}.side{display:grid;min-height:0;grid-template-rows:auto minmax(0,1fr);gap:18px;align-content:stretch}.side .card{padding:22px}.side :deep(.plan-history){box-sizing:border-box;min-height:0;height:100%;margin:0;display:flex;flex-direction:column}.side :deep(.plan-grid){grid-template-columns:1fr;overflow:auto;padding-right:2px}.history{display:grid;width:100%;gap:4px;padding:12px 0;border:0;border-bottom:1px solid #edf2ee;background:transparent;text-align:left;cursor:pointer}.history b{color:#40584d;font-size:13px}.history small,.muted,.note p{color:#829088;font-size:12px;line-height:1.65}.note{background:#f4faf5}.note code{color:#2c7c5e}.result,.plan-management,.trip-editor,.notifications{margin-top:29px}.result-head{display:flex;justify-content:space-between;gap:20px;align-items:start;margin-bottom:18px}.result h2{font-size:28px}.result-head p:last-child{color:#738278}.secondary{margin-left:8px;border:1px solid #d8e6dc;background:#fff;color:#39725b}.narrative{padding:20px;line-height:1.8;color:#436053;white-space:pre-line}.publish-btn{border-color:#c4d9ce;background:#f4faf6;color:#3d735a}.publish-msg{margin:12px 0 0;color:#4d8a6b;font-size:13px}.days{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:15px}.day{padding:21px}.day>span{color:#5d9a7f;font-size:11px;font-weight:800}.day h3{margin:9px 0;color:#315044}.day>p{color:#738177;font-size:13px;line-height:1.7}.activities{display:grid;gap:7px}.activities i{display:grid;grid-template-columns:70px 1fr;gap:4px 9px;border-radius:9px;padding:10px;background:#f3f8f4;color:#4e675b;font-size:12px;font-style:normal}.activities i b{color:#318363}.activities i small{grid-column:2;color:#819087;line-height:1.45}.result-fallback{padding:22px;color:#4b6458}.result-fallback p{margin:8px 0 0;color:#7b8982;font-size:13px;line-height:1.7}.revision,.management-actions{display:flex;gap:10px;margin-top:17px}.revision .primary{margin:0;white-space:nowrap}.plan-management,.trip-editor,.notifications{padding:22px}.plan-management{display:flex;justify-content:space-between;gap:20px;align-items:center;background:#f7fbf8}.plan-management h2,.trip-editor h2,.notifications h2{margin:0;color:#315044;font-size:19px}.plan-management p{margin:6px 0 0;color:#77867e;font-size:13px}.editor-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:15px}.editor-save{margin:0}.notifications article{display:flex;justify-content:space-between;gap:16px;align-items:center;padding:12px 0;border-top:1px solid #edf2ee}.notifications article p{margin:0;color:#51655b;font-size:13px}@media(max-width:760px){.planner-page{padding:26px 16px}.hero{padding:27px 22px}.hero-mark{display:none}.planner-grid{grid-template-columns:1fr}.side{grid-template-rows:auto}.side :deep(.plan-history){height:auto}.side :deep(.plan-grid){max-height:none}.field-grid,.editor-grid{grid-template-columns:1fr}.result-head,.plan-management,.notifications article{display:block}.result-head>div:last-child{margin-top:14px}.revision{flex-direction:column}.revision .primary{width:100%}.management-actions{flex-wrap:wrap}}
</style>
