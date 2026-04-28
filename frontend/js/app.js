const apiBase = "";
const HISTORY_VISIBLE_LIMIT = 5;

const MODE_LABELS = {
  extractive: "本地检索模式",
  gpt: "GPT增强",
  deepseek: "DeepSeek增强",
  qwen: "Qwen增强",
  ollama: "Ollama本地增强",
  extractive_fallback: "回退到本地检索模式",
  empty_index: "知识库未就绪",
  no_context: "未命中制度依据",
};

const GENERATION_LABELS = {
  llm: "大模型生成",
  extractive: "检索摘要",
  fallback: "失败回退",
};

const RETRIEVAL_LABELS = {
  vector: "向量检索",
  keyword_fallback: "关键词回退",
  no_index: "未建索引",
};

const EMBEDDING_QUALITY_LABELS = {
  real: "真实 Embedding RAG",
  fallback: "fallback 轻量检索",
};

const MODEL_META = {
  gpt: {
    title: "GPT增强",
    defaultBaseUrl: "https://api.openai.com/v1",
    defaultModel: "gpt-4o-mini",
  },
  deepseek: {
    title: "DeepSeek增强",
    defaultBaseUrl: "https://api.deepseek.com/v1",
    defaultModel: "deepseek-chat",
  },
  qwen: {
    title: "Qwen增强",
    defaultBaseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    defaultModel: "qwen-plus",
  },
  ollama: {
    title: "Ollama本地增强",
    defaultBaseUrl: "http://127.0.0.1:11434/v1",
    defaultModel: "qwen2.5:3b",
  },
};

const loginView = document.getElementById("loginView");
const appView = document.getElementById("appView");
const loginForm = document.getElementById("loginForm");
const loginPhone = document.getElementById("loginPhone");
const loginPassword = document.getElementById("loginPassword");
const loginStatus = document.getElementById("loginStatus");

const welcomeText = document.getElementById("welcomeText");
const runtimeModeEl = document.getElementById("runtimeMode");
const kbStatusEl = document.getElementById("kbStatus");
const settingsNav = document.getElementById("settingsNav");
const userBadge = document.getElementById("userBadge");
const qaModeText = document.getElementById("qaModeText");
const qaRetrievalText = document.getElementById("qaRetrievalText");
const qaEmbeddingModelText = document.getElementById("qaEmbeddingModelText");
const qaEmbeddingQualityText = document.getElementById("qaEmbeddingQualityText");
const qaEmbeddingNotice = document.getElementById("qaEmbeddingNotice");

const questionInput = document.getElementById("questionInput");
const askBtn = document.getElementById("askBtn");
const askStatus = document.getElementById("askStatus");
const answerText = document.getElementById("answerText");
const sourcesEl = document.getElementById("sources");

const profilePhone = document.getElementById("profilePhone");
const profileRole = document.getElementById("profileRole");
const profilePhoneInput = document.getElementById("profilePhoneInput");
const profileForm = document.getElementById("profileForm");
const passwordForm = document.getElementById("passwordForm");
const currentPasswordInput = document.getElementById("currentPasswordInput");
const newPasswordInput = document.getElementById("newPasswordInput");
const profileStatus = document.getElementById("profileStatus");
const logoutBtn = document.getElementById("logoutBtn");
const historyList = document.getElementById("historyList");

const settingsForm = document.getElementById("settingsForm");
const temperatureInput = document.getElementById("temperatureInput");
const maxContextSourcesInput = document.getElementById("maxContextSourcesInput");
const maxSnippetCharsInput = document.getElementById("maxSnippetCharsInput");
const maxContextCharsInput = document.getElementById("maxContextCharsInput");
const settingsStatus = document.getElementById("settingsStatus");
const llmBadge = document.getElementById("llmBadge");
const settingsRuntimeText = document.getElementById("settingsRuntimeText");
const settingsModeBanner = document.getElementById("settingsModeBanner");
const settingsTabs = document.querySelectorAll(".settings-tab");
const settingsPanels = document.querySelectorAll(".settings-tab-panel");
const centerTabs = document.querySelectorAll(".center-tab");
const centerPanels = document.querySelectorAll(".center-tab-panel");

