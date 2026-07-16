// Novel Agent 前端:Codex 式聊天 + 步骤展示 + 多格式 + 系统打磨
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

let currentProject = null;
let chatHistory = [];
let config = { default: "", models: [], ready: true };
let agentsList = [];
let currentAgent = "orchestrator";        // 入口 agent(固定为 orchestrator,用户不能手选)
let activeAgent = "orchestrator";           // 当前活跃 agent(由 delegate 事件自动更新)
let workflowPhases = [];
let readonlyAgents = [];
const AGENT_LABELS = {
  orchestrator: "总编",
  "story-architect": "架构师",
  "narrative-writer": "主笔",
  "character-designer": "角色师",
  "consistency-checker": "质检员",
  "story-explorer": "资料员",
  worldbuilder: "设定管理员",
  // 兼容旧名
  planner: "策划师", writer: "主笔", editor: "编辑",
};
const AGENT_ICONS = {
  orchestrator: "🎯",
  "story-architect": "📐",
  "narrative-writer": "✍️",
  "character-designer": "👤",
  "consistency-checker": "🔍",
  "story-explorer": "📊",
  worldbuilder: "🌐",
  // 兼容旧名
  planner: "📐", writer: "✍️", editor: "🔧",
};

// ---------- 工具 ----------
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  return res.json();
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// 极简 markdown 渲染 (无需外部依赖)
function renderMd(src) {
  if (!src) return "";
  let s = esc(src);
  // 代码块
  s = s.replace(/```([\s\S]*?)```/g, (_, c) => `<pre><code>${c.replace(/^\n/, "")}</code></pre>`);
  // 标题
  s = s.replace(/^### (.*)$/gm, "<h3>$1</h3>")
       .replace(/^## (.*)$/gm, "<h3>$1</h3>")
       .replace(/^# (.*)$/gm, "<h3>$1</h3>");
  // 粗体/斜体/行内代码
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
       .replace(/`([^`]+)`/g, "<code>$1</code>");
  // 引用
  s = s.replace(/^&gt; (.*)$/gm, "<blockquote>$1</blockquote>");
  // 列表
  const lines = s.split("\n");
  let out = [], inUl = false, inOl = false;
  for (const ln of lines) {
    if (/^- /.test(ln)) {
      if (!inUl) { out.push("<ul>"); inUl = true; }
      out.push(`<li>${ln.slice(2)}</li>`);
    } else if (/^\d+\. /.test(ln)) {
      if (!inOl) { out.push("<ol>"); inOl = true; }
      out.push(`<li>${ln.replace(/^\d+\. /, "")}</li>`);
    } else {
      if (inUl) { out.push("</ul>"); inUl = false; }
      if (inOl) { out.push("</ol>"); inOl = false; }
      out.push(ln);
    }
  }
  if (inUl) out.push("</ul>");
  if (inOl) out.push("</ol>");
  s = out.join("\n");
  // 段落 (连续两个换行)
  s = s.split(/\n{2,}/).map((b) => /^<(h3|ul|ol|pre|blockquote)/.test(b.trim()) ? b : `<p>${b.replace(/\n/g, "<br>")}</p>`).join("\n");
  return s;
}

// ---------- toast ----------
function toast(msg, type = "ok", ms = 3000) {
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = msg;
  $("#toast-wrap").appendChild(t);
  setTimeout(() => {
    t.style.opacity = "0";
    t.style.transition = ".3s";
    setTimeout(() => t.remove(), 300);
  }, ms);
}

// ---------- 配置/模型 ----------
async function loadConfig() {
  config = await api("/api/config");
  $("#model-label").textContent = config.default.split("/").pop();
  // 就绪提示
  if (!config.ready) {
    toast(`模型 ${config.default} 未配置 API Key,请设置环境变量或编辑 config.yaml`, "warn", 6000);
  }
  refreshStatus();
}

// 顶栏模型按钮:直接打开设置面板让用户去配置/选择
$("#model-btn").addEventListener("click", () => {
  $("#settings-btn").click();
});

function refreshStatus() {
  const sb = $("#status-bar");
  if (!currentProject) {
    sb.innerHTML = config.ready ? "" : `<span class="pill warn">⚠ 未配置 Key</span>`;
    return;
  }
  const st = currentProject.stats || {};
  const parts = [
    `<span class="pill">${st.chapters || 0} 章</span>`,
    `<span class="pill"><b>${(st.total_chars || 0).toLocaleString()}</b> 字</span>`,
  ];
  if (!config.ready) parts.push(`<span class="pill warn">⚠ Key</span>`);
  sb.innerHTML = parts.join("");
}

// ---------- 项目 ----------
async function loadProjects() {
  const list = await api("/api/projects");
  const menu = $("#proj-menu");
  menu.innerHTML = `<button class="proj-opt" id="new-project-opt">+ 新建项目…</button>` +
    list.map((p) => `<button class="proj-opt" data-id="${p.id}">${esc(p.name)}</button>`).join("");
  $$("#proj-menu .proj-opt").forEach((el) => {
    if (el.id === "new-project-opt") {
      el.onclick = () => $("#proj-modal").classList.add("show");
    } else {
      el.onclick = () => { selectProject(el.dataset.id); closeSidebar(); };
    }
  });
  // 当前项目标签
  if (currentProject) {
    $("#proj-select-label").textContent = currentProject.name;
  } else if (list.length) {
    $("#proj-select-label").textContent = "选择项目 ▾";
  }
}

// 项目选择器下拉
$("#proj-select-btn").addEventListener("click", (e) => {
  e.stopPropagation();
  $("#proj-select-btn").parentElement.classList.toggle("open");
});
document.addEventListener("click", () => {
  $("#proj-select-btn")?.parentElement.classList.remove("open");
});

async function selectProject(pid) {
  const p = await api(`/api/projects/${pid}`);
  currentProject = p;
  $("#proj-info").textContent = p.name + (p.genre ? ` · ${p.genre}` : "");
  $("#proj-select-label").textContent = p.name;
  // 拉取已上传素材
  let sources = [];
  try { sources = await api(`/api/projects/${pid}/sources`); } catch { sources = []; }
  currentProject.sources = sources;
  renderTree();
  loadProjects();
  await loadMessages(pid);
  refreshStatus();
}

// ---------- 文件树 ----------
const KIND_META = {
  character: { label: "角色", icon: "👤" },
  location: { label: "地点", icon: "📍" },
  lore: { label: "世界观", icon: "🌐" },
  timeline: { label: "时间线", icon: "⏱" },
};
const FILE_ICON = { chapter: "📄", source: "📚" };

function renderTree() {
  const tree = $("#tree");
  if (!currentProject) {
    tree.innerHTML = `<div class="tree-empty"><div class="tree-empty-icon">📂</div>
      <p>选择或新建一个项目</p><p class="muted">章节、设定、素材将在此以文件树形式展示</p></div>`;
    return;
  }
  const p = currentProject;
  const chs = (p.chapters || []).slice().sort((a, b) => a.idx - b.idx);
  const elems = p.elements || [];
  const srcs = p.sources || [];

  // 按设定类型分组
  const byKind = {};
  for (const e of elems) {
    (byKind[e.kind] ||= []).push(e);
  }

  const parts = [];
  // 项目信息节点
  parts.push(`<div class="tree-file" data-act="info">
    <span class="ico">⚙️</span><span class="name">项目设置</span>
    <span class="meta">${p.genre || ""}</span></div>`);

  // 章节文件夹
  parts.push(`<div class="tree-folder open" id="f-chapters">
    <div class="tree-folder-head" data-toggle="f-chapters">
      <span class="chev">▸</span><span class="ico">📁</span>
      <span class="name">章节</span><span class="cnt">${chs.length}</span>
    </div><div class="tree-folder-children">`);
  if (!chs.length) {
    parts.push(`<div class="tree-file" style="opacity:.5;cursor:default"><span class="ico">·</span><span class="name">(暂无章节,点对话让 Agent 生成)</span></div>`);
  }
  chs.forEach((c) => {
    const n = (c.content || "").length;
    parts.push(`<div class="tree-file" data-chapter="${c.id}">
      <span class="ico">${FILE_ICON.chapter}</span>
      <span class="name">${String(c.idx + 1).padStart(2, "0")}. ${esc(c.title)}</span>
      <span class="meta">${n ? n + "字" : "草稿"}</span></div>`);
  });
  parts.push(`</div></div>`);

  // 设定文件夹
  parts.push(`<div class="tree-folder open" id="f-elements">
    <div class="tree-folder-head" data-toggle="f-elements">
      <span class="chev">▸</span><span class="ico">📁</span>
      <span class="name">设定</span><span class="cnt">${elems.length}</span>
    </div><div class="tree-folder-children">`);
  if (!elems.length) {
    parts.push(`<div class="tree-file" style="opacity:.5;cursor:default"><span class="ico">·</span><span class="name">(暂无设定,点底部 + 设定 添加)</span></div>`);
  }
  for (const [kind, meta] of Object.entries(KIND_META)) {
    const list = byKind[kind] || [];
    if (!list.length) continue;
    parts.push(`<div class="tree-folder open" id="f-elem-${kind}">
      <div class="tree-folder-head" data-toggle="f-elem-${kind}">
        <span class="chev">▸</span><span class="ico">${meta.icon}</span>
        <span class="name">${meta.label}</span><span class="cnt">${list.length}</span>
      </div><div class="tree-folder-children">`);
    list.forEach((e) => {
      parts.push(`<div class="tree-file" data-element="${e.id}">
        <span class="ico">${meta.icon}</span>
        <span class="name">${esc(e.name)}</span>
        <button class="edel" data-del-elem="${e.id}" title="删除">✕</button></div>`);
    });
    parts.push(`</div></div>`);
  }
  // 未知 kind
  const others = elems.filter((e) => !KIND_META[e.kind]);
  if (others.length) {
    parts.push(`<div class="tree-folder open" id="f-elem-other">
      <div class="tree-folder-head" data-toggle="f-elem-other">
        <span class="chev">▸</span><span class="ico">📁</span>
        <span class="name">其他</span><span class="cnt">${others.length}</span>
      </div><div class="tree-folder-children">`);
    others.forEach((e) => {
      parts.push(`<div class="tree-file" data-element="${e.id}">
        <span class="ico">📄</span><span class="name">${esc(e.name)}</span>
        <button class="edel" data-del-elem="${e.id}" title="删除">✕</button></div>`);
    });
    parts.push(`</div></div>`);
  }
  parts.push(`</div></div>`);

  // 素材库文件夹
  parts.push(`<div class="tree-folder open" id="f-sources">
    <div class="tree-folder-head" data-toggle="f-sources">
      <span class="chev">▸</span><span class="ico">📁</span>
      <span class="name">素材库</span><span class="cnt">${srcs.length}</span>
    </div><div class="tree-folder-children">`);
  if (!srcs.length) {
    parts.push(`<div class="tree-file" style="opacity:.5;cursor:default"><span class="ico">·</span><span class="name">(点顶栏「上传」导入 txt/md/docx/pdf/epub)</span></div>`);
  }
  srcs.forEach((s) => {
    parts.push(`<div class="tree-file" data-source="${esc(s.source)}">
      <span class="ico">${FILE_ICON.source}</span>
      <span class="name">${esc(s.source)}</span>
      <span class="meta">${s.chunks}块</span></div>`);
  });
  parts.push(`</div></div>`);

  tree.innerHTML = parts.join("");

  // 绑定文件夹展开/收起
  tree.querySelectorAll(".tree-folder-head").forEach((h) => {
    h.addEventListener("click", (e) => {
      if (e.target.closest(".edel") || e.target.closest("button")) return;
      h.parentElement.classList.toggle("open");
    });
  });
  // 章节点击
  tree.querySelectorAll("[data-chapter]").forEach((el) => {
    el.addEventListener("click", () => openChapter(el.dataset.chapter));
  });
  // 设定点击 → 打开抽屉预览
  tree.querySelectorAll("[data-element]").forEach((el) => {
    el.addEventListener("click", () => openElement(el.dataset.element));
  });
  // 素材点击 → 预览片段
  tree.querySelectorAll("[data-source]").forEach((el) => {
    el.addEventListener("click", () => openSource(el.dataset.source));
  });
  // 设定删除
  tree.querySelectorAll("[data-del-elem]").forEach((el) => {
    el.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      if (!confirm("删除该设定?")) return;
      await api(`/api/elements/${el.dataset.delElem}`, { method: "DELETE" });
      await selectProject(currentProject.id);
      toast("已删除设定", "ok");
    });
  });
}

// 打开设定预览
function openElement(eid) {
  const e = currentProject.elements.find((x) => x.id === eid);
  if (!e) return;
  const meta = KIND_META[e.kind] || { icon: "📄", label: "设定" };
  drawerChapterId = null;
  $("#drawer-title").textContent = `${meta.label} · ${e.name}`;
  $("#drawer-body").innerHTML =
    `<h3>${meta.icon} ${esc(e.name)}</h3><p class="muted">${esc(e.kind)}</p>` +
    `<h3>详情</h3>${esc(e.detail || "(无)")}`;
  $("#drawer-edit-area").classList.add("hidden");
  $("#drawer-body").classList.remove("hidden");
  $("#drawer-edit").classList.add("hidden");
  $("#drawer-save").classList.add("hidden");
  $("#drawer").classList.add("open");
}

// 打开素材预览(首块文本)
async function openSource(source) {
  drawerChapterId = null;
  $("#drawer-title").textContent = `素材 · ${source}`;
  $("#drawer-body").innerHTML = `<p class="muted">加载中…</p>`;
  $("#drawer").classList.add("open");
  $("#drawer-edit-area").classList.add("hidden");
  $("#drawer-body").classList.remove("hidden");
  // 复用 search 拿片段
  try {
    const r = await api(`/api/projects/${currentProject.id}/search?q=${encodeURIComponent(source.slice(0, 8))}`);
    const snips = (r.results || []).map((x) => esc(x.text)).join("\n\n---\n\n");
    $("#drawer-body").innerHTML = `<h3>📚 ${esc(source)}</h3>${snips || "<p class='muted'>(无内容)</p>"}`;
  } catch {
    $("#drawer-body").innerHTML = `<p class="err">读取失败</p>`;
  }
}

async function loadMessages(pid) {
  const msgs = await api(`/api/projects/${pid}/messages`);
  $("#chat").innerHTML = "";
  chatHistory = [];
  if (msgs.length === 0) {
    showEmpty();
    return;
  }
  for (const m of msgs) {
    if (m.role === "tool") continue;
    if (m.role === "assistant" && m.tool_name === "tool_calls") continue;
    appendMessage(m.role, m.content, false);
  }
  scrollChat();
}

function showEmpty() {
  $("#chat").innerHTML = "";
  const div = document.createElement("div");
  div.className = "empty";
  div.id = "empty-state";
  div.innerHTML = `<div class="empty-icon">✦</div><h2>小说创作 Agent</h2>
    <p>类似 Codex 的协作式小说写作助手。它会自主规划并调用工具完成创作。</p>`;
  $("#chat").appendChild(div);
  rebuildSuggestions();
}

function rebuildSuggestions() {
  const suggs = [
    "查看当前项目状态与进度",
    "继续续写最近一章,2000字",
    "对最近一章做质量检查",
  ];
  const wrap = document.createElement("div");
  wrap.className = "suggestions";
  suggs.forEach((t) => {
    const b = document.createElement("button");
    b.className = "sugg";
    b.textContent = t;
    b.onclick = () => send(t);
    wrap.appendChild(b);
  });
  const es = $("#empty-state");
  if (es) es.appendChild(wrap);
}

// ---------- 对话 ----------
function appendMessage(role, content, streaming) {
  const es = $("#empty-state");
  if (es) es.remove();
  const msg = { role, content: content || "", steps: [], streaming };
  chatHistory.push(msg);
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = `<div class="role ${role}">${role === "user" ? "你" : "Agent"}</div>
    <div class="bubble"></div>`;
  $("#chat").appendChild(div);
  msg.el = div.querySelector(".bubble");
  if (content) {
    if (role === "assistant") msg.el.innerHTML = `<div class="md">${renderMd(content)}</div>`;
    else msg.el.textContent = content;
  }
  scrollChat();
  return msg;
}

function scrollChat() {
  const c = $("#chat");
  c.scrollTop = c.scrollHeight;
}

async function send(text) {
  if (!currentProject) {
    toast("请先创建或选择一个项目", "warn");
    return;
  }
  if (!config.ready) {
    toast("模型未配置 Key,可在顶栏切换已配置的模型", "warn", 5000);
  }
  text = text || $("#input").value.trim();
  if (!text) return;
  $("#input").value = "";
  autoGrow();
  appendMessage("user", text);

  const assistant = appendMessage("assistant", "", true);
  // thinking 占位
  const think = document.createElement("div");
  think.className = "step-head running";
  think.innerHTML = `<span class="dot"></span><span class="label-think">思考中<span class="thinking-dots"></span></span>`;
  assistant.el.appendChild(think);

  try {
    const res = await fetch(`/api/projects/${currentProject.id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: text, agent: "orchestrator" }),
    });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        let evt;
        try { evt = JSON.parse(line.slice(6)); } catch { continue; }
        // 首个事件移除 thinking 占位
        if (think.parentNode && (evt.type === "step" || evt.type === "answer_start" || evt.type === "token")) {
          think.remove();
        }
        handleEvent(evt, assistant);
      }
    }
    if (think.parentNode) think.remove();
  } catch (e) {
    if (think.parentNode) think.remove();
    assistant.el.innerHTML = `<span class="err">连接失败: ${esc(e.message)}</span>`;
  }
  await selectProject(currentProject.id);
}

