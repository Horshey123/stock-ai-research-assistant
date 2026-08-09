<script setup>
import { computed, nextTick, ref, watch } from "vue";
import { createApi } from "./api";
import { loadRecentReports, loadSettings, rememberReport, saveSettings } from "./storage";
import BottomNav from "./components/BottomNav.vue";
import HistoryView from "./components/HistoryView.vue";
import HomeView from "./components/HomeView.vue";
import ProgressView from "./components/ProgressView.vue";
import ReportView from "./components/ReportView.vue";
import SettingsView from "./components/SettingsView.vue";

const settings = ref(loadSettings());
const activeView = ref(settings.value.apiBaseUrl ? "home" : "settings");
const currentJob = ref(null);
const currentReport = ref(null);
const recentReports = ref(loadRecentReports());

const api = computed(() => createApi(settings.value));
const navView = computed(() =>
  activeView.value === "progress" ? "home" : activeView.value,
);

watch(activeView, async () => {
  await nextTick();
  window.scrollTo({ top: 0, behavior: "smooth" });
});

function openView(view) {
  if (view === "report" && !currentReport.value) {
    activeView.value = "history";
    return;
  }
  activeView.value = view;
}

function handleJobStarted(job) {
  currentJob.value = job;
  activeView.value = "progress";
}

function handleReportLoaded(report) {
  currentReport.value = report;
  recentReports.value = rememberReport(report);
  activeView.value = "report";
}

function handleSettingsSaved(nextSettings) {
  settings.value = saveSettings(nextSettings);
  activeView.value = "home";
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <button class="brand" type="button" @click="openView('home')">
        <span class="brand-mark">AI</span>
        <span>
          <strong>股研 AI</strong>
          <small>个人研究助手</small>
        </span>
      </button>
      <span class="private-pill"><i></i> 私有连接</span>
    </header>

    <main class="page-container">
      <HomeView
        v-if="activeView === 'home'"
        :api="api"
        :configured="Boolean(settings.apiBaseUrl)"
        @job-started="handleJobStarted"
        @report-loaded="handleReportLoaded"
        @open-settings="openView('settings')"
      />
      <ProgressView
        v-else-if="activeView === 'progress'"
        :api="api"
        :initial-job="currentJob"
        @report-loaded="handleReportLoaded"
        @back="openView('home')"
      />
      <ReportView
        v-else-if="activeView === 'report'"
        :report="currentReport"
      />
      <HistoryView
        v-else-if="activeView === 'history'"
        :api="api"
        :recent-reports="recentReports"
        @report-loaded="handleReportLoaded"
      />
      <SettingsView
        v-else
        :initial-settings="settings"
        @saved="handleSettingsSaved"
      />
    </main>

    <BottomNav
      :active="navView"
      :has-report="Boolean(currentReport)"
      @navigate="openView"
    />
  </div>
</template>