const fileCountEl = document.getElementById("fileCount");
const chunkCountEl = document.getElementById("chunkCount");
const lastIndexedAtEl = document.getElementById("lastIndexedAt");
const reindexBtn = document.getElementById("reindexBtn");
const reindexResult = document.getElementById("reindexResult");

const createAccountForm = document.getElementById("createAccountForm");
const newAccountPhone = document.getElementById("newAccountPhone");
const newAccountPassword = document.getElementById("newAccountPassword");
const newAccountRole = document.getElementById("newAccountRole");
const resetPasswordForm = document.getElementById("resetPasswordForm");
const resetPhone = document.getElementById("resetPhone");
const resetPassword = document.getElementById("resetPassword");
const adminStatus = document.getElementById("adminStatus");
const accountsList = document.getElementById("accountsList");

const modelFields = {
  gpt: {
    card: document.querySelector('[data-model="gpt"]'),
    enabled: document.getElementById("gptEnabledInput"),
    baseUrl: document.getElementById("gptBaseUrlInput"),
    apiKey: document.getElementById("gptApiKeyInput"),
    model: document.getElementById("gptModelInput"),
  },
  deepseek: {
    card: document.querySelector('[data-model="deepseek"]'),
    enabled: document.getElementById("deepseekEnabledInput"),
    baseUrl: document.getElementById("deepseekBaseUrlInput"),
    apiKey: document.getElementById("deepseekApiKeyInput"),
    model: document.getElementById("deepseekModelInput"),
  },
  qwen: {
    card: document.querySelector('[data-model="qwen"]'),
    enabled: document.getElementById("qwenEnabledInput"),
    baseUrl: document.getElementById("qwenBaseUrlInput"),
    apiKey: document.getElementById("qwenApiKeyInput"),
    model: document.getElementById("qwenModelInput"),
  },
  ollama: {
    card: document.querySelector('[data-model="ollama"]'),
    enabled: document.getElementById("ollamaEnabledInput"),
    baseUrl: document.getElementById("ollamaBaseUrlInput"),
    apiKey: document.getElementById("ollamaApiKeyInput"),
    model: document.getElementById("ollamaModelInput"),
  },
};

const embeddingFields = {
  provider: document.getElementById("embeddingProviderInput"),
  baseUrl: document.getElementById("embeddingBaseUrlInput"),
  apiKey: document.getElementById("embeddingApiKeyInput"),
  model: document.getElementById("embeddingModelInput"),
  enabled: document.getElementById("embeddingEnabledInput"),
};

let currentUser = null;
let currentSettings = null;

function activateSettingsTab(tabName) {
  settingsTabs.forEach((button) => {
    const active = button.dataset.settingsTab === tabName;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  settingsPanels.forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.settingsPanel !== tabName);
  });
}

