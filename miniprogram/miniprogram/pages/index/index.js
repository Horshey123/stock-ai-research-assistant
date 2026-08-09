const {
  createAnalysisJob,
  getErrorMessage,
  getLatestReport,
  healthCheck,
} = require("../../utils/api");

Page({
  data: {
    code: "",
    refreshData: false,
    submitting: false,
    latestLoading: false,
    serviceStatus: "checking",
    serviceText: "正在连接后端",
    examples: [
      { code: "600519", name: "贵州茅台" },
      { code: "000001", name: "平安银行" },
      { code: "300750", name: "宁德时代" },
    ],
  },

  onLoad(options) {
    if (options.code) {
      this.setData({ code: String(options.code).slice(0, 6) });
    }
  },

  onShow() {
    this.checkService();
  },

  async checkService() {
    this.setData({
      serviceStatus: "checking",
      serviceText: "正在连接后端",
    });
    try {
      const result = await healthCheck();
      this.setData({
        serviceStatus: result.status === "ok" ? "online" : "offline",
        serviceText:
          result.status === "ok" ? "后端服务已连接" : "后端服务异常",
      });
    } catch (error) {
      this.setData({
        serviceStatus: "offline",
        serviceText: "后端未连接，请先启动 FastAPI",
      });
    }
  },

  onCodeInput(event) {
    const code = String(event.detail.value || "")
      .replace(/\D/g, "")
      .slice(0, 6);
    this.setData({ code });
  },

  chooseExample(event) {
    this.setData({ code: event.currentTarget.dataset.code });
  },

  onRefreshChange(event) {
    this.setData({ refreshData: event.detail.value });
  },

  validateCode() {
    if (!/^\d{6}$/.test(this.data.code)) {
      wx.showToast({
        title: "请输入6位股票代码",
        icon: "none",
      });
      return false;
    }
    return true;
  },

  async submitAnalysis() {
    if (!this.validateCode() || this.data.submitting) {
      return;
    }

    this.setData({ submitting: true });
    try {
      const job = await createAnalysisJob(
        this.data.code,
        this.data.refreshData
      );
      if (job.status === "completed" && job.report_id) {
        wx.navigateTo({
          url: `/pages/report/report?reportId=${job.report_id}&code=${job.code}`,
        });
        return;
      }
      wx.navigateTo({
        url: `/pages/progress/progress?jobId=${job.id}&code=${job.code}`,
      });
    } catch (error) {
      wx.showModal({
        title: "提交失败",
        content: getErrorMessage(error),
        showCancel: false,
      });
    } finally {
      this.setData({ submitting: false });
    }
  },

  async viewLatestReport() {
    if (!this.validateCode() || this.data.latestLoading) {
      return;
    }

    this.setData({ latestLoading: true });
    try {
      const report = await getLatestReport(this.data.code);
      wx.navigateTo({
        url: `/pages/report/report?reportId=${report.id}&code=${report.code}`,
      });
    } catch (error) {
      wx.showModal({
        title: "未找到报告",
        content:
          error.statusCode === 404
            ? "该股票还没有历史报告，请先生成一次分析。"
            : getErrorMessage(error),
        showCancel: false,
      });
    } finally {
      this.setData({ latestLoading: false });
    }
  },
});