function handleEvent(evt, assistant) {
  const bubble = assistant.el;
  switch (evt.type) {
    case "start":
      break;
    case "delegate": {
      // 委派事件:显示总编 → 专家 的协同 + 自动更新活跃 agent 芯片
      const fromLbl = evt.from ? (AGENT_LABELS[evt.from] || evt.from) : "上级";
      const toLbl = AGENT_LABELS[evt.to] || evt.to;
      const toIcon = AGENT_ICONS[evt.to] || "↪";
      // OpenClaw 模式:活跃 agent 随委派自动切换(用户无需手选)
      if (evt.to) updateActiveAgent(evt.to);
      const div = document.createElement("div");
      div.className = "delegate-event";
      div.innerHTML = `<span class="del-arrow">↳</span>
        <span class="del-icon">${toIcon}</span>
        <span class="del-text">委派给 <b>${toLbl}</b></span>
        <span class="del-task">${esc((evt.task || "").slice(0, 60))}${evt.task && evt.task.length > 60 ? "…" : ""}</span>`;
      bubble.appendChild(div);
      scrollChat();
      break;
    }
    case "step": {
      const ag = evt.agent || "";
      const agLbl = ag ? (AGENT_LABELS[ag] || ag) : "";
      const agIcon = ag ? (AGENT_ICONS[ag] || "") : "";
      const step = { tool: evt.tool, args: evt.args, thinking: evt.thinking || "", agent: ag };
      assistant.steps.push(step);
      const div = document.createElement("div");
      div.className = "step" + (evt.depth ? " sub-step" : "");
      const depthIndent = evt.depth ? `style="margin-left:${evt.depth * 12}px"` : "";
      div.innerHTML = `<div class="step-head running" ${depthIndent}><span class="dot"></span>
        ${agIcon ? `<span class="step-agent">${agIcon} ${esc(agLbl)}</span>` : ""}
        调用工具 <span class="tool">${esc(evt.tool)}</span></div>
        ${evt.thinking ? `<div class="step-thinking" ${depthIndent}>${esc(evt.thinking)}</div>` : ""}
        <div class="step-args" ${depthIndent}>${esc(JSON.stringify(evt.args, null, 2))}</div>
        <div class="step-result" ${depthIndent}>执行中…</div>`;
      bubble.appendChild(div);
      step.resultEl = div.querySelector(".step-result");
      step.headEl = div.querySelector(".step-head");
      scrollChat();
      break;
    }
    case "observation": {
      const step = assistant.steps[assistant.steps.length - 1];
      if (step) {
        step.resultEl.textContent = prettyResult(evt.result);
        step.headEl.classList.remove("running");
        step.headEl.classList.add("done");
      }
      scrollChat();
      break;
    }
    case "answer_start": {
      assistant.answerEl = document.createElement("div");
      assistant.answerEl.className = "md";
      bubble.appendChild(assistant.answerEl);
      assistant.rawBuf = "";
      const caret = document.createElement("span");
      caret.className = "caret";
      bubble.appendChild(caret);
      break;
    }
    case "token": {
      if (!assistant.answerEl) {
        assistant.answerEl = document.createElement("div");
        assistant.answerEl.className = "md";
        assistant.rawBuf = "";
        bubble.appendChild(assistant.answerEl);
      }
      assistant.rawBuf += evt.text;
      // 流式渲染 markdown (节流:每 token 都渲染,内容小可接受)
      assistant.answerEl.innerHTML = renderMd(assistant.rawBuf);
      scrollChat();
      break;
    }
    case "answer_end": {
      const caret = bubble.querySelector(".caret");
      if (caret) caret.remove();
      break;
    }
    case "error":
      bubble.innerHTML += `<div class="err">错误: ${esc(evt.message)}</div>`;
      break;
    case "done":
      if (!assistant.answerEl) {
        const note = document.createElement("div");
        note.style.color = "var(--green)";
        note.style.fontSize = "13px";
        note.textContent = `✓ 完成 (${evt.steps} 步)` + (evt.note ? ` · ${evt.note}` : "");
        bubble.appendChild(note);
      } else {
        const note = document.createElement("div");
        note.style.color = "var(--muted)";
        note.style.fontSize = "12px";
        note.style.marginTop = "8px";
        note.textContent = `✓ 完成 · ${evt.steps} 步` +
          (evt.stats ? ` · ${evt.stats.chapters}章/${evt.stats.total_chars}字` : "");
        bubble.appendChild(note);
      }
      // 任务完成,活跃 agent 回到 orchestrator(总编)
      updateActiveAgent("orchestrator");
      scrollChat();
      break;
  }
}