function activateCenterTab(tabName) {
  centerTabs.forEach((button) => {
    const active = button.dataset.centerTab === tabName;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  centerPanels.forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.centerPanel !== tabName);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatTime(iso) {
  if (!iso) return "暂无";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function setAnswer(text, isEmpty = false) {
  answerText.textContent = text;
  answerText.classList.toggle("empty", isEmpty);
}

function getJsonError(data, fallback) {
  return data && data.error ? data.error : fallback;
}

function getModeLabel(mode) {
  return MODE_LABELS[mode] || "本地检索模式";
}

function getGenerationLabel(type) {
  return GENERATION_LABELS[type] || "检索摘要";
}

function getRetrievalLabel(type) {
  return RETRIEVAL_LABELS[type] || "向量检索";
}

function getEmbeddingQualityLabel(quality) {
  return EMBEDDING_QUALITY_LABELS[quality] || EMBEDDING_QUALITY_LABELS.fallback;
}

function getEmbeddingNoticeText(data = {}) {
  if (data.embedding_quality !== "fallback") return "";
  return "当前为轻量 fallback 检索，效果可能较弱，建议配置真实 Embedding。";
}

function buildAskStatusText(data = {}) {
  const parts = [];
  parts.push(data.mode_label || getModeLabel(data.mode));
  if (data.generation_type) parts.push(`生成方式：${getGenerationLabel(data.generation_type)}`);
  if (data.used_model) parts.push(`模型：${data.used_model}`);
  if (data.retrieval_type) parts.push(`检索：${getRetrievalLabel(data.retrieval_type)}`);
  if (data.embedding_quality) parts.push(`Embedding：${getEmbeddingQualityLabel(data.embedding_quality)}`);
  if (data.embedding_model) parts.push(`向量模型：${data.embedding_model}`);
  if (data.fallback_reason) parts.push(`说明：${data.fallback_reason}`);
  return parts.filter(Boolean).join(" · ");
}

function showLogin() {
  loginView.classList.remove("hidden");
  appView.classList.add("hidden");
}

function showApp(user) {
  currentUser = user;
  loginView.classList.add("hidden");
  appView.classList.remove("hidden");
  settingsNav.classList.toggle("hidden", user.role !== "admin");
  welcomeText.textContent = `当前登录：${user.phone} · ${user.role === "admin" ? "管理员" : "普通用户"}`;
  profilePhone.textContent = user.phone;
  profileRole.textContent = user.role === "admin" ? "管理员" : "普通用户";
  profilePhoneInput.value = user.phone;
  userBadge.textContent = user.role === "admin" ? "管理员会话" : "普通用户会话";
  activateView("qa");
}

function activateView(viewName) {
  document.querySelectorAll(".rail-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewName);
  });
  document.querySelectorAll(".view-panel").forEach((panel) => panel.classList.add("hidden"));
  const target = document.getElementById(`${viewName}View`);
  if (target) target.classList.remove("hidden");
}

function renderSources(sources = []) {
  sourcesEl.innerHTML = "";
  if (!sources.length) {
    sourcesEl.innerHTML = '<p class="muted">暂无引用来源</p>';
    return;
  }

  sources.forEach((item, index) => {
    const titlePath = Array.isArray(item.title_path) ? item.title_path.filter(Boolean).join(" > ") : "";
    const node = document.createElement("div");
    node.className = "source-item";
    node.innerHTML = `
      <div class="source-meta">
        <span class="source-file">[${index + 1}] ${escapeHtml(item.file || "未知文档")}</span>
        <span class="source-score">相关度 ${escapeHtml(String(item.score ?? "-"))}</span>
      </div>
      <div class="source-tags">
        <span class="source-tag">${escapeHtml(getRetrievalLabel(item.retrieval_type))}</span>
        ${titlePath ? `<span class="source-path">${escapeHtml(titlePath)}</span>` : ""}
      </div>
      <div class="snippet">${escapeHtml(item.snippet || "")}</div>
    `;
    sourcesEl.appendChild(node);
  });
}

function renderHistory(items = []) {
  historyList.innerHTML = "";
  const visibleItems = items.slice(0, HISTORY_VISIBLE_LIMIT);

  if (!visibleItems.length) {
    historyList.innerHTML = '<p class="muted">暂无历史记录</p>';
    return;
  }

  visibleItems.forEach((item) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "history-item";
    row.innerHTML = `
      <strong>${escapeHtml(item.question || "")}</strong>
      <span>${escapeHtml(item.answer || "")}</span>
      <em>${formatTime(item.created_at)} · ${item.source_count ?? 0} 个来源</em>
    `;
    row.addEventListener("click", () => {
      questionInput.value = item.question || "";
      activateView("qa");
      questionInput.focus();
    });
    historyList.appendChild(row);
  });
}

function renderAccounts(items = []) {
  accountsList.innerHTML = "";
  if (!items.length) {
    accountsList.innerHTML = '<p class="muted">暂无账号数据</p>';
    return;
  }

  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "account-item";
    row.innerHTML = `
      <strong>${escapeHtml(item.phone || "")}</strong>
      <span>${item.role === "admin" ? "管理员" : "普通用户"}</span>
      <em>创建于 ${formatTime(item.created_at)}</em>
    `;
    accountsList.appendChild(row);
  });
}

