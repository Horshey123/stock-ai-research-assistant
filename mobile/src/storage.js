const SETTINGS_KEY = "stock-ai-mobile-settings-v1";
const RECENT_KEY = "stock-ai-mobile-reports-v1";

export function loadSettings() {
  try {
    return {
      apiBaseUrl: "",
      apiToken: "",
      ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}"),
    };
  } catch {
    return { apiBaseUrl: "", apiToken: "" };
  }
}

export function saveSettings(settings) {
  const value = {
    apiBaseUrl: String(settings.apiBaseUrl || "").trim().replace(/\/+$/, ""),
    apiToken: String(settings.apiToken || "").trim(),
  };
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(value));
  return value;
}

export function loadRecentReports() {
  try {
    const reports = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
    return Array.isArray(reports) ? reports : [];
  } catch {
    return [];
  }
}

export function rememberReport(report) {
  if (!report?.id) return loadRecentReports();
  const item = {
    id: report.id,
    code: report.code,
    stock_name: report.stock_name || report.analysis?.stock?.name || "",
    total_score: report.total_score ?? report.analysis?.overall?.total_score ?? null,
    rating: report.rating || report.analysis?.overall?.rating || "",
    created_at: report.created_at || new Date().toISOString(),
  };
  const next = [
    item,
    ...loadRecentReports().filter((current) => current.id !== item.id),
  ].slice(0, 30);
  localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  return next;
}
