const {
  getAnalysisJob,
  getErrorMessage,
} = require("../../utils/api");

const STATUS_ORDER = [
  "queued",
  "fetching_data",
  "preparing_context",
  "analyzing",
  "validating",
  "completed",
];

const STATUS_TEXT = {
  queued: "任务已进入队列",
  fetching_data: "正在获取股票数据",
  preparing_context: "正在提取关键内容",
  analyzing: "AI 正在生成分析",
  validating: "正在校验报告",
  completed: "分析完成",
  failed: "分析失败",
};

const STEP_DEFINITIONS = [
  { key: "queued", label: "创建任务", desc: "任务已提交到后端" },
  { key: "fetching_data", label: "获取数据", desc: "行情、财务、公告和新闻" },
  { key: "preparing_context", label: "整理数据", desc: "提取关键指标与确定性事实" },
  { key: "analyzing", label: "AI 分析", desc: "生成价值、走势与风险判断" },
  { key: "validating", label: "校验报告", desc: "核对评分和关键数字" },
  { key: "completed", label: "生成报告", desc: "保存分析结果" },
];

function buildSteps(status) {
  const currentIndex = STATUS_ORDER.indexOf(status);
  return STEP_DEFINITIONS.map((step, index) => {
    let state = "waiting";
    if (currentIndex > index || status === "completed") {
      state = "done";
    } else if (currentIndex === index) {
      state = "active";
    }
    return { ...step, state };
  });
}

Page({
  data: {
    jobId: "",
    code: "",
    status: "queued",
    statusText: STATUS_TEXT.queued,
    progress: 0,
    message: "正在读取任务状态……",
    error: "",
    stopped: false,
    steps: buildSteps("queued"),
  },

  onLoad(options) {
    if (!options.jobId) {
      wx.showModal({
        title: "缺少任务编号",
        content: "请返回首页重新提交分析。",
        showCancel: false,
        success: () => wx.reLaunch({ url: "/pages/index/index" }),
      });
      return;
    }

    this.setData({
      jobId: options.jobId,
      code: options.code || "",
    });
    this._stopped = false;
    this._networkFailures = 0;
    this.pollJob();
  },

  onUnload() {
    this._stopped = true;
    if (this._timer) {
      clearTimeout(this._timer);
    }
  },

  scheduleNext(delay = 1500) {
    if (this._stopped) {
      return;
    }
    this._timer = setTimeout(() => this.pollJob(), delay);
  },

  async pollJob() {
    if (this._stopped || this._requesting) {
      return;
    }

    this._requesting = true;
    try {
      const job = await getAnalysisJob(this.data.jobId);
      this._networkFailures = 0;
      this.setData({
        code: job.code || this.data.code,
        status: job.status,
        statusText: STATUS_TEXT[job.status] || "正在处理",
        progress: job.progress || 0,
        message: job.message || "",
        error: job.error || "",
        stopped: job.status === "failed",
        steps: buildSteps(job.status),
      });

      if (job.status === "completed" && job.report_id) {
        this._stopped = true;
        this._timer = setTimeout(() => {
          wx.redirectTo({
            url: `/pages/report/report?reportId=${job.report_id}&code=${job.code}`,
          });
        }, 700);
      } else if (job.status !== "failed") {
        this.scheduleNext();
      } else {
        this._stopped = true;
      }
    } catch (error) {
      this._networkFailures += 1;
      const shouldStop = this._networkFailures >= 5;
      this.setData({
        statusText: shouldStop ? "暂时无法连接后端" : "连接中断，正在重试",
        message: getErrorMessage(error),
        stopped: shouldStop,
      });
      if (shouldStop) {
        this._stopped = true;
      } else {
        this.scheduleNext(2200);
      }
    } finally {
      this._requesting = false;
    }
  },

  retryPoll() {
    this._stopped = false;
    this._networkFailures = 0;
    this.setData({
      stopped: false,
      error: "",
      message: "正在重新连接后端……",
    });
    this.pollJob();
  },

  backHome() {
    wx.reLaunch({
      url: `/pages/index/index?code=${this.data.code}`,
    });
  },
});
