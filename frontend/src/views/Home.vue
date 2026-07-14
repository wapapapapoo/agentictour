<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, type Plan } from '@/services/api'
import PublishPanel from '@/components/PublishPanel.vue'

const form = ref({ origin_city: '上海', destination_city: '杭州', start_date: '', end_date: '', people_count: '2', budget_total: '4000', interests: '人文街巷、咖啡、自然风光', hotel_level: '舒适型', transport_preference: '高铁优先', pace: '适中', special_requirements: '' })
const loading = ref(false); const historyLoading = ref(true); const error = ref(''); const plan = ref<Plan | null>(null); const histories = ref<Plan[]>([]); const revision = ref(''); const naturalLanguage = ref('')
const planData = computed(() => plan.value?.latest_version?.plan_json || {})
const planDays = computed(() => Array.isArray(planData.value.days) ? planData.value.days as Array<Record<string, unknown>> : [])
const today = new Date().toISOString().slice(0, 10)
const window = globalThis.window

async function loadHistory() { historyLoading.value = true; try { histories.value = await api.listPlans() } catch { histories.value = [] } finally { historyLoading.value = false } }
async function generate() { error.value = ''; naturalLanguage.value = ''; if (!form.value.start_date || !form.value.end_date) { error.value = '请先选择出行日期。'; return }; loading.value = true; try { plan.value = await api.generatePlan(form.value); await loadHistory() } catch (e) { error.value = e instanceof Error ? e.message : '行程生成失败，请稍后重试。' } finally { loading.value = false } }
async function revise() { if (!plan.value || !revision.value.trim()) return; loading.value = true; error.value = ''; try { plan.value = await api.revisePlan(plan.value.id, revision.value); revision.value = ''; await loadHistory() } catch (e) { error.value = e instanceof Error ? e.message : '调整失败' } finally { loading.value = false } }
async function humanize() { if (!plan.value) return; loading.value = true; try { naturalLanguage.value = (await api.humanizePlan(plan.value.id)).natural_language } catch (e) { error.value = e instanceof Error ? e.message : '暂时无法生成讲解' } finally { loading.value = false } }
async function openHistory(item: Plan) { error.value = ''; loading.value = true; try { plan.value = await api.getPlan(item.id) } catch (e) { error.value = e instanceof Error ? e.message : '读取失败' } finally { loading.value = false } }
onMounted(loadHistory)
</script>

