<script setup>
import { onMounted, ref } from "vue";

const props = defineProps({
  api: { type: Object, required: true },
  configured: { type: Boolean, default: false },
});

const emit = defineEmits([
  "job-started",
  "report-loaded",
  "open-settings",
]);

const code = ref("600519");
const refreshData = ref(false);
const submitting = ref(false);
const loadingLatest = ref(false);
const serviceState = ref("checking");
const serviceMessage = ref("正在连接电脑后端");
const error = ref("");

const quickStocks = [
  { code: "600519", name: "贵州茅台" },
  { code: "300750", name: "宁德时代" },
  { code: "000858", name: "五粮液" },
  { code: "601318", name: "中国平安" },
];

async function checkHealth() {
  if (!props.configured) {
    serviceState.value = "offline";
    serviceMessage.value = "尚未配置 Tailscale 地址";
    return;
  }
  serviceState.value = "checking";
  serviceMessage.value = "正在连接电脑后端";
  try {
    const health = await props.api.health();
    serviceState.value = health.deepseek_configured ? "online" : "warning";
    serviceMessage.value = health.deepseek_configured
      ? `服务在线 · v${health.version}`
      : "服务在线，但 DeepSeek 密钥未配置";
  } catch (requestError) {
    serviceState.value = "offline";
    serviceMessage.value = requestError.message;
  }
}

function validateCode() {
  const value = code.value.trim();
  if (!/^\d{6}$/.test(value)) {
    error.value = "请输入6位A股代码，例如600519。";
    return null;
  }
  return value;
}

async function startAnalysis() {
  const value = validateCode();
  if (!value) return;
  if (!props.configured) {
    emit("open-settings");
    return;
  }
  submitting.value = true;
  error.value = "";
  try {
    const job = await props.api.createJob(value, refreshData.value);
    emit("job-started", job);
  } catch (requestError) {
    error.value = requestError.message;
    await checkHealth();
  } finally {
    submitting.value = false;
  }
}

async function openLatest() {
  const value = validateCode();
  if (!value) return;
  loadingLatest.value = true;
  error.value = "";
  try {
    const report = await props.api.getLatestReport(value);
    emit("report-loaded", report);
  } catch (requestError) {
    error.value = requestError.message;
  } finally {
    loadingLatest.value = false;
  }
}

onMounted(checkHealth);
</script>

<template>
  <section class="view-stack">
    <div class="hero-card">
      <div class="eyebrow">A股研究工作台</div>
      <h1>从公开数据到<br /><span>结构化 AI 研判</span></h1>
      <p>输入股票代码，自动聚合行情、财务、公告与新闻，生成可追溯的个人研究报告。</p>
      <div class="service-chip" :class="serviceState">
        <i></i>
        <span>{{ serviceMessage }}</span>
        <button type="button" @click="checkHealth">重试</button>
      </div>
    </div>

    <div class="card analysis-form">
      <div class="section-heading">
        <div>
          <span class="section-kicker">NEW RESEARCH</span>
          <h2>开始新的分析</h2>
        </div>
        <span class="step-badge">约 2–5 分钟</span>
      </div>

      <label class="field-label" for="stock-code">股票代码</label>
      <div class="stock-input-wrap">
        <span>CN</span>
        <input
          id="stock-code"
          v-model="code"
          inputmode="numeric"
          maxlength="6"
          placeholder="例如 600519"
          @keyup.enter="startAnalysis"
        />
      </div>

      <div class="quick-grid">
        <button
          v-for="stock in quickStocks"
          :key="stock.code"
          type="button"
          :class="{ selected: code === stock.code }"
          @click="code = stock.code"
        >
          <strong>{{ stock.name }}</strong>
          <span>{{ stock.code }}</span>
        </button>
      </div>

      <label class="switch-row">
        <span>
          <strong>强制刷新数据</strong>
          <small>关闭时优先复用24小时内报告</small>
        </span>
        <input v-model="refreshData" type="checkbox" />
        <i></i>
      </label>

      <p v-if="error" class="inline-error">{{ error }}</p>

      <button class="primary-button" type="button" :disabled="submitting" @click="startAnalysis">
        <span v-if="submitting" class="button-spinner"></span>
        <span v-else class="button-icon">✦</span>
        {{ submitting ? "正在提交任务" : "生成 AI 研究报告" }}
      </button>
      <button class="secondary-button" type="button" :disabled="loadingLatest" @click="openLatest">
        {{ loadingLatest ? "正在读取" : "查看该股票最近报告" }}
      </button>
    </div>

    <div class="feature-strip">
      <div><b>01</b><span>多源数据</span></div>
      <div><b>02</b><span>逻辑校验</span></div>
      <div><b>03</b><span>情景分析</span></div>
    </div>
  </section>
</template>
