const {
  getErrorMessage,
  getLatestReport,
  getReport,
} = require("../../utils/api");

const SCORE_CONFIG = [
  { key: "fundamental", label: "基本面", maxScore: 30 },
  { key: "growth", label: "成长性", maxScore: 20 },
  { key: "valuation", label: "估值", maxScore: 20 },
  { key: "trend", label: "趋势", maxScore: 15 },
  { key: "risk_control", label: "风险控制", maxScore: 15 },
];

const SECTION_CONFIG = [
  { key: "fundamental", title: "基本面分析" },
  { key: "growth", title: "成长性分析" },
  { key: "valuation", title: "估值分析" },
  { key: "technical", title: "技术与走势" },
  { key: "news_and_events", title: "新闻与事件" },
];

function asList(value) {
  return Array.isArray(value) ? value : [];
}

function formatDate(value) {
  if (!value) {
    return "";
  }
  return String(value).replace("T", " ").replace(/\+.*$/, "").slice(0, 19);
}

function buildViewModel(apiReport) {
  const data = apiReport.analysis || {};
  const stock = data.stock || {};
  const overall = data.overall || {};
  const scorecard = data.scorecard || {};
  const analysis = data.analysis || {};
  const outlook = data.outlook || {};
  const actionPlan = data.action_plan || {};
  const dataQuality = data.data_quality || {};
  const metadata = data.analysis_metadata || {};
  const validation = data.validation || {};

  const scoreCards = SCORE_CONFIG.map((config) => {
    const item = scorecard[config.key] || {};
    const score = Number(item.score || 0);
    return {
      ...config,
      score,
      reason: item.reason || "暂无说明",
      percent: Math.min(100, Math.max(0, (score / config.maxScore) * 100)),
    };
  });

  const sections = SECTION_CONFIG.map((config) => {
    const item = analysis[config.key] || {};
    return {
      ...config,
      conclusion: item.conclusion || "暂无结论",
      evidence: asList(item.evidence),
      risks: asList(item.risks),
      positiveEvents: asList(item.positive_events),
      negativeEvents: asList(item.negative_events),
      uncertainEvents: asList(item.uncertain_events),
      unknowns: asList(item.unknowns),
    };
  });

  const scenarios = asList(outlook.scenarios).map((item, index) => ({
    name: item.name || `情景${index + 1}`,
    conditions: asList(item.conditions),
    expectedDirection: item.expected_direction || "",
    response: item.response || "",
    tone: index === 0 ? "positive" : index === 2 ? "negative" : "neutral",
  }));

  const verified = data.verified_facts || {};
  const marketPosition = verified.market_position || {};
  const valuation = verified.valuation || {};

  return {
    id: apiReport.id,
    code: stock.code || apiReport.code,
    name: stock.name || apiReport.stock_name || "股票分析",
    industry: stock.industry || "行业信息暂缺",
    score: Number(overall.total_score || apiReport.total_score || 0),
    rating: overall.rating || apiReport.rating || "待评估",
    confidence: overall.confidence || "未知",
    summary: overall.summary || "暂无摘要",
    scoreCards,
    sections,
    shortTerm: {
      title: "短期展望",
      horizon: (outlook.short_term || {}).horizon || "",
      view: (outlook.short_term || {}).view || "暂无判断",
      drivers: asList((outlook.short_term || {}).drivers),
      invalidations: asList(
        (outlook.short_term || {}).invalidation_conditions
      ),
    },
    mediumTerm: {
      title: "中期展望",
      horizon: (outlook.medium_term || {}).horizon || "",
      view: (outlook.medium_term || {}).view || "暂无判断",
      drivers: asList((outlook.medium_term || {}).drivers),
      invalidations: asList(
        (outlook.medium_term || {}).invalidation_conditions
      ),
    },
    scenarios,
    stance: actionPlan.stance || overall.rating || "待观察",
    suitableFor: asList(actionPlan.suitable_for),
    watchIndicators: asList(actionPlan.watch_indicators),
    riskNotes: asList(actionPlan.position_and_risk_notes),
    availableSections: asList(dataQuality.available_sections),
    missingSections: asList(dataQuality.missing_sections),
    limitations: asList(dataQuality.limitations),
    disclaimer:
      data.disclaimer || "本报告仅用于个人研究，不构成投资建议。",
    generatedAt: formatDate(
      metadata.generated_at || apiReport.created_at
    ),
    model: metadata.model || "",
    validationStatus: validation.status || "",
    validationWarnings: asList(validation.warnings).map(
      (item) => item.message || String(item)
    ),
    latestTradeDate: verified.latest_trade_date || "",
    latestClose:
      marketPosition.latest_close === undefined
        ? "--"
        : marketPosition.latest_close,
    peTtm: valuation.pe_ttm === undefined ? "--" : valuation.pe_ttm,
    pbMrq: valuation.pb_mrq === undefined ? "--" : valuation.pb_mrq,
  };
}

Page({
  data: {
    reportId: "",
    code: "",
    loading: true,
    error: "",
    report: null,
  },

  onLoad(options) {
    this.setData({
      reportId: options.reportId || "",
      code: options.code || "",
    });
    this.loadReport();
  },

  async loadReport() {
    this.setData({ loading: true, error: "" });
    try {
      let result;
      if (this.data.reportId) {
        result = await getReport(this.data.reportId);
      } else if (this.data.code) {
        result = await getLatestReport(this.data.code);
      } else {
        throw new Error("缺少报告编号和股票代码。");
      }
      this.setData({
        reportId: result.id,
        code: result.code,
        report: buildViewModel(result),
      });
    } catch (error) {
      this.setData({ error: getErrorMessage(error) });
    } finally {
      this.setData({ loading: false });
    }
  },

  copySummary() {
    if (!this.data.report) {
      return;
    }
    const report = this.data.report;
    wx.setClipboardData({
      data: `${report.name}（${report.code}）\n综合评分：${report.score}\n评级：${report.rating}\n${report.summary}`,
    });
  },

  backHome() {
    wx.reLaunch({
      url: `/pages/index/index?code=${this.data.code}`,
    });
  },

  onShareAppMessage() {
    const report = this.data.report;
    return {
      title: report
        ? `${report.name} AI 分析：${report.score}分`
        : "AI 股票研究助手",
      path: `/pages/report/report?reportId=${this.data.reportId}&code=${this.data.code}`,
    };
  },
});