function prettyResult(r) {
  try {
    const o = typeof r === "string" ? JSON.parse(r) : r;
    return JSON.stringify(o, null, 2);
  } catch {
    return r;
  }
}

// ---------- 章节抽屉 (可编辑) ----------
let drawerChapterId = null;

async function openChapter(cid) {
  const p = currentProject;
  const ch = p.chapters.find((c) => c.id === cid);
  if (!ch) return;
  drawerChapterId = cid;
  $("#drawer-title").textContent = ch.title;
  let body = `<h3>梗概</h3>${esc(ch.outline || "(无)")}`;
  body += `<h3>正文 (${(ch.content || "").length} 字)</h3>${esc(ch.content || "(尚未撰写)")}`;
  $("#drawer-body").innerHTML = body;
  $("#drawer-edit-area").value = ch.content || "";
  $("#drawer-body").classList.remove("hidden");
  $("#drawer-edit-area").classList.add("hidden");
  $("#drawer-edit").classList.remove("hidden");
  $("#drawer-save").classList.add("hidden");
  $("#drawer").classList.add("open");
}

$("#drawer-edit").addEventListener("click", () => {
  $("#drawer-body").classList.add("hidden");
  $("#drawer-edit-area").classList.remove("hidden");
  $("#drawer-edit").classList.add("hidden");
  $("#drawer-save").classList.remove("hidden");
});
$("#drawer-save").addEventListener("click", async () => {
  const content = $("#drawer-edit-area").value;
  await api(`/api/chapters/${drawerChapterId}`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
  toast("章节已保存", "ok");
  // 刷新
  await selectProject(currentProject.id);
  openChapter(drawerChapterId);
});
$("#drawer-close").addEventListener("click", () => $("#drawer").classList.remove("open"));
$("#view-chapter-btn").addEventListener("click", () => {
  const p = currentProject;
  if (!p || !p.chapters?.length) return toast("暂无章节", "warn");
  openChapter(p.chapters[p.chapters.length - 1].id);
});

// ---------- 新建章节 ----------
$("#new-chapter-btn").addEventListener("click", async () => {
  if (!currentProject) return toast("先选择项目", "warn");
  const title = prompt("章节标题:");
  if (!title) return;
  const idx = (currentProject.chapters || []).length;
  const c = await api(`/api/projects/${currentProject.id}/chapters`, {
    method: "POST",
    body: JSON.stringify({ title, idx, outline: "", content: "" }),
  });
  await selectProject(currentProject.id);
  if (c.id) openChapter(c.id);
  toast("章节已创建", "ok");
});

// ---------- 上传 (toast) ----------
$("#upload-btn").addEventListener("click", () => $("#upload-input").click());
$("#upload-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file || !currentProject) return;
  const fd = new FormData();
  fd.append("file", file);
  toast(`正在导入 ${file.name}…`, "ok", 1500);
  const res = await fetch(`/api/projects/${currentProject.id}/upload`, {
    method: "POST",
    body: fd,
  });
  const data = await res.json();
  if (data.error) {
    toast(data.error, "err", 5000);
  } else {
    toast(`已导入 ${data.source}: ${data.chunks} 块 / ${data.chars} 字`, "ok", 4000);
  }
  e.target.value = "";
});