function updateRuntimeMode(mode = "extractive") {
  const label = getModeLabel(mode);
  const enhanced = !["extractive", "empty_index", "no_context"].includes(mode);
  runtimeModeEl.textContent = label;
  qaModeText.textContent = label;
  settingsRuntimeText.textContent = label;
  settingsModeBanner.textContent = label;
  llmBadge.textContent = enhanced ? "已启用" : "本地检索";
  llmBadge.classList.toggle("muted-badge", !enhanced);
}

function updateEmbeddingStatus(data = {}) {
  const quality = data.embedding_quality || "fallback";
  const model = data.embedding_model || "text-embedding-v4";
  qaRetrievalText.textContent = getEmbeddingQualityLabel(quality);
  qaEmbeddingModelText.textContent = model;
  qaEmbeddingQualityText.textContent = quality;

  const notice = getEmbeddingNoticeText(data);
  qaEmbeddingNotice.textContent = notice;
  qaEmbeddingNotice.classList.toggle("hidden", !notice);
}

function updateModelCardStates() {
  Object.values(modelFields).forEach((fields) => {
    fields.card.classList.toggle("active", fields.enabled.checked);
  });
}

function normalizeSettingsShape(settings = {}) {
  const normalized = {
    models: {},
    embedding: {
      provider: settings.embedding?.provider || "qwen",
      base_url: settings.embedding?.base_url || "https://dashscope.aliyuncs.com/compatible-mode/v1",
      api_key: settings.embedding?.api_key || "",
      model: settings.embedding?.model || "text-embedding-v4",
      enabled: Boolean(settings.embedding?.enabled),
    },
    temperature: settings.temperature ?? 0.2,
    max_context_sources: settings.max_context_sources ?? settings.top_k ?? 3,
    max_snippet_chars: settings.max_snippet_chars ?? 500,
    max_context_chars: settings.max_context_chars ?? 1500,
    active_mode: settings.active_mode || "extractive",
  };

  Object.entries(MODEL_META).forEach(([key, meta]) => {
    const incoming = settings.models?.[key] || {};
    normalized.models[key] = {
      provider_name: incoming.provider_name || key,
      base_url: incoming.base_url || meta.defaultBaseUrl,
      api_key: incoming.api_key || (key === "ollama" ? "ollama" : ""),
      model: incoming.model || meta.defaultModel,
      enabled: Boolean(incoming.enabled),
    };
  });

  return normalized;
}

function applySettings(settings) {
  currentSettings = normalizeSettingsShape(settings);
  Object.entries(modelFields).forEach(([key, fields]) => {
    const config = currentSettings.models[key];
    fields.enabled.checked = Boolean(config.enabled);
    fields.baseUrl.value = config.base_url || "";
    fields.apiKey.value = config.api_key || "";
    fields.model.value = config.model || "";
  });
  embeddingFields.provider.value = currentSettings.embedding.provider || "qwen";
  embeddingFields.baseUrl.value = currentSettings.embedding.base_url || "";
  embeddingFields.apiKey.value = currentSettings.embedding.api_key || "";
  embeddingFields.model.value = currentSettings.embedding.model || "text-embedding-v4";
  embeddingFields.enabled.checked = Boolean(currentSettings.embedding.enabled);
  temperatureInput.value = currentSettings.temperature ?? 0.2;
  maxContextSourcesInput.value = currentSettings.max_context_sources ?? 3;
  maxSnippetCharsInput.value = currentSettings.max_snippet_chars ?? 500;
  maxContextCharsInput.value = currentSettings.max_context_chars ?? 1500;
  updateModelCardStates();
  updateRuntimeMode(currentSettings.active_mode);
}

