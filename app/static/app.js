"use strict";
let token = "";
let searchId = "";
let cleanupPlan = null;
let previousJobs = "";
const $ = id => document.getElementById(id);
function node(tag, text = "", attrs = {}) {
  const result = document.createElement(tag);
  if (text) result.textContent = text;
  for (const [key, value] of Object.entries(attrs)) result.setAttribute(key, value);
  return result;
}
function notify(text, error = false) {
  $("notice").textContent = text;
  $("notice").classList.toggle("error", error);
}
async function call(path, options = {}) {
  const headers = {"X-Local-Token": token, ...(options.headers || {})};
  let body = options.body;
  if (body !== undefined && !(body instanceof Blob)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  const response = await fetch(path, {...options, headers, body});
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map(item => item.msg).join("；") : data.detail;
    throw new Error(detail || "请求失败，请重试。");
  }
  return data;
}
function selected(className) {
  return [...document.querySelectorAll("." + className + ":checked")].map(input => input.value);
}
function checkbox(className, value, checked = false) {
  const input = node("input", "", {type: "checkbox", class: className, value});
  input.checked = checked;
  input.setAttribute("aria-label", "选择 " + value);
  return input;
}
async function guarded(action) {
  try { await action(); } catch (error) { notify(error.message, true); }
}
function fileLink(path, label) {
  return node("a", label, {href: "/api/files?path=" + encodeURIComponent(path)});
}
function renderPapers(rows) {
  const picked = new Set(selected("paperCheck"));
  const body = $("papers");
  body.replaceChildren();
  if (!rows.length) {
    const cell = node("td", "", {colspan: "4"});
    const empty = node("div", "", {class: "empty-state"});
    empty.append(node("strong", "资料库还没有论文"));
    empty.append(node("p", "从上方发现一篇论文，或导入已有的本地 PDF。"));
    cell.append(empty);
    const tr = node("tr"); tr.append(cell); body.append(tr); return;
  }
  for (const paper of rows) {
    const tr = node("tr"), choose = node("td"), title = node("td"), status = node("td"), files = node("td");
    choose.append(checkbox("paperCheck", paper.ref, picked.has(paper.ref)));
    title.append(node("strong", paper.ref), node("p", paper.title));
    status.textContent = {
      registered: "已登记", downloaded: "已下载", failed: "处理失败",
      converted_needs_review: "已转换 · 内容待复核"
    }[paper.state] || paper.state;
    for (const file of paper.files) {
      if (!file.exists || file.status !== "present") continue;
      const label = {pdf: "PDF", markdown: "Markdown", validation: "检查记录"}[file.kind];
      if (label) files.append(fileLink(file.path, label), document.createTextNode(" "));
    }
    tr.append(choose, title, status, files); body.append(tr);
  }
}
function renderReports(rows) {
  const picked = new Set(selected("reportCheck"));
  const container = $("reports"); container.replaceChildren();
  if (!rows.length) { container.append(node("p", "暂无简报或周总结。", {class: "hint"})); return; }
  for (const report of rows) {
    const line = node("div", "", {class: "reportRow"});
    line.append(checkbox("reportCheck", report.id, picked.has(report.id)));
    const detail = node("div");
    detail.append(node("strong", (report.kind === "weekly" ? "周总结 " : "简报 ") + report.period),
      node("small", "编号：" + report.id));
    detail.append(node("small", "论文：" + (report.refs.join("、") || "无新增")));
    line.append(detail);
    line.append(report.exists ? fileLink(report.path, "下载 Markdown") : node("span", "文件已删除", {class: "hint"}));
    container.append(line);
  }
}
function renderJobs(rows) {
  const box = $("jobs"); box.replaceChildren();
  if (!rows.length) { box.append(node("p", "暂无任务。", {class: "hint"})); return; }
  const labels = {queued: "排队中", running: "正在处理", succeeded: "已完成",
    partial: "部分完成", failed: "失败", interrupted: "中断"};
  for (const job of rows.slice(0, 15)) {
    const item = node("div", "", {class: "job"});
    const kinds = {collect: "收集论文", import: "导入 PDF", brief: "生成简报", weekly: "每周总结", "catch-up": "补充周报"};
    item.append(node("strong", (kinds[job.kind] || job.kind) + " · " + (labels[job.status] || job.status)));
    item.append(node("small", new Date(job.created).toLocaleString("zh-CN", {timeZone: "Asia/Shanghai"})));
    if (job.error) item.append(node("p", job.error, {class: "error"}));
    if (job.result) {
      const details = node("details"); details.append(node("summary", "查看处理结果"));
      details.append(node("pre", JSON.stringify(job.result, null, 2))); item.append(details);
    }
    box.append(item);
  }
}
async function refresh() {
  const [papers, reports, jobs] = await Promise.all([call("/api/papers"), call("/api/reports"), call("/api/jobs")]);
  renderPapers(papers); renderReports(reports); renderJobs(jobs);
  $("statPapers").textContent = String(papers.length);
  $("statPdfs").textContent = String(papers.reduce((count, paper) => count + paper.files.filter(file => file.kind === "pdf" && file.exists && file.status === "present").length, 0));
  $("statReports").textContent = String(reports.filter(report => report.exists).length);
  $("statJobs").textContent = String(jobs.filter(job => job.status === "queued" || job.status === "running").length);
  previousJobs = JSON.stringify(jobs.map(job => [job.id, job.status, job.updated]));
}
async function submitJob(path, body, extra = {}) {
  const result = await call(path, {method: "POST", body, ...extra});
  notify("任务已提交。处理进度会自动更新；完成前请保持服务运行。");
  await refresh();
  return result;
}
$("configForm").addEventListener("submit", event => {
  event.preventDefault();
  guarded(async () => {
    const body = {model: $("model").value.trim()};
    if ($("apiKey").value) body.api_key = $("apiKey").value;
    const data = await call("/api/config", {method: "PUT", body});
    $("apiKey").value = "";
    $("configState").textContent = data.key_configured ? "密钥已配置（不显示内容）" : "尚未配置密钥";
    notify("DeepSeek 配置已保存。");
  });
});
$("searchForm").addEventListener("submit", event => {
  event.preventDefault();
  guarded(async () => {
    notify("正在检索论文元数据…");
    const data = await call("/api/search", {method: "POST", body: {
      mode: $("mode").value, days: Number($("days").value),
      limit: Number($("limit").value), query: $("query").value
    }});
    searchId = data.search_id;
    const box = $("candidates"); box.replaceChildren();
    data.candidates.forEach((paper, i) => {
      const row = node("label", "", {class: "candidate"});
      row.append(checkbox("candidateCheck", String(i + 1)));
      const info = node("span");
      info.append(node("strong", paper.title));
      const votes = paper.evidence?.upvotes;
      info.append(node("small", paper.source_id + " · " + paper.published_at.slice(0, 10)
        + (votes === undefined ? "" : " · 社区票数 " + votes)));
      info.append(node("p", paper.abstract || "暂无摘要"));
      row.append(info); box.append(row);
    });
    $("collectControls").hidden = !data.candidates.length;
    notify(data.candidates.length ? "请勾选想收集的论文，再点击收集。" : "该范围未找到论文。");
  });
});
$("collectButton").addEventListener("click", () => guarded(async () => {
  const indices = selected("candidateCheck").map(Number);
  if (!indices.length) throw new Error("请先勾选候选论文。");
  await submitJob("/api/collect", {search_id: searchId, indices,
    summarize: $("summarize").checked, restore: $("restore").checked});
}));
$("importForm").addEventListener("submit", event => {
  event.preventDefault();
  guarded(async () => {
    const file = $("pdf").files[0];
    if (!file) throw new Error("请选择 PDF。");
    if (file.size > 50 * 1024 * 1024) throw new Error("PDF 超过 50 MiB。");
    const params = new URLSearchParams({title: $("title").value, filename: file.name});
    await submitJob("/api/import?" + params, file, {headers: {"Content-Type": "application/pdf"}});
    $("pdf").value = "";
  });
});
$("briefButton").addEventListener("click", () => guarded(async () => {
  const refs = selected("paperCheck");
  if (!refs.length) throw new Error("请先在“我的论文”中勾选论文。");
  await submitJob("/api/brief", {refs});
}));
$("weeklyForm").addEventListener("submit", event => {
  event.preventDefault();
  guarded(() => submitJob("/api/weekly", {week: $("week").value.trim() || null, force: $("force").checked}));
});
$("catchUpButton").addEventListener("click", () => guarded(() => submitJob("/api/catch-up")));
$("refreshButton").addEventListener("click", () => guarded(async () => { await refresh(); notify("资料库已刷新。"); }));
$("cleanupForm").addEventListener("submit", event => {
  event.preventDefault();
  guarded(async () => {
    cleanupPlan = await call("/api/cleanup/preview", {method: "POST", body: {
      mode: $("cleanupMode").value, refs: selected("paperCheck"), reports: selected("reportCheck")
    }});
    $("preview").hidden = false;
    $("previewSize").textContent = cleanupPlan.targets.length + " 个文件，预计释放 "
      + (cleanupPlan.bytes_total / 1024 / 1024).toFixed(2) + " MiB。编号索引继续保留。";
    $("previewFiles").textContent = cleanupPlan.targets.map(item => item.path).join("\n") || "没有符合条件的文件。";
    $("deleteButton").disabled = cleanupPlan.targets.length === 0;
  });
});
$("cancelDelete").addEventListener("click", () => { cleanupPlan = null; $("preview").hidden = true; });
$("deleteButton").addEventListener("click", () => guarded(async () => {
  if (!cleanupPlan) return;
  if (!confirm("确认永久删除预览中的 " + cleanupPlan.targets.length + " 个文件？此操作不经过回收站。")) return;
  const data = await call("/api/cleanup/execute", {method: "POST", body: {
    plan_id: cleanupPlan.id, confirmation: "DELETE"
  }});
  $("preview").hidden = true; cleanupPlan = null;
  notify("已删除 " + data.deleted.length + " 个文件；失败 " + data.failed.length + " 个。", data.failed.length > 0);
  await refresh();
}));
async function init() {
  token = (await call("/api/session")).token;
  const config = await call("/api/config");
  $("model").value = config.model;
  $("configState").textContent = config.key_configured ? "密钥已配置（不显示内容）" : "尚未配置密钥；导入本地 PDF 无需密钥";
  $("libraryPath").textContent = config.library;
  await refresh();
  $("serviceState").textContent = "本机服务已连接";
  notify("已连接本机服务。你可以手动检索论文或导入本地 PDF。");
  setInterval(() => guarded(async () => {
    const jobs = await call("/api/jobs");
    const fingerprint = JSON.stringify(jobs.map(job => [job.id, job.status, job.updated]));
    if (fingerprint !== previousJobs) await refresh();
  }), 3000);
}
guarded(init);
