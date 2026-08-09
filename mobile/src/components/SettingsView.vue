<script setup>
import { reactive, ref, watch } from "vue";
import { createApi, normalizeBaseUrl } from "../api";

const props = defineProps({
  initialSettings: { type: Object, required: true },
});
const emit = defineEmits(["saved"]);

const form = reactive({
  apiBaseUrl: props.initialSettings.apiBaseUrl || "",
  apiToken: props.initialSettings.apiToken || "",
});
const testing = ref(false);
const testResult = ref(null);

watch(
  () => props.initialSettings,
  (value) => {
    form.apiBaseUrl = value.apiBaseUrl || "";
    form.apiToken = value.apiToken || "";
  },
  { deep: true },
);

async function testConnection() {
  testResult.value = null;
  if (!normalizeBaseUrl(form.apiBaseUrl)) {
    testResult.value = { ok: false, message: "请先填写 HTTPS 地址。" };
    return;
  }
  testing.value = true;
  try {
    const health = await createApi(form).health();
    testResult.value = {
      ok: true,
      message: `连接成功 · 后端 v${health.version} · DeepSeek ${health.deepseek_configured ? "已配置" : "未配置"}`,
    };
  } catch (error) {
    testResult.value = { ok: false, message: error.message };
  } finally {
    testing.value = false;
  }
}

function save() {
  if (!normalizeBaseUrl(form.apiBaseUrl)) {
    testResult.value = { ok: false, message: "请填写 Tailscale Serve 显示的 HTTPS 地址。" };
    return;
  }
  emit("saved", { ...form, apiBaseUrl: normalizeBaseUrl(form.apiBaseUrl) });
}
</script>

<template>
  <section class="view-stack">
    <div class="page-title-row no-back">
      <div>
        <span class="section-kicker">PRIVATE NETWORK</span>
        <h1>连接设置</h1>
        <p>手机通过 Tailscale 私有网络访问你电脑上的分析服务。</p>
      </div>
    </div>

    <div class="card settings-card">
      <label class="field-label" for="base-url">Tailscale HTTPS 地址</label>
      <input
        id="base-url"
        v-model="form.apiBaseUrl"
        class="text-input"
        inputmode="url"
        autocomplete="off"
        placeholder="https://电脑名.xxxx.ts.net"
      />
      <p class="field-help">双击“启动股票AI手机服务”后，终端会显示此地址。不要填写127.0.0.1。</p>

      <label class="field-label" for="api-token">后端访问令牌（可选）</label>
      <input
        id="api-token"
        v-model="form.apiToken"
        class="text-input"
        type="password"
        autocomplete="off"
        placeholder="与电脑 .env.local 保持一致"
      />

      <div v-if="testResult" class="test-result" :class="{ success: testResult.ok }">
        <span>{{ testResult.ok ? "✓" : "!" }}</span>
        {{ testResult.message }}
      </div>

      <button class="secondary-button" type="button" :disabled="testing" @click="testConnection">
        {{ testing ? "正在测试" : "测试连接" }}
      </button>
      <button class="primary-button" type="button" @click="save">保存并返回首页</button>
    </div>

    <div class="setup-steps">
      <h2>电脑端使用顺序</h2>
      <div><b>1</b><span>打开并登录 Tailscale</span></div>
      <div><b>2</b><span>双击启动“股票AI手机服务”</span></div>
      <div><b>3</b><span>将终端显示的 HTTPS 地址填到上方</span></div>
      <div><b>4</b><span>手机保持 Tailscale 连接状态</span></div>
    </div>
  </section>
</template>