// ---------- 导出 ----------
const exportBtn = $("#export-btn");
exportBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  if (!currentProject) return toast("先选择项目", "warn");
  exportBtn.parentElement.classList.toggle("open");
});
document.addEventListener("click", () => {
  exportBtn.parentElement.classList.remove("open");
});
$("#export-menu").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-fmt]");
  if (!btn) return;
  exportBtn.parentElement.classList.remove("open");
  const fmt = btn.dataset.fmt;
  const pid = currentProject.id;
  const url = `/api/projects/${pid}/export?fmt=${fmt}`;
  if (fmt === "html") {
    window.open(url, "_blank");
  } else {
    const a = document.createElement("a");
    a.href = url;
    a.download = "";
    document.body.appendChild(a);
    a.click();
    a.remove();
    toast(`已导出 ${fmt.toUpperCase()}`, "ok");
  }
});

// ---------- 新建项目 ----------

$("#proj-cancel").addEventListener("click", () => $("#proj-modal").classList.remove("show"));
$("#proj-ok").addEventListener("click", async () => {
  const body = {
    name: $("#p-name").value.trim(),
    genre: $("#p-genre").value.trim(),
    style: $("#p-style").value.trim(),
    premise: $("#p-premise").value.trim(),
  };
  if (!body.name) return toast("请填名称", "warn");
  const p = await api("/api/projects", { method: "POST", body: JSON.stringify(body) });
  $("#proj-modal").classList.remove("show");
  ["p-name", "p-genre", "p-style", "p-premise"].forEach((i) => ($("#" + i).value = ""));
  await loadProjects();
  await selectProject(p.id);
  closeSidebar();
  toast("项目已创建", "ok");
});