function getSettingsPayload() {
  const models = {};
  Object.entries(modelFields).forEach(([key, fields]) => {
    models[key] = {
      provider_name: key,
      base_url: fields.baseUrl.value.trim(),
      api_key: fields.apiKey.value.trim(),
      model: fields.model.value.trim(),
      enabled: fields.enabled.checked,
    };
  });

  return {
    models,
    embedding: {
      provider: embeddingFields.provider.value.trim() || "qwen",
      base_url: embeddingFields.baseUrl.value.trim(),
      api_key: embeddingFields.apiKey.value.trim(),
      model: embeddingFields.model.value.trim(),
      enabled: embeddingFields.enabled.checked,
    },
    temperature: Number(temperatureInput.value || 0.2),
    max_context_sources: Number(maxContextSourcesInput.value || 3),
    max_snippet_chars: Number(maxSnippetCharsInput.value || 500),
    max_context_chars: Number(maxContextCharsInput.value || 1500),
  };
}

async function fetchJson(url, options = {}) {
  const response = await fetch(`${apiBase}${url}`, {
    credentials: "same-origin",
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(getJsonError(data, "请求失败"));
  }
  return data;
}

async function refreshSession() {
  const data = await fetchJson("/api/auth/session");
  if (!data.authenticated) {
    currentUser = null;
    showLogin();
    return false;
  }
  showApp(data.user);
  return true;
}

async function loadHistory() {
  const data = await fetchJson("/api/history");
  renderHistory(data.items || []);
}

async function loadAdminData() {
  if (!currentUser || currentUser.role !== "admin") return;

  const [statusData, settingsData, accountsData] = await Promise.all([
    fetchJson("/api/status"),
    fetchJson("/api/settings"),
    fetchJson("/api/admin/accounts"),
  ]);

  fileCountEl.textContent = statusData.file_count ?? 0;
  chunkCountEl.textContent = statusData.chunk_count ?? 0;
  lastIndexedAtEl.textContent = formatTime(statusData.last_indexed_at);
  kbStatusEl.textContent = statusData.is_index_ready ? "知识库已就绪" : "知识库尚未建立索引";
  applySettings(settingsData);
  updateEmbeddingStatus(statusData);
  renderAccounts(accountsData.items || []);
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginStatus.textContent = "正在登录...";
  try {
    const data = await fetchJson("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone: loginPhone.value.trim(),
        password: loginPassword.value,
      }),
    });
    loginPassword.value = "";
    showApp(data.user);
    await loadHistory();
    if (data.user.role === "admin") {
      await loadAdminData();
    } else {
      kbStatusEl.textContent = "管理员可在设置中查看系统状态";
    }
    loginStatus.textContent = "登录成功。";
  } catch (error) {
    loginStatus.textContent = error.message;
  }
});

document.querySelectorAll(".rail-item").forEach((button) => {
  button.addEventListener("click", async () => {
    const target = button.dataset.view;
    if (!target) return;
    activateView(target);
    if (target === "center") await loadHistory();
    if (target === "settings") await loadAdminData();
  });
});

document.querySelectorAll(".quick-btn").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.textContent.trim();
    questionInput.focus();
  });
});

settingsTabs.forEach((button) => {
  button.addEventListener("click", () => {
    activateSettingsTab(button.dataset.settingsTab);
  });
});

centerTabs.forEach((button) => {
  button.addEventListener("click", () => {
    activateCenterTab(button.dataset.centerTab);
  });
});

Object.entries(modelFields).forEach(([key, fields]) => {
  fields.enabled.addEventListener("change", () => {
    if (fields.enabled.checked) {
      Object.entries(modelFields).forEach(([otherKey, otherFields]) => {
        if (otherKey !== key) otherFields.enabled.checked = false;
      });
    }
    updateModelCardStates();
  });
});

