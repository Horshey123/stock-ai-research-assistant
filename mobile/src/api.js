export function normalizeBaseUrl(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function errorMessage(payload, fallback) {
  if (!payload) return fallback;
  if (typeof payload === "string") return payload;
  if (typeof payload.detail === "string") return payload.detail;
  if (payload.detail) return JSON.stringify(payload.detail);
  return fallback;
}

export function createApi(settings) {
  const baseUrl = normalizeBaseUrl(settings?.apiBaseUrl);
  const token = String(settings?.apiToken || "").trim();

  async function request(path, options = {}) {
    if (!baseUrl) {
      throw new Error("请先在设置中填写 Tailscale HTTPS 地址。");
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      options.timeout || 20000,
    );

    try {
      const response = await fetch(`${baseUrl}${path}`, {
        method: options.method || "GET",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "X-API-Key": token } : {}),
        },
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
      });

      const text = await response.text();
      let payload = null;
      if (text) {
        try {
          payload = JSON.parse(text);
        } catch {
          payload = text;
        }
      }

      if (!response.ok) {
        throw new Error(
          errorMessage(payload, `接口请求失败（${response.status}）`),
        );
      }
      return payload;
    } catch (error) {
      if (error?.name === "AbortError") {
        throw new Error("请求超时，请确认电脑后端和 Tailscale 已启动。");
      }
      if (error instanceof TypeError) {
        throw new Error("无法连接电脑后端，请检查 Tailscale 地址和服务状态。");
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  return {
    health: () => request("/api/v1/health", { timeout: 8000 }),
    createJob: (code, refreshData = false) =>
      request("/api/v1/analysis-jobs", {
        method: "POST",
        body: {
          code,
          refresh_data: refreshData,
          reuse_hours: refreshData ? 0 : 24,
        },
      }),
    getJob: (jobId) => request(`/api/v1/analysis-jobs/${jobId}`),
    getReport: (reportId) => request(`/api/v1/reports/${reportId}`, { timeout: 30000 }),
    getLatestReport: (code) =>
      request(`/api/v1/stocks/${code}/latest-report`, { timeout: 30000 }),
    listReports: (code) => request(`/api/v1/stocks/${code}/reports?limit=30`),
  };
}