// ---------- 添加设定 ----------
$("#add-element-btn").addEventListener("click", () => {
  if (!currentProject) return toast("先选择项目", "warn");
  $("#elem-modal").classList.add("show");
});
$("#elem-cancel").addEventListener("click", () => $("#elem-modal").classList.remove("show"));
$("#elem-ok").addEventListener("click", async () => {
  const body = {
    kind: $("#e-kind").value,
    name: $("#e-name").value.trim(),
    detail: $("#e-detail").value.trim(),
  };
  if (!body.name) return toast("请填名称", "warn");
  await api(`/api/projects/${currentProject.id}/elements`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  $("#elem-modal").classList.remove("show");
  $("#e-name").value = "";
  $("#e-detail").value = "";
  await selectProject(currentProject.id);
  toast("设定已添加", "ok");
});

// ---------- 清空对话 ----------
$("#clear-chat-btn").addEventListener("click", async () => {
  if (!currentProject || !confirm("清空当前项目对话历史?")) return;
  await api(`/api/projects/${currentProject.id}/messages`, { method: "DELETE" });
  showEmpty();
  toast("已清空对话", "ok");
});

// ---------- 响应式侧栏 ----------
function openSidebar() {
  $("#sidebar").classList.add("open");
  $("#scrim").classList.add("show");
}
function closeSidebar() {
  $("#sidebar").classList.remove("open");
  $("#scrim").classList.remove("show");
}
$("#menu-btn").addEventListener("click", openSidebar);
$("#sidebar-close").addEventListener("click", closeSidebar);
$("#scrim").addEventListener("click", closeSidebar);

// ---------- composer ----------
$("#send-btn").addEventListener("click", () => send());
$("#input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send();
  }
});
function autoGrow() {
  const t = $("#input");
  t.style.height = "auto";
  t.style.height = Math.min(t.scrollHeight, 140) + "px";
}
$("#input").addEventListener("input", autoGrow);
// 斜杠命令:输入 / 触发 popup
$("#input").addEventListener("input", (e) => {
  const v = e.target.value;
  if (v.startsWith("/") && !v.includes("\n")) renderSlashPopup(v);
  else { $("#slash-popup").classList.add("hidden"); slashOpen = false; }
});
$("#input").addEventListener("keydown", (e) => {
  if (slashOpen && (e.key === "Enter" || e.key === "Tab")) {
    const sel = $("#slash-popup .slash-item.sel") || $("#slash-popup .slash-item");
    if (sel) { e.preventDefault(); sel.click(); return; }
  }
  if (slashOpen && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
    e.preventDefault();
    const items = [...$$("#slash-popup .slash-item")];
    if (!items.length) return;
    let cur = items.findIndex((x) => x.classList.contains("sel"));
    cur = e.key === "ArrowDown" ? (cur + 1) % items.length : (cur - 1 + items.length) % items.length;
    items.forEach((x) => x.classList.remove("sel"));
    items[cur].classList.add("sel");
  }
});

// 导出辅助(给命令面板用)
async function doExport(fmt) {
  if (!currentProject) return toast("先选择项目", "warn");
  window.location.href = `/api/projects/${currentProject.id}/export?fmt=${fmt}`;
}

document.addEventListener("click", (e) => {
  if (e.target.classList.contains("sugg")) send(e.target.dataset.prompt || e.target.textContent);
});

// init
loadConfig();
loadProjects();
loadAgents();

// ---------- 多 agent 选择器 ----------
function agentBadgesHtml(a) {
  const parts = [];
  if (a.is_entry) parts.push(`<span class="abadge entry">入口</span>`);
  if (a.phase) parts.push(`<span class="abadge phase">阶段 ${esc(a.phase)}</span>`);
  if (a.sandbox === "read-only") {
    parts.push(`<span class="abadge ro" title="只读沙盒,不可写入">🔒 只读</span>`);
  } else if (a.sandbox === "read-write") {
    parts.push(`<span class="abadge rw" title="可读可写">✏️ 可写</span>`);
  }
  if (a.model_tier) {
    const tier = a.model_tier === "high" ? "强" : a.model_tier === "mid" ? "中" : "轻";
    parts.push(`<span class="abadge tier tier-${a.model_tier}" title="模型层级">${tier}</span>`);
  }
  return parts.join("");
}

async function loadAgents() {
  try {
    const data = await api("/api/agents");
    agentsList = data.agents || [];
    currentAgent = data.default || "orchestrator";
    activeAgent = currentAgent;
    workflowPhases = data.workflow_phases || [];
    readonlyAgents = data.readonly_agents || [];
    updateActiveAgent(currentAgent);   // 初始化芯片
    renderWorkflowPhases();
  } catch (e) {
    console.warn("load agents failed", e);
  }
}

// OpenClaw 模式:更新活跃 agent 芯片(自动跟踪 delegate,用户不手选)
function updateActiveAgent(name) {
  activeAgent = name;
  const a = agentsList.find((x) => x.name === name) || { icon: "🎯", label: name, name };
  const chipIcon = $("#agent-chip-icon");
  const chipLabel = $("#agent-chip-label");
  if (chipIcon) chipIcon.textContent = a.icon || "🎯";
  if (chipLabel) chipLabel.textContent = a.label || name;
  const chip = $("#agent-chip");
  if (chip) chip.dataset.agent = name;
}

// 打开 Agent Panel(展示当前活跃 agent 的 memory/tools/指令栈,只读)
function openAgentPanel() {
  const a = agentsList.find((x) => x.name === activeAgent);
  const body = $("#ap-body");
  const title = $("#ap-title");
  if (!a) {
    title.textContent = "Agent";
    body.innerHTML = `<p class="muted">暂无活跃 agent 信息</p>`;
  } else {
    title.innerHTML = `<span style="font-size:18px">${a.icon}</span> ${esc(a.label)}`;
    const toolsList = (a.tools || []).map((t) => `<span class="ap-tool">${esc(t)}</span>`).join("");
    body.innerHTML = `
      <div class="ap-sec">
        <div class="ap-sec-title">角色</div>
        <div class="ap-role">${esc(a.role || "(无描述)")}</div>
      </div>
      <div class="ap-sec">
        <div class="ap-sec-title">阶段</div>
        <div class="ap-meta">${esc(a.phase || "全局")}</div>
      </div>
      <div class="ap-sec">
        <div class="ap-sec-title">沙盒</div>
        <div class="ap-meta">
          <span class="abadge ${a.sandbox === "read-only" ? "ro" : "rw"}">
            ${a.sandbox === "read-only" ? "🔒 只读" : "✏️ 可写"}
          </span>
          <span class="abadge tier tier-${a.model_tier || "mid"}">
            ${a.model_tier === "high" ? "强" : a.model_tier === "mid" ? "中" : "轻"}模型
          </span>
        </div>
      </div>
      <div class="ap-sec">
        <div class="ap-sec-title">可用工具 (${(a.tools || []).length})</div>
        <div class="ap-tools">${toolsList || "<span class='muted'>(无)</span>"}</div>
      </div>
      <div class="ap-sec">
        <div class="ap-sec-title">说明</div>
        <div class="ap-note">入口固定为「总编 orchestrator」,它会根据任务自动委派给对应专家 agent。这里显示的是当前活跃 agent 的实时状态。</div>
      </div>
    `;
  }
  $("#agent-panel").classList.add("open");
}

