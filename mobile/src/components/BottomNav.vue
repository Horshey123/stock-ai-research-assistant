<script setup>
defineProps({
  active: { type: String, default: "home" },
  hasReport: { type: Boolean, default: false },
});

const emit = defineEmits(["navigate"]);

const items = [
  { id: "home", label: "分析", icon: "⌁" },
  { id: "report", label: "报告", icon: "▤" },
  { id: "history", label: "历史", icon: "◷" },
  { id: "settings", label: "设置", icon: "⚙" },
];
</script>

<template>
  <nav class="bottom-nav" aria-label="主导航">
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      :class="{ active: active === item.id }"
      @click="emit('navigate', item.id)"
    >
      <span class="nav-icon">{{ item.icon }}</span>
      <span>{{ item.label }}</span>
    </button>
  </nav>
</template>