<template>
  <div class="page planner-page">
    <section class="hero">
      <div>
        <p class="eyebrow">
          Plan with confidence
        </p><h1 class="page-title">
          把旅行的期待，变成可执行的路线
        </h1><p class="page-intro">
          告诉我你的偏好，AgenticTour 将结合实时信息，为你编排每一天。
        </p>
      </div><div class="hero-orbit">
        <span>✦</span><i /><b />
      </div>
    </section>
    <div class="planner-grid">
      <section class="card plan-form">
        <div class="section-heading">
          <span class="step-number">01</span><div><h2>旅程信息</h2><p>越具体，建议就越贴合你。</p></div>
        </div>
        <div class="field-grid">
          <label>出发城市<input
            v-model="form.origin_city"
            placeholder="如：上海"
          ></label><label>目的地<input
            v-model="form.destination_city"
            placeholder="如：杭州"
          ></label><label>出发日期<input
            v-model="form.start_date"
            :min="today"
            type="date"
          ></label><label>返程日期<input
            v-model="form.end_date"
            :min="form.start_date || today"
            type="date"
          ></label><label>同行人数<select v-model="form.people_count"><option value="1">1 人</option><option value="2">2 人</option><option value="3">3–4 人</option><option value="5">5 人以上</option></select></label><label>总预算（元）<input
            v-model="form.budget_total"
            inputmode="numeric"
          ></label>
        </div>
        <div class="section-heading compact">
          <span class="step-number">02</span><div><h2>旅行偏好</h2></div>
        </div>
        <label class="wide-label">想体验什么？<textarea
          v-model="form.interests"
          rows="2"
          placeholder="如：历史人文、亲子、摄影、美食…"
        /></label>
        <div class="chips">
          <button
            v-for="tag in ['慢节奏','美食探索','自然徒步','城市漫游','拍照出片']"
            :key="tag"
            type="button"
            @click="form.interests = form.interests.includes(tag) ? form.interests.replace(tag,'').replace('、、','、') : `${form.interests}、${tag}`"
          >
            {{ tag }}
          </button>
        </div>
        <div class="field-grid preferences">
          <label>住宿标准<select v-model="form.hotel_level"><option>经济实惠</option><option>舒适型</option><option>高品质</option></select></label><label>交通偏好<select v-model="form.transport_preference"><option>高铁优先</option><option>自驾优先</option><option>公共交通</option></select></label><label>旅行节奏<select v-model="form.pace"><option>轻松</option><option>适中</option><option>充实</option></select></label>
        </div>
        <label class="wide-label">特别需求（可选）<textarea
          v-model="form.special_requirements"
          rows="2"
          placeholder="如：老人同行、避开排队、必须去的景点…"
        /></label>
        <button
          class="primary-button generate"
          :disabled="loading"
          @click="generate"
        >
          {{ loading ? '旅行智能体正在思考…' : '✦ 生成我的旅行计划' }}
        </button><p class="form-note">
          生成后会经过时间、预算与风险检查，并保留调整空间。
        </p><div
          v-if="error"
          class="notice error"
        >
          {{ error }}
        </div>
      </section>
      <aside class="side-column">
        <section class="card workflow">
          <p class="eyebrow">
            Multi-agent workflow
          </p><h2>这次旅行，谁在帮你？</h2><div class="agent">
            <span>⌘</span><div><b>规划 Agent</b><small>拆解日程与路线</small></div><em>进行中</em>
          </div><div class="agent">
            <span>⌁</span><div><b>数据 Agent</b><small>天气、交通、景点信息</small></div><em>待调用</em>
          </div><div class="agent">
            <span>✓</span><div><b>审查 Agent</b><small>时间与预算风险检查</small></div><em>待检查</em>
          </div>
        </section>
        <section class="card history">
          <div class="history-title">
            <h2>最近行程</h2><span>{{ histories.length }} 条</span>
          </div><div
            v-if="historyLoading"
            class="muted small-pad"
          >
            正在读取…
          </div><button
            v-for="item in histories.slice(0,3)"
            :key="item.id"
            class="history-item"
            @click="openHistory(item)"
          >
            <span class="history-icon">⌖</span><span><b>{{ item.destination_city }} · {{ item.title || '旅行计划' }}</b><small>{{ item.start_date }} 至 {{ item.end_date }}</small></span><i>›</i>
          </button><div
            v-if="!historyLoading && !histories.length"
            class="muted small-pad"
          >
            还没有保存的行程，生成第一份吧。
          </div>
        </section>
      </aside>
    </div>
    <section
      class="readiness"
      aria-label="旅行规划能力说明"
    >
      <div class="readiness-copy">
        <p class="eyebrow">
          Travel intelligence
        </p><h2>一份好行程，不只是景点清单。</h2><p>从实时信息到约束审查，AgenticTour 会把影响旅行体验的关键因素放进同一份计划里。</p>
      </div>
      <div class="capability-grid">
        <article><span class="cap-icon weather">☼</span><div><b>天气与穿衣</b><small>行程节奏、室内备选与风险提醒</small></div><em>实时数据待接入</em></article>
        <article><span class="cap-icon place">⌖</span><div><b>景点与路线</b><small>开放信息、移动耗时与主题标签</small></div><em>实时数据待接入</em></article>
        <article><span class="cap-icon stay">▣</span><div><b>住宿与预算</b><small>区域匹配、住宿标准与总额控制</small></div><em>约束已支持</em></article>
        <article><span class="cap-icon check">✓</span><div><b>计划审查</b><small>时间冲突、预算冲突与低置信提示</small></div><em>审查界面待接入</em></article>
      </div>
    </section>
    <section
      v-if="plan"
      class="result-section"
    >
      <div class="result-heading">
        <div>
          <p class="eyebrow">
            Your itinerary · V{{ plan.latest_version?.version_no || 1 }}
          </p><h2>{{ String(planData.title || `${plan.destination_city}旅行计划`) }}</h2><p>{{ String(planData.summary || '已为你生成一份可调整的旅行建议。') }}</p>
        </div><div class="result-actions">
          <button
            class="secondary-button"
            :disabled="loading"
            @click="humanize"
          >
            换成自然讲解
          </button><button
            class="secondary-button"
            type="button"
            @click="window.print()"
          >
            打印
          </button><PublishPanel
            :title="String(planData.title || `${plan.destination_city}旅行计划`)"
            content-type="plan"
          />
        </div>
      </div><div
        v-if="naturalLanguage"
        class="natural card"
      >
        {{ naturalLanguage }}
      </div>
      <div
        v-if="planDays.length"
        class="day-list"
      >
        <article
          v-for="(day, index) in planDays"
          :key="index"
          class="card day-card"
        >
          <span class="day-label">DAY {{ index + 1 }}</span><h3>{{ String(day.title || day.date || `第 ${index + 1} 天`) }}</h3><p>{{ String(day.summary || day.description || '详细日程由规划 Agent 整理中。') }}</p><div
            v-if="Array.isArray(day.activities)"
            class="activities"
          >
            <span
              v-for="(activity, itemIndex) in day.activities"
              :key="itemIndex"
            >{{ typeof activity === 'string' ? activity : JSON.stringify(activity) }}</span>
          </div>
        </article>
      </div>
      <div
        v-else
        class="card raw-result"
      >
        <h3>行程数据</h3><pre>{{ JSON.stringify(planData, null, 2) }}</pre>
      </div>
      <div
        v-if="Array.isArray(planData.warnings) && planData.warnings.length"
        class="warnings"
      >
        <b>出行提醒</b><span
          v-for="warning in planData.warnings"
          :key="String(warning)"
        >⚠ {{ warning }}</span>
      </div>
      <div class="revision card">
        <div><b>想换一种玩法？</b><small>例如：减少步行、加入夜生活、把预算压到 3000 元。</small></div><input
          v-model="revision"
          placeholder="告诉我你想怎么调整…"
          @keyup.enter="revise"
        ><button
          class="primary-button"
          :disabled="loading || !revision.trim()"
          @click="revise"
        >
          调整计划
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero { display:flex; justify-content:space-between; align-items:center; margin-bottom:34px; }.hero-orbit{position:relative;width:122px;height:82px;background:radial-gradient(circle at 50% 60%,#d6f1df,transparent 42%)}.hero-orbit span{position:absolute;left:45px;top:22px;color:#258a70;font-size:29px}.hero-orbit i,.hero-orbit b{position:absolute;border:1px solid #cbe6d5;border-radius:50%;transform:rotate(-22deg)}.hero-orbit i{width:112px;height:42px;top:18px}.hero-orbit b{width:74px;height:28px;top:28px;left:19px}.planner-grid{display:grid;grid-template-columns:minmax(0,1fr) 315px;gap:22px}.plan-form{padding:28px}.section-heading{display:flex;align-items:center;gap:12px;margin-bottom:22px}.section-heading h2,.workflow h2,.history h2{font-size:17px;margin:0}.section-heading p{font-size:12px;color:#87928d;margin:2px 0 0}.section-heading.compact{margin:28px 0 16px}.step-number{color:#2b9b7b;background:#eaf8f1;border-radius:8px;width:29px;height:29px;display:grid;place-items:center;font-weight:700;font-size:13px}.field-grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}.field-grid.preferences{grid-template-columns:repeat(3,1fr);margin:16px 0}label{display:block;color:#56635d;font-size:12px;font-weight:600}input,textarea,select{width:100%;display:block;border:1px solid #dfe7e1;background:#fbfcfa;color:#26372f;border-radius:8px;padding:10px 11px;margin-top:6px;outline:0;font-size:14px}input:focus,textarea:focus,select:focus{border-color:#62b69a;box-shadow:0 0 0 3px #e9f7f0}.wide-label{margin-top:16px}.chips{display:flex;gap:7px;flex-wrap:wrap;margin:9px 0 2px}.chips button{border:1px solid #dbe8e0;background:#f7fbf8;border-radius:20px;padding:5px 10px;color:#5c776d;font-size:12px}.generate{width:100%;margin-top:25px}.form-note{text-align:center;color:#8a9690;font-size:11px;margin:11px 0 0}.side-column{display:grid;align-content:start;gap:18px}.workflow,.history{padding:21px}.workflow h2{margin:5px 0 15px}.agent{display:flex;align-items:center;gap:10px;padding:11px 0;border-top:1px solid #edf1ed}.agent>span{width:29px;height:29px;display:grid;place-items:center;border-radius:8px;background:#edf8f2;color:#278d70}.agent b,.agent small{display:block;font-size:12px}.agent small{color:#8a9690;margin-top:2px}.agent em{font-style:normal;font-size:10px;color:#9aa49f;margin-left:auto}.history-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}.history-title span{font-size:11px;color:#7f8d86}.history-item{width:100%;display:flex;text-align:left;align-items:center;gap:9px;padding:11px 0;border:0;border-top:1px solid #edf1ed;background:transparent;color:#46564e}.history-icon{color:#38a27f;font-size:18px}.history-item b,.history-item small{display:block;font-size:12px}.history-item small{color:#8a9690;margin-top:2px}.history-item i{margin-left:auto;font-style:normal;color:#90a099;font-size:21px}.small-pad{padding:12px 0;font-size:12px}.result-section{margin-top:40px}.result-heading{display:flex;justify-content:space-between;gap:25px;align-items:end;margin-bottom:18px}.result-heading h2{font:700 28px 'Noto Serif SC','Microsoft YaHei',serif;margin:4px 0 8px}.result-heading p:not(.eyebrow){margin:0;color:#76837d;font-size:14px}.result-actions{display:flex;gap:8px;white-space:nowrap}.natural{padding:20px;margin-bottom:15px;line-height:1.8;color:#42584e}.day-list{display:grid;gap:12px}.day-card{padding:21px 23px}.day-label{display:inline-block;color:#299678;background:#eff9f3;border-radius:12px;padding:3px 8px;font-size:10px;font-weight:700;letter-spacing:.5px}.day-card h3{margin:9px 0 5px;font-size:17px}.day-card p{color:#63736b;font-size:14px;margin:0}.activities{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}.activities span{padding:5px 8px;background:#f5f8f5;border-radius:6px;color:#507166;font-size:12px}.warnings{display:flex;flex-direction:column;gap:7px;margin:17px 0;padding:16px 18px;background:#fff9e8;border:1px solid #f3e7b8;border-radius:12px;color:#856b24;font-size:13px}.raw-result{padding:21px}.raw-result h3{margin:0 0 12px}.raw-result pre{overflow:auto;font-size:12px;background:#f6f8f6;padding:14px;border-radius:8px}.revision{padding:15px;display:grid;grid-template-columns:1fr minmax(190px,2fr) auto;align-items:center;gap:12px}.revision b,.revision small{display:block}.revision b{font-size:14px}.revision small{font-size:11px;color:#829089;margin-top:4px}.revision input{margin:0}.revision .primary-button{padding:10px 14px}
@media(max-width:850px){.planner-grid{grid-template-columns:1fr}.side-column{grid-template-columns:1fr 1fr}.revision{grid-template-columns:1fr auto}.revision>div{grid-column:1/-1}}@media(max-width:560px){.hero-orbit{display:none}.field-grid,.field-grid.preferences,.side-column{grid-template-columns:1fr}.plan-form{padding:20px}.result-heading{align-items:start;flex-direction:column}.revision{grid-template-columns:1fr}.revision .primary-button{width:100%}}
</style>

<style scoped>
/* Visual refinement: stronger hierarchy, calmer cards, and form-first ergonomics. */
.planner-page { position: relative; }
.hero { position: relative; min-height: 144px; margin-bottom: 30px; padding: 25px 31px; overflow: hidden; border: 1px solid #dcebdd; border-radius: 23px; background: linear-gradient(115deg, rgba(252,255,252,.94), rgba(232,247,237,.85)); box-shadow: 0 14px 32px rgba(35,97,68,.06); }
.hero::after { position: absolute; top: -86px; right: 85px; width: 240px; height: 240px; border: 1px solid rgba(68,168,125,.16); border-radius: 50%; box-shadow: 0 0 0 28px rgba(83,179,133,.06), 0 0 0 61px rgba(83,179,133,.035); content: ''; }
.hero > div:first-child { position: relative; z-index: 1; }.hero .page-title { font-size: 32px; }.hero-orbit { z-index: 1; transform: scale(1.16); }
.planner-grid { grid-template-columns: minmax(0, 1fr) 320px; gap: 24px; align-items: start; }
.plan-form { position: relative; padding: 31px; overflow: hidden; }.plan-form::before { position: absolute; top: 0; left: 30px; right: 30px; height: 3px; border-radius: 0 0 5px 5px; background: linear-gradient(90deg, #31a27e, #9bd4a9); content: ''; }
.section-heading { margin-bottom: 20px; }.section-heading.compact { margin: 31px 0 17px; padding-top: 25px; border-top: 1px solid #edf2ee; }.section-heading h2 { color: #213f35; font-size: 18px; letter-spacing: -.2px; }.section-heading p { margin-top: 4px; }.step-number { width: 34px; height: 34px; border: 1px solid #d5edde; border-radius: 11px; color: #148064; background: linear-gradient(145deg,#f3fcf6,#e4f7eb); box-shadow: inset 0 1px rgba(255,255,255,.9); }
.field-grid { gap: 12px; }.field-grid.preferences { gap: 10px; margin: 14px 0 3px; }
label { min-height: 78px; padding: 10px 12px 9px; border: 1px solid #e1eae3; border-radius: 12px; color: #68766f; background: #fbfdfb; font-size: 11px; font-weight: 700; letter-spacing: .25px; transition: border-color .18s, box-shadow .18s, background .18s; }
label:focus-within { border-color: #72bd9f; background: #fff; box-shadow: 0 0 0 4px rgba(64,165,124,.11); }.wide-label { min-height: 0; margin-top: 15px; } .wide-label textarea { min-height: 58px; }
input, textarea, select { margin-top: 3px; padding: 3px 0 0; border: 0; border-radius: 0; color: #253b32; background: transparent; box-shadow: none; font-size: 14px; font-weight: 500; } input:focus, textarea:focus, select:focus { border: 0; box-shadow: none; } input::placeholder, textarea::placeholder { color: #adb8b1; font-weight: 400; } select { cursor: pointer; } textarea { resize: vertical; line-height: 1.55; }
.chips { gap: 8px; margin: 10px 1px 4px; }.chips button { border: 1px solid #dceae1; border-radius: 20px; padding: 6px 11px; color: #527166; background: #f7fbf8; font-size: 12px; transition: all .16s; }.chips button:hover { border-color: #84c9aa; color: #16795f; background: #ebf8f0; transform: translateY(-1px); }
.generate { min-height: 48px; margin-top: 27px; font-size: 14px; }.form-note { margin-top: 12px; }.side-column { gap: 20px; }.workflow, .history { padding: 23px; border-radius: 18px; }.workflow { background: linear-gradient(160deg,rgba(255,255,255,.98),rgba(242,250,245,.98)); }.workflow h2 { margin: 7px 0 17px; color: #254237; }.agent { padding: 13px 0; }.agent:first-of-type { border-top-color: #dceae0; }.agent > span { width: 33px; height: 33px; border-radius: 10px; background: #e7f6ed; }.agent b { color: #395248; }.agent em { padding: 3px 6px; border-radius: 9px; color: #54917b; background: #ebf7ef; }.history-title { margin-bottom: 9px; }.history-item { border-radius: 9px; padding: 11px 8px; transition: background .16s; }.history-item:hover { background: #f1f8f3; }.history-item:first-of-type { border-top: 1px solid #edf1ed; }
.result-section { margin-top: 47px; padding: 29px; border: 1px solid #dceade; border-radius: 23px; background: rgba(249,253,250,.7); }.result-heading { margin-bottom: 22px; }.result-heading h2 { color: #214235; }.day-card { border-left: 4px solid #5fb78f; padding: 23px 25px; }.revision { border-color: #cee5d6; box-shadow: 0 10px 25px rgba(39,100,70,.05); }
@media (max-width: 850px) { .hero::after { right: -80px; }.planner-grid { grid-template-columns: 1fr; }.side-column { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .hero { min-height: auto; padding: 24px 20px; }.plan-form { padding: 24px 18px; }.plan-form::before { left: 18px; right: 18px; }.field-grid.preferences { gap: 12px; }.side-column { grid-template-columns: 1fr; }.result-section { padding: 19px 14px; } }
.readiness { display: grid; grid-template-columns: 260px 1fr; gap: 28px; align-items: center; margin-top: 28px; padding: 25px 28px; border: 1px solid #dce9df; border-radius: 20px; background: rgba(255,255,255,.68); }.readiness-copy h2 { margin: 7px 0; color: #254337; font: 700 21px/1.4 'Noto Serif SC','Microsoft YaHei',serif; }.readiness-copy p:last-child { margin: 0; color: #738078; font-size: 13px; line-height: 1.7; }.capability-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }.capability-grid article { display: grid; grid-template-columns: 32px 1fr; gap: 9px; align-items: center; min-height: 68px; padding: 10px; border: 1px solid #e4ede6; border-radius: 12px; background: rgba(252,254,252,.86); }.cap-icon { display: grid; width: 31px; height: 31px; place-items: center; border-radius: 9px; font-weight: 700; }.weather { color: #bc8825; background: #fff5d9; }.place { color: #3980a2; background: #e6f4fb; }.stay { color: #8670b2; background: #f0eafb; }.check { color: #278764; background: #e2f5e9; }.capability-grid b, .capability-grid small { display: block; }.capability-grid b { color: #385147; font-size: 12px; }.capability-grid small { margin-top: 2px; color: #89958f; font-size: 10px; }.capability-grid em { grid-column: 2; color: #6b9c88; font-size: 10px; font-style: normal; }
@media (max-width: 850px) { .readiness { grid-template-columns: 1fr; gap: 18px; } } @media (max-width: 560px) { .readiness { padding: 20px 16px; }.capability-grid { grid-template-columns: 1fr; } }
</style>