function renderWorkflowPhases() {
  const el = $("#workflow-phases");
  if (!el) return;
  if (!workflowPhases.length) { el.innerHTML = ""; return; }
  el.innerHTML = workflowPhases.map((p, i) => {
    const agents = p.agents || (p.agent ? [p.agent] : []);
    const icons = agents.map((n) => {
      const a = agentsList.find((x) => x.name === n);
      return a ? `<span class="wf-agent" title="${esc(a.label)}">${a.icon}</span>` : "";
    }).join("");
    // 循环标识:打回重写 / 下一章循环
    const loopBadge = p.loop === "reject"
      ? `<span class="wf-loop reject" title="不通过则打回重写">↺ 打回</span>`
      : p.loop === "next-chapter"
      ? `<span class="wf-loop next" title="通过则推进下一章">↻ 循环</span>`
      : "";
    // 阶段间箭头
    const arrow = i < workflowPhases.length - 1 ? `<div class="wf-arrow">↓</div>` : "";
    return `<div class="wf-item">
      <span class="wf-no">${p.phase}</span>
      <span class="wf-body">
        <span class="wf-name">${esc(p.name)} ${loopBadge}</span>
        <span class="wf-desc">${esc(p.description || "")}</span>
        <span class="wf-agents">${icons}</span>
      </span>
    </div>${arrow}`;
  }).join("");
}

// Agent 芯片点击 → 打开 Agent Panel (OpenClaw 模式,只读详情)
$("#agent-chip").addEventListener("click", (e) => {
  e.stopPropagation();
  openAgentPanel();
});
$("#ap-close").addEventListener("click", () => $("#agent-panel").classList.remove("open"));

// ==================== 命令面板 (⌘K / Ctrl+K) ====================
const CMDK_ITEMS = [
  { id: "new-project", icon: "📁", label: "新建项目", action: () => $("#proj-modal").classList.add("show") },
  { id: "switch-project", icon: "📂", label: "切换项目", action: () => $("#proj-select-btn").click() },
  { id: "upload", icon: "📤", label: "上传素材", action: () => $("#upload-input").click() },
  { id: "export-txt", icon: "📄", label: "导出 TXT", action: () => doExport("txt") },
  { id: "export-docx", icon: "📘", label: "导出 Word", action: () => doExport("docx") },
  { id: "view-chapters", icon: "📑", label: "查看章节列表", action: () => $("#view-chapter-btn").click() },
  { id: "settings", icon: "⚙️", label: "打开设置", action: () => $("#settings-btn").click() },
  { id: "agent-panel", icon: "🎯", label: "查看活跃 Agent", action: () => openAgentPanel() },
  { id: "clear-chat", icon: "🗑", label: "清空对话", action: () => $("#clear-chat-btn").click() },
  { id: "cmd-continue", icon: "✍️", label: "续写最近一章", action: () => send("继续续写最近一章,2000字") },
  { id: "cmd-status", icon: "📊", label: "查看项目状态", action: () => send("查看当前项目状态与进度") },
  { id: "cmd-check", icon: "🔍", label: "质量检查", action: () => send("对最近一章做质量检查") },
];

function openCmdk() {
  $("#cmdk-overlay").classList.remove("hidden");
  $("#cmdk-input").value = "";
  renderCmdk("");
  setTimeout(() => $("#cmdk-input").focus(), 50);
}
function closeCmdk() {
  $("#cmdk-overlay").classList.add("hidden");
}
function renderCmdk(q) {
  const ql = q.toLowerCase().trim();
  const items = !ql ? CMDK_ITEMS : CMDK_ITEMS.filter((it) =>
    it.label.toLowerCase().includes(ql) || it.id.includes(ql));
  $("#cmdk-list").innerHTML = items.map((it, i) =>
    `<button class="cmdk-item${i === 0 ? " sel" : ""}" data-id="${it.id}">
      <span class="cmdk-icon">${it.icon}</span><span class="cmdk-text">${esc(it.label)}</span>
    </button>`).join("") || `<div class="cmdk-empty">无匹配</div>`;
  $("#cmdk-list").querySelectorAll(".cmdk-item").forEach((el) => {
    el.onclick = () => {
      const it = CMDK_ITEMS.find((x) => x.id === el.dataset.id);
      if (it) { closeCmdk(); it.action(); }
    };
  });
}
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    $("#cmdk-overlay").classList.contains("hidden") ? openCmdk() : closeCmdk();
  }
  if (e.key === "Escape") closeCmdk();
});
$("#cmdk-input").addEventListener("input", (e) => renderCmdk(e.target.value));
$("#cmdk-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const sel = $("#cmdk-list .cmdk-item.sel") || $("#cmdk-list .cmdk-item");
    if (sel) sel.click();
  } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    const items = [...$$("#cmdk-list .cmdk-item")];
    if (!items.length) return;
    let cur = items.findIndex((x) => x.classList.contains("sel"));
    cur = e.key === "ArrowDown" ? (cur + 1) % items.length : (cur - 1 + items.length) % items.length;
    items.forEach((x) => x.classList.remove("sel"));
    items[cur].classList.add("sel");
    items[cur].scrollIntoView({ block: "nearest" });
  }
});
$("#cmdk-overlay").addEventListener("click", (e) => {
  if (e.target.id === "cmdk-overlay") closeCmdk();
});

