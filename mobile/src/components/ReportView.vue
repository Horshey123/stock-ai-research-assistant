<script setup>
import { computed } from "vue";

const props = defineProps({
  report: { type: Object, default: null },
});

const analysis = computed(() => props.report?.analysis || {});
const stock = computed(() => analysis.value.stock || {});
const overall = computed(() => analysis.value.overall || {});
const scorecard = computed(() => analysis.value.scorecard || {});
const details = computed(() => analysis.value.analysis || {});
const outlook = computed(() => analysis.value.outlook || {});
const actionPlan = computed(() => analysis.value.action_plan || {});
const quality = computed(() => analysis.value.data_quality || {});
const facts = computed(() => analysis.value.verified_facts || {});

const scoreItems = computed(() => [
  { key: "fundamental", label: "基本面", max: 30, ...scorecard.value.fundamental },
  { key: "growth", label: "成长性", max: 20, ...scorecard.value.growth },
  { key: "valuation", label: "估值", max: 20, ...scorecard.value.valuation },
  { key: "trend", label: "趋势", max: 15, ...scorecard.value.trend },
  { key: "risk_control", label: "风险控制", max: 15, ...scorecard.value.risk_control },
]);

const detailItems = computed(() => [
  { key: "fundamental", title: "基本面", subtitle: "盈利质量与财务稳健性", data: details.value.fundamental },
  { key: "growth", title: "成长性", subtitle: "业绩增速与业务动能", data: details.value.growth },
  { key: "valuation", title: "估值", subtitle: "相对历史区间的位置", data: details.value.valuation },
  { key: "technical", title: "技术趋势", subtitle: "价格、均线与波动特征", data: details.value.technical },
]);

function percentage(item) {
  return `${Math.max(0, Math.min(100, ((Number(item.score) || 0) / item.max) * 100))}%`;
}

