<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  api: { type: Object, required: true },
  initialJob: { type: Object, default: null },
});

const emit = defineEmits(["report-loaded", "back"]);
const job = ref(props.initialJob);
const error = ref("");
const fetchingReport = ref(false);
let timer = null;

const steps = [
  { status: "queued", label: "任务排队", detail: "创建分析任务" },
  { status: "fetching_data", label: "采集数据", detail: "行情、财务、公告与新闻" },
  { status: "preparing_context", label: "整理上下文", detail: "提取关键指标和已验证事实" },
  { status: "analyzing", label: "AI 深度分析", detail: "生成多维度结构化结论" },
  { status: "validating", label: "逻辑校验", detail: "核对分数、均线与关键数字" },
  { status: "completed", label: "完成报告", detail: "保存并呈现研究结果" },
];

const currentStepIndex = computed(() => {
  const index = steps.findIndex((step) => step.status === job.value?.status);
  return index < 0 ? 0 : index;
});

function stepState(index) {
  if (job.value?.status === "failed") return index <= currentStepIndex.value ? "failed" : "pending";
  if (index < currentStepIndex.value) return "done";
  if (index === currentStepIndex.value) return job.value?.status === "completed" ? "done" : "active";
  return "pending";
}

async function loadCompletedReport() {
  if (!job.value?.report_id || fetchingReport.value) return;
  fetchingReport.value = true;
  try {
    const report = await props.api.getReport(job.value.report_id);
    emit("report-loaded", report);
  } catch (requestError) {
    error.value = requestError.message;
  } finally {
    fetchingReport.value = false;
  }
}

async function poll() {
  if (!job.value?.id) return;
  try {
    job.value = await props.api.getJob(job.value.id);
    error.value = "";
    if (job.value.status === "completed") {
      clearInterval(timer);
      await loadCompletedReport();
    } else if (job.value.status === "failed") {
      clearInterval(timer);
      error.value = job.value.error || job.value.message || "分析任务失败。";
    }
  } catch (requestError) {
    error.value = requestError.message;
  }
}

onMounted(async () => {
  await poll();
  if (!["completed", "failed"].includes(job.value?.status)) {
    timer = setInterval(poll, 2500);
  }
});

onBeforeUnmount(() => clearInterval(timer));
</script>

<template>
  <section class="view-stack progress-view">
    <div class="page-title-row">
      <button class="back-button" type="button" @click="emit('back')">‹</button>
      <div>
        <span class="section-kicker">ANALYSIS JOB</span>
        <h1>正在研究 {{ job?.code }}</h1>
      </div>
    </div>

    <div class="progress-orbit">
      <div class="progress-ring" :style="{ '--progress': `${job?.progress || 0}%` }">
        <div>
          <strong>{{ job?.progress || 0 }}</strong><span>%</span>
        </div>
      </div>
      <p>{{ job?.message || "任务正在执行" }}</p>
      <small>可以保持此页面，完成后将自动打开报告</small>
    </div>

    <div class="card timeline-card">
      <div
        v-for="(step, index) in steps"
        :key="step.status"
        class="timeline-item"
        :class="stepState(index)"
      >
        <div class="timeline-marker">
          <span v-if="stepState(index) === 'done'">✓</span>
          <span v-else-if="stepState(index) === 'failed'">!</span>
          <i v-else></i>
        </div>
        <div>
          <strong>{{ step.label }}</strong>
          <small>{{ step.detail }}</small>
        </div>
      </div>
    </div>

    <p v-if="error" class="inline-error">{{ error }}</p>
    <button v-if="error" class="secondary-button" type="button" @click="poll">重新查询状态</button>
  </section>
</template>