// ==================== 斜杠命令 (在输入框输入 / 触发) ====================
const SLASH_COMMANDS = [
  { cmd: "/续写", desc: "续写最近一章", fill: "继续续写最近一章,2000字" },
  { cmd: "/状态", desc: "查看项目状态", fill: "查看当前项目状态与进度" },
  { cmd: "/质检", desc: "质量检查", fill: "对最近一章做质量检查" },
  { cmd: "/大纲", desc: "生成大纲", fill: "帮我构思一个大纲,12章" },
  { cmd: "/设定", desc: "添加设定", fill: "帮我添加一个角色设定" },
  { cmd: "/润色", desc: "润色最近一章", fill: "润色最近一章,增强感染力" },
  { cmd: "/清空", desc: "清空对话", fill: null, action: () => $("#clear-chat-btn").click() },
  { cmd: "/设置", desc: "打开设置", fill: null, action: () => $("#settings-btn").click() },
  { cmd: "/导出", desc: "导出", fill: null, action: () => $("#export-btn").click() },
];
let slashOpen = false;
function renderSlashPopup(q) {
  const items = SLASH_COMMANDS.filter((s) => !q || s.cmd.includes(q.slice(1)) || s.desc.includes(q));
  const pop = $("#slash-popup");
  if (!items.length) { pop.classList.add("hidden"); slashOpen = false; return; }
  pop.classList.remove("hidden");
  slashOpen = true;
  pop.innerHTML = items.map((s, i) =>
    `<button class="slash-item${i === 0 ? " sel" : ""}" data-fill="${esc(s.fill || "")}" data-cmd="${esc(s.cmd)}">
      <span class="slash-cmd">${esc(s.cmd)}</span><span class="slash-desc">${esc(s.desc)}</span>
    </button>`).join("");
  pop.querySelectorAll(".slash-item").forEach((el) => {
    el.onclick = () => {
      const cmd = SLASH_COMMANDS.find((s) => s.cmd === el.dataset.cmd);
      if (cmd) {
        if (cmd.action) { cmd.action(); $("#input").value = ""; }
        else if (cmd.fill) { $("#input").value = cmd.fill; }
        pop.classList.add("hidden"); slashOpen = false;
        $("#input").focus(); autoGrow();
      }
    };
  });
}

// ==================== 设置面板 ====================
let spData = null; // 当前设置数据
let spSelectedProvider = null; // 添加模型时选中的厂商
let spBaseMap = {}; // 模型 -> 厂商默认 base

$("#settings-btn").addEventListener("click", async () => {
  $("#settings-panel").classList.add("open");
  await loadSettings();
});
$("#sp-close").addEventListener("click", () => $("#settings-panel").classList.remove("open"));

async function loadSettings() {
  spData = await api("/api/settings");
  spSelectedProvider = null;
  // 构建模型 -> 厂商预设 base 的反查表
  spBaseMap = {};
  for (const p of (spData.providers || [])) {
    if (!p.api_base) continue;
    for (const m of p.models) spBaseMap[m] = p.api_base;
  }
  renderSettings();
}

// 根据模型名找厂商默认 base
function defaultBaseFor(model) {
  if (!spBaseMap) return "";
  if (spBaseMap[model]) return spBaseMap[model];
  // 按 provider 前缀匹配
  const prov = model.split("/", 1)[0];
  const p = (spData?.providers || []).find((x) => x.provider === prov);
  return p?.api_base || "";
}

function renderSettings() {
  const d = spData;
  const parts = [];

  // ---- 当前模型 ----
  parts.push(`<div class="sp-sec"><div class="sp-sec-title">当前模型</div>`);
  parts.push(`<div class="sp-row"><label>${esc(d.default)}</label>
    <span class="mc-badge ${d.ready ? "ok" : "warn"}">${d.ready ? "就绪" : "缺 Key"}</span></div>`);
  parts.push(`</div>`);

  // ---- 已配置模型列表 ----
  parts.push(`<div class="sp-sec"><div class="sp-sec-title">已配置模型 (${d.models.length})</div>`);
  for (const m of d.models) {
    const badges = [];
    if (m.is_default) badges.push(`<span class="mc-badge def">默认</span>`);
    badges.push(`<span class="mc-badge ${m.ready ? "ok" : "warn"}">${m.ready ? "就绪" : "缺Key"}</span>`);
    const defBase = defaultBaseFor(m.model);
    const curBase = m.api_base || "";
    const isOfficial = !curBase || (defBase && curBase === defBase);
    // 官方默认地址不显示输入框,只展示只读徽章;自定义时才显示可编辑输入框
    const baseField = isOfficial
      ? `<div class="sp-field"><span class="lbl" style="color:var(--green)">API Base · 官方默认 ✓</span>
          <div class="sp-readonly">${esc(defBase || "—")}</div></div>`
      : `<div class="sp-field"><span class="lbl">API Base · 自定义</span>
          <input class="sp-input" data-base="${esc(m.model)}" placeholder="${esc(defBase || "")}" value="${esc(curBase)}" /></div>`;
    parts.push(`<div class="model-card ${m.is_default ? "default" : ""}">
      <div class="mc-head">
        <span class="mc-name">${esc(m.model)}</span>
        ${badges.join("")}
        <button class="mc-setdef" data-model="${esc(m.model)}" title="设为默认">★</button>
        <button class="mc-del" data-model="${esc(m.model)}" title="删除">✕</button>
      </div>
      <div class="mc-fields">
        <div class="sp-field">
          <span class="lbl">API Key ${m.api_key_set ? "(已设置)" : ""}</span>
          <input class="sp-input" type="password" data-key="${esc(m.model)}" placeholder="${m.api_key_set ? "•••••• (留空保留)" : "粘贴 API Key"}" value="" />
        </div>
        ${baseField}
        <div class="sp-row">
          <div class="sp-field" style="flex:1"><span class="lbl">Temperature</span>
            <input class="sp-input small" type="number" step="0.1" min="0" max="2" data-temp="${esc(m.model)}" value="${m.temperature}" /></div>
          <div class="sp-field" style="flex:1"><span class="lbl">Max Tokens</span>
            <input class="sp-input small" type="number" step="256" data-tok="${esc(m.model)}" value="${m.max_tokens}" /></div>
        </div>
        <button class="btn primary sm mc-save" data-model="${esc(m.model)}">保存此模型配置</button>
      </div>
    </div>`);
  }
  parts.push(`</div>`);

  // ---- 添加自定义模型 ----
  parts.push(`<div class="sp-sec"><div class="sp-sec-title">+ 添加模型</div>`);
  parts.push(`<div class="add-model">`);
  // 厂商快捷
  parts.push(`<div class="provider-pick">`);
  for (const p of d.providers) {
    parts.push(`<button class="pp-btn" data-provider="${p.provider}">${p.label}</button>`);
  }
  parts.push(`</div>`);
  // 选中厂商后显示预设模型
  if (spSelectedProvider) {
    const p = d.providers.find((x) => x.provider === spSelectedProvider);
    if (p) {
      if (p.api_base) parts.push(`<p class="hint" style="margin-bottom:6px">端点(已自动填入,无需修改):<code>${esc(p.api_base)}</code></p>`);
      parts.push(`<div class="pp-models">`);
      for (const m of p.models) {
        parts.push(`<button class="pm-btn" data-addmodel="${esc(m)}" data-base="${esc(p.api_base || "")}">+ ${esc(m)}</button>`);
      }
      parts.push(`</div>`);
      if (p.env) parts.push(`<p class="hint">环境变量 ${p.env} 也可配置 Key</p>`);
    }
  }
  // 自定义模型入口:可填模型名 + 自定义地址 + 密钥
  parts.push(`<div class="sp-field custom-model-box" style="margin-top:12px">
    <span class="lbl">+ 自定义模型 (填模型名/地址/密钥)</span>
    <div class="sp-row">
      <input class="sp-input" id="sp-custom-model" placeholder="模型名 (如 openai/my-model 或 ollama/llama3)" />
    </div>
    <div class="sp-row">
      <input class="sp-input" id="sp-custom-base" placeholder="API Base 自定义端点 (可留空走厂商默认)" />
    </div>
    <div class="sp-row">
      <input class="sp-input" id="sp-custom-key" type="password" placeholder="API Key 密钥 (可留空走环境变量)" />
      <button class="btn primary sm" id="sp-add-custom">添加自定义</button>
    </div>
    <p class="hint">格式: provider/model。密钥留空时后端会读对应环境变量;地址留空时用厂商默认。</p>
  </div>`);
  parts.push(`</div></div>`);

  // ---- Agent 参数 ----
  parts.push(`<div class="sp-sec"><div class="sp-sec-title">Agent 参数</div>`);
  parts.push(`<div class="sp-row"><label>最大步数 (工具调用轮次)</label>
    <input class="sp-input small" type="number" id="sp-maxsteps" value="${d.max_steps}" min="1" max="30" /></div>`);
  parts.push(`<div class="sp-row"><label>素材分块大小 (字符)</label>
    <input class="sp-input small" type="number" id="sp-chunksize" value="${d.chunk_size}" min="200" step="200" /></div>`);
  parts.push(`<div class="sp-row"><label>续写检索块数</label>
    <input class="sp-input small" type="number" id="sp-retrievek" value="${d.retrieve_k}" min="1" max="20" /></div>`);
  parts.push(`<button class="btn primary" id="sp-save-agent" style="margin-top:8px">保存 Agent 参数</button>`);
  parts.push(`</div>`);

  $("#sp-body").innerHTML = parts.join("");
  bindSettings();
}