function formatTime(value) {
  if (!value) return "未知";
  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
</script>

<template>
  <section v-if="report" class="view-stack report-view">
    <div class="report-hero">
      <div class="report-stock-line">
        <div>
          <span>{{ stock.industry || "A股上市公司" }}</span>
          <h1>{{ stock.name || report.stock_name || report.code }}</h1>
          <b>{{ stock.code || report.code }}</b>
        </div>
        <div class="score-medallion">
          <strong>{{ overall.total_score ?? report.total_score ?? "--" }}</strong>
          <span>/ 100</span>
        </div>
      </div>
      <div class="rating-row">
        <span class="rating-pill">{{ overall.rating || report.rating || "未评级" }}</span>
        <span>置信度 {{ overall.confidence || "未知" }}</span>
        <span>{{ formatTime(report.created_at) }}</span>
      </div>
      <p>{{ overall.summary || "暂无综合结论。" }}</p>
    </div>

    <div class="card score-card">
      <div class="section-heading compact">
        <div><span class="section-kicker">SCORECARD</span><h2>五维评分</h2></div>
      </div>
      <div v-for="item in scoreItems" :key="item.key" class="score-row">
        <div class="score-row-top">
          <strong>{{ item.label }}</strong>
          <span><b>{{ item.score ?? "--" }}</b> / {{ item.max }}</span>
        </div>
        <div class="score-track"><i :style="{ width: percentage(item) }"></i></div>
        <p>{{ item.reason || "暂无评分说明。" }}</p>
      </div>
    </div>

    <div v-if="facts.market_position?.summary" class="fact-banner">
      <span>已验证事实</span>
      <p>{{ facts.market_position.summary }}</p>
    </div>

    <article v-for="(item, index) in detailItems" :key="item.key" class="card research-section">
      <div class="research-title">
        <div class="section-number">{{ String(index + 1).padStart(2, "0") }}</div>
        <div><h2>{{ item.title }}</h2><span>{{ item.subtitle }}</span></div>
      </div>
      <p class="conclusion">{{ item.data?.conclusion || "暂无结论。" }}</p>
      <template v-if="item.data?.evidence?.length">
        <h3>核心证据</h3>
        <ul class="evidence-list">
          <li v-for="text in item.data.evidence" :key="text"><i>✓</i><span>{{ text }}</span></li>
        </ul>
      </template>
      <template v-if="item.data?.risks?.length">
        <h3>需要留意</h3>
        <ul class="risk-list">
          <li v-for="text in item.data.risks" :key="text">{{ text }}</li>
        </ul>
      </template>
    </article>

    <article class="card research-section">
      <div class="research-title">
        <div class="section-number">05</div>
        <div><h2>新闻与事件</h2><span>近期催化与不确定因素</span></div>
      </div>
      <p class="conclusion">{{ details.news_and_events?.conclusion || "暂无事件结论。" }}</p>
      <div class="event-columns">
        <div v-if="details.news_and_events?.positive_events?.length" class="event-group positive">
          <strong>正面事件</strong>
          <p v-for="text in details.news_and_events.positive_events" :key="text">{{ text }}</p>
        </div>
        <div v-if="details.news_and_events?.negative_events?.length" class="event-group negative">
          <strong>负面事件</strong>
          <p v-for="text in details.news_and_events.negative_events" :key="text">{{ text }}</p>
        </div>
        <div v-if="details.news_and_events?.uncertain_events?.length" class="event-group uncertain">
          <strong>待确认</strong>
          <p v-for="text in details.news_and_events.uncertain_events" :key="text">{{ text }}</p>
        </div>
      </div>
    </article>

    <div class="section-heading outlook-heading">
      <div><span class="section-kicker">CONDITIONAL OUTLOOK</span><h2>条件化展望</h2></div>
    </div>

    <div class="outlook-grid">
      <div v-for="period in ['short_term', 'medium_term']" :key="period" class="outlook-card">
        <span>{{ outlook[period]?.horizon || (period === "short_term" ? "短期" : "中期") }}</span>
        <strong>{{ outlook[period]?.view || "未知" }}</strong>
        <h3>主要驱动</h3>
        <p v-for="text in outlook[period]?.drivers || []" :key="text">{{ text }}</p>
        <h3>失效条件</h3>
        <p v-for="text in outlook[period]?.invalidation_conditions || []" :key="text">{{ text }}</p>
      </div>
    </div>

    <div class="scenario-list">
      <article v-for="scenario in outlook.scenarios || []" :key="scenario.name" :class="String(scenario.name).includes('乐观') ? 'optimistic' : String(scenario.name).includes('悲观') ? 'pessimistic' : 'neutral'">
        <div><span>{{ scenario.name }}情景</span><b>{{ scenario.expected_direction }}</b></div>
        <h3>触发条件</h3>
        <p v-for="text in scenario.conditions || []" :key="text">{{ text }}</p>
        <h3>观察与应对</h3>
        <p>{{ scenario.response }}</p>
      </article>
    </div>

    <article class="card action-card">
      <div class="section-heading compact">
        <div><span class="section-kicker">ACTION NOTES</span><h2>研究行动清单</h2></div>
        <span class="rating-pill">{{ actionPlan.stance || "观察" }}</span>
      </div>
      <h3>后续跟踪指标</h3>
      <ul class="check-list"><li v-for="text in actionPlan.watch_indicators || []" :key="text">{{ text }}</li></ul>
      <h3>风险纪律</h3>
      <ul class="check-list caution"><li v-for="text in actionPlan.position_and_risk_notes || []" :key="text">{{ text }}</li></ul>
    </article>

    <article class="card quality-card">
      <div class="section-heading compact">
        <div><span class="section-kicker">DATA QUALITY</span><h2>数据完整性</h2></div>
      </div>
      <div class="quality-row"><span>可用模块</span><p>{{ quality.available_sections?.join("、") || "未知" }}</p></div>
      <div class="quality-row"><span>缺失模块</span><p>{{ quality.missing_sections?.join("、") || "无" }}</p></div>
      <div class="quality-row"><span>分析限制</span><p>{{ quality.limitations?.join("；") || "暂无" }}</p></div>
    </article>

    <div class="disclaimer-card">
      <strong>研究声明</strong>
      <p>{{ analysis.disclaimer || "本报告仅用于个人研究，不构成投资建议。" }}</p>
      <small>数据生成时间：{{ formatTime(analysis.analysis_metadata?.source_data_generated_at) }}</small>
    </div>
  </section>

  <div v-else class="empty-state">
    <span>▤</span>
    <strong>尚未打开报告</strong>
    <p>先生成新报告，或者从历史记录中选择一份。</p>
  </div>
</template>