askBtn.addEventListener("click", async () => {
  const question = questionInput.value.trim();
  if (!question) {
    askStatus.textContent = "请输入问题后再提问。";
    questionInput.focus();
    return;
  }

  askBtn.disabled = true;
  askStatus.textContent = "正在检索制度依据...";
  setAnswer("正在生成答案...", true);
  renderSources([]);

  try {
    const data = await fetchJson("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    setAnswer(data.answer || "未返回回答", !data.answer);
    renderSources(data.sources || []);
    askStatus.textContent = buildAskStatusText(data);
    updateRuntimeMode(data.mode);
    updateEmbeddingStatus(data);
    await loadHistory();
  } catch (error) {
    askStatus.textContent = error.message;
    setAnswer("请稍后重试。", true);
  } finally {
    askBtn.disabled = false;
  }
});

profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  profileStatus.textContent = "正在更新手机号...";
  try {
    const data = await fetchJson("/api/me/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: profilePhoneInput.value.trim() }),
    });
    showApp(data.user);
    await loadHistory();
    profileStatus.textContent = "手机号已更新。";
  } catch (error) {
    profileStatus.textContent = error.message;
  }
});

passwordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  profileStatus.textContent = "正在更新密码...";
  try {
    await fetchJson("/api/me/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: currentPasswordInput.value,
        new_password: newPasswordInput.value,
      }),
    });
    currentPasswordInput.value = "";
    newPasswordInput.value = "";
    profileStatus.textContent = "密码已更新。";
  } catch (error) {
    profileStatus.textContent = error.message;
  }
});

logoutBtn.addEventListener("click", async () => {
  await fetchJson("/api/auth/logout", { method: "POST" });
  currentUser = null;
  showLogin();
});

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  settingsStatus.textContent = "正在保存模型设置...";
  try {
    const data = await fetchJson("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getSettingsPayload()),
    });
    applySettings(data);
    settingsStatus.textContent = "模型设置已保存，回到问答页即可生效。";
  } catch (error) {
    settingsStatus.textContent = error.message;
  }
});

reindexBtn.addEventListener("click", async () => {
  reindexBtn.disabled = true;
  reindexResult.textContent = "正在重建索引...";
  try {
    const data = await fetchJson("/api/reindex", { method: "POST" });
    fileCountEl.textContent = data.file_count ?? 0;
    chunkCountEl.textContent = data.chunk_count ?? 0;
    lastIndexedAtEl.textContent = formatTime(data.last_indexed_at);
    kbStatusEl.textContent = data.is_index_ready ? "知识库已就绪" : "知识库尚未建立索引";
    updateEmbeddingStatus(data);
    reindexResult.textContent = `索引完成：${data.file_count ?? 0} 个文件，${data.chunk_count ?? 0} 个片段。`;
  } catch (error) {
    reindexResult.textContent = error.message;
  } finally {
    reindexBtn.disabled = false;
  }
});

createAccountForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  adminStatus.textContent = "正在创建账号...";
  try {
    await fetchJson("/api/admin/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone: newAccountPhone.value.trim(),
        password: newAccountPassword.value,
        role: newAccountRole.value,
      }),
    });
    newAccountPhone.value = "";
    newAccountPassword.value = "";
    adminStatus.textContent = "账号创建成功。";
    await loadAdminData();
  } catch (error) {
    adminStatus.textContent = error.message;
  }
});

resetPasswordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  adminStatus.textContent = "正在重置密码...";
  try {
    await fetchJson("/api/admin/accounts/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone: resetPhone.value.trim(),
        new_password: resetPassword.value,
      }),
    });
    resetPhone.value = "";
    resetPassword.value = "";
    adminStatus.textContent = "密码已重置。";
  } catch (error) {
    adminStatus.textContent = error.message;
  }
});

refreshSession()
  .then(async (authenticated) => {
    if (!authenticated) return;
    await loadHistory();
    if (currentUser && currentUser.role === "admin") {
      await loadAdminData();
    } else {
      kbStatusEl.textContent = "管理员可在设置中查看系统状态";
      updateRuntimeMode("extractive");
    }
  })
  .catch(() => {
    showLogin();
  });