function bindSettings() {
  // 选中厂商
  $$("#sp-body .pp-btn").forEach((b) => {
    b.onclick = () => {
      spSelectedProvider = b.dataset.provider;
      renderSettings();
    };
  });
  // 添加预设模型
  $$("#sp-body .pm-btn").forEach((b) => {
    b.onclick = async () => {
      const model = b.dataset.addmodel;
      const defBase = b.dataset.base || "";
      await api("/api/settings/model", {
        method: "PUT",
        body: JSON.stringify({ model, api_key: "", api_base: defBase, temperature: 0.8, max_tokens: 4096 }),
      });
      toast(`已添加 ${model}`, "ok");
      await loadSettings();
    };
  });
  // 添加自定义模型 (模型名 + 自定义地址 + 密钥)
  const addBtn = $("#sp-add-custom");
  if (addBtn) {
    addBtn.onclick = async () => {
      const modelEl = $("#sp-custom-model");
      const baseEl = $("#sp-custom-base");
      const keyEl = $("#sp-custom-key");
      const model = modelEl ? modelEl.value.trim() : "";
      if (!model) return toast("请填写模型名", "warn");
      if (!model.includes("/")) return toast("格式: provider/model", "warn");
      const customBase = baseEl ? baseEl.value.trim() : "";
      const customKey = keyEl ? keyEl.value.trim() : "";
      // 用户填了自定义 base 就用,否则用厂商默认
      const defBase = defaultBaseFor(model);
      const api_base = customBase || defBase || "";
      await api("/api/settings/model", {
        method: "PUT",
        body: JSON.stringify({
          model,
          api_key: customKey,
          api_base,
          temperature: 0.8,
          max_tokens: 4096,
        }),
      });
      toast(`已添加自定义模型 ${model}`, "ok");
      // 清空输入
      if (modelEl) modelEl.value = "";
      if (baseEl) baseEl.value = "";
      if (keyEl) keyEl.value = "";
      await loadSettings();
    };
  }
  // 保存单个模型配置
  $$("#sp-body .mc-save").forEach((b) => {
    b.onclick = async () => {
      const m = b.dataset.model;
      const keyEl = $(`#sp-body [data-key="${CSS.escape(m)}"]`);
      const baseEl = $(`#sp-body [data-base="${CSS.escape(m)}"]`);
      const tempEl = $(`#sp-body [data-temp="${CSS.escape(m)}"]`);
      const tokEl = $(`#sp-body [data-tok="${CSS.escape(m)}"]`);
      // 留空或等于厂商默认时,统一存空串(由后端兜底填默认)
      let baseVal = baseEl ? baseEl.value.trim() : "";
      const def = defaultBaseFor(m);
      if (!baseVal || (def && baseVal === def)) baseVal = "";
      const body = {
        model: m,
        api_key: keyEl ? keyEl.value : null,
        api_base: baseVal,
        temperature: tempEl ? parseFloat(tempEl.value) : null,
        max_tokens: tokEl ? parseInt(tokEl.value) : null,
      };
      await api("/api/settings/model", { method: "PUT", body: JSON.stringify(body) });
      toast(`${m} 配置已保存`, "ok");
      await loadSettings();
      await loadConfig();
    };
  });
  // 设为默认
  $$("#sp-body .mc-setdef").forEach((b) => {
    b.onclick = async () => {
      await api("/api/config/model", { method: "PUT", body: JSON.stringify({ model: b.dataset.model }) });
      toast(`已设为默认: ${b.dataset.model}`, "ok");
      await loadSettings();
      await loadConfig();
    };
  });
  // 删除模型
  $$("#sp-body .mc-del").forEach((b) => {
    b.onclick = async () => {
      if (!confirm(`删除模型 ${b.dataset.model}?`)) return;
      await api("/api/settings/model", { method: "DELETE", body: JSON.stringify({ model: b.dataset.model }) });
      toast("已删除", "ok");
      await loadSettings();
      await loadConfig();
    };
  });
  // 保存 Agent 参数
  const saveAgent = $("#sp-save-agent");
  if (saveAgent) {
    saveAgent.onclick = async () => {
      await api("/api/settings/agent", {
        method: "PUT",
        body: JSON.stringify({
          max_steps: parseInt($("#sp-maxsteps").value),
          chunk_size: parseInt($("#sp-chunksize").value),
          retrieve_k: parseInt($("#sp-retrievek").value),
        }),
      });
      toast("Agent 参数已保存", "ok");
    };
  }
}
