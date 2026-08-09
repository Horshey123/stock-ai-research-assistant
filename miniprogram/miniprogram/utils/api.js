function getBaseUrl() {
  const app = getApp();
  return app.globalData.apiBaseUrl.replace(/\/$/, "");
}

function getErrorMessage(error) {
  if (!error) {
    return "请求失败，请稍后重试。";
  }
  if (typeof error === "string") {
    return error;
  }
  if (error.detail) {
    return typeof error.detail === "string"
      ? error.detail
      : JSON.stringify(error.detail);
  }
  return error.errMsg || error.message || "请求失败，请稍后重试。";
}

function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getBaseUrl()}${path}`,
      method: options.method || "GET",
      data: options.data,
      timeout: options.timeout || 15000,
      header: {
        "content-type": "application/json",
      },
      success(response) {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data);
          return;
        }
        reject({
          statusCode: response.statusCode,
          detail:
            response.data && response.data.detail
              ? response.data.detail
              : `接口返回 ${response.statusCode}`,
        });
      },
      fail(error) {
        reject(error);
      },
    });
  });
}

function healthCheck() {
  return request("/api/v1/health");
}

function createAnalysisJob(code, refreshData = false) {
  return request("/api/v1/analysis-jobs", {
    method: "POST",
    data: {
      code,
      refresh_data: refreshData,
      reuse_hours: refreshData ? 0 : 24,
    },
  });
}

function getAnalysisJob(jobId) {
  return request(`/api/v1/analysis-jobs/${jobId}`);
}

function getReport(reportId) {
  return request(`/api/v1/reports/${reportId}`);
}

function getLatestReport(code) {
  return request(`/api/v1/stocks/${code}/latest-report`);
}

module.exports = {
  createAnalysisJob,
  getAnalysisJob,
  getErrorMessage,
  getLatestReport,
  getReport,
  healthCheck,
};
