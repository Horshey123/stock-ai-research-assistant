<script setup>
import { ref } from "vue";

const props = defineProps({
  api: { type: Object, required: true },
  recentReports: { type: Array, default: () => [] },
});

const emit = defineEmits(["report-loaded"]);
const code = ref(props.recentReports[0]?.code || "600519");
const reports = ref([]);
const loading = ref(false);
const openingId = ref("");
const error = ref("");

function formatTime(value) {
  if (!value) return "未知时间";
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function search() {
  if (!/^\d{6}$/.test(code.value.trim())) {
    error.value = "请输入6位股票代码。";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const payload = await props.api.listReports(code.value.trim());
    reports.value = payload.items || [];
    if (!reports.value.length) error.value = "该股票还没有保存过报告。";
  } catch (requestError) {
    error.value = requestError.message;
  } finally {
    loading.value = false;
  }
}

async function openReport(item) {
  openingId.value = item.id;
  error.value = "";
  try {
    emit("report-loaded", await props.api.getReport(item.id));
  } catch (requestError) {
    error.value = requestError.message;
  } finally {
    openingId.value = "";
  }
}
</script>

<template>
  <section class="view-stack">
    <div class="page-title-row no-back">
      <div>
        <span class="section-kicker">REPORT ARCHIVE</span>
        <h1>历史报告</h1>
        <p>从电脑数据库读取已经生成的研究记录。</p>
      </div>
    </div>

    <div class="card history-search">
      <label class="field-label" for="history-code">按股票代码查询</label>
      <div class="inline-search">
        <input id="history-code" v-model="code" inputmode="numeric" maxlength="6" @keyup.enter="search" />
        <button type="button" :disabled="loading" @click="search">{{ loading ? "查询中" : "查询" }}</button>
      </div>
    </div>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <div v-if="reports.length" class="report-list">
      <button v-for="item in reports" :key="item.id" type="button" @click="openReport(item)">
        <div class="report-list-score">{{ item.total_score ?? "--" }}</div>
        <div class="report-list-main">
          <strong>{{ item.stock_name || item.code }}</strong>
          <span>{{ item.code }} · {{ item.rating || "未评级" }}</span>
          <small>{{ formatTime(item.created_at) }}</small>
        </div>
        <span class="chevron">{{ openingId === item.id ? "…" : "›" }}</span>
      </button>
    </div>

    <template v-else-if="recentReports.length">
      <div class="section-heading compact">
        <div><span class="section-kicker">ON THIS PHONE</span><h2>最近打开</h2></div>
      </div>
      <div class="report-list muted-list">
        <button v-for="item in recentReports" :key="item.id" type="button" @click="openReport(item)">
          <div class="report-list-score">{{ item.total_score ?? "--" }}</div>
          <div class="report-list-main">
            <strong>{{ item.stock_name || item.code }}</strong>
            <span>{{ item.code }} · {{ item.rating || "未评级" }}</span>
            <small>{{ formatTime(item.created_at) }}</small>
          </div>
          <span class="chevron">›</span>
        </button>
      </div>
    </template>

    <div v-else class="empty-state">
      <span>▤</span>
      <strong>还没有历史报告</strong>
      <p>完成第一次股票分析后，报告会出现在这里。</p>
    </div>
  </section>
</template>
