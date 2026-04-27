const apiBase = "";

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
const llmEnabled = document.getElementById("llmEnabled");
const providerSelect = document.getElementById("providerSelect");
const baseUrlInput = document.getElementById("baseUrlInput");
const modelInput = document.getElementById("modelInput");
const apiKeyInput = document.getElementById("apiKeyInput");
const temperatureInput = document.getElementById("temperatureInput");
const topKInput = document.getElementById("topKInput");
const settingsStatus = document.getElementById("settingsStatus");
const llmBadge = document.getElementById("llmBadge");
const settingsRuntimeText = document.getElementById("settingsRuntimeText");

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

let currentUser = null;

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
  updateRuntimeMode();
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
    const node = document.createElement("div");
    node.className = "source-item";
    node.innerHTML = `
      <div class="source-meta">
        <span class="source-file">[${index + 1}] ${escapeHtml(item.file || "未知文档")}</span>
        <span class="source-score">相关度 ${escapeHtml(String(item.score ?? "-"))}</span>
      </div>
      <div class="snippet">${escapeHtml(item.snippet || "")}</div>
    `;
    sourcesEl.appendChild(node);
  });
}

function renderHistory(items = []) {
  historyList.innerHTML = "";
  if (!items.length) {
    historyList.innerHTML = '<p class="muted">暂无历史记录</p>';
    return;
  }

  items.forEach((item) => {
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

function updateRuntimeMode() {
  const enabled = Boolean(llmEnabled.checked);
  runtimeModeEl.textContent = enabled ? "LLM 生成" : "本地检索";
  llmBadge.textContent = enabled ? "开启" : "关闭";
  llmBadge.classList.toggle("muted-badge", !enabled);
  qaModeText.textContent = enabled ? "大模型引用生成" : "本地检索摘要";
  settingsRuntimeText.textContent = enabled ? "大模型生成已开启" : "当前使用本地检索摘要";
}

function applySettings(settings) {
  llmEnabled.checked = Boolean(settings.enabled);
  providerSelect.value = settings.provider || "ollama";
  baseUrlInput.value = settings.base_url || "http://127.0.0.1:11434";
  modelInput.value = settings.model || "qwen2.5:7b";
  apiKeyInput.value = settings.api_key || "";
  temperatureInput.value = settings.temperature ?? 0.2;
  topKInput.value = settings.top_k ?? 5;
  updateRuntimeMode();
}

function getSettingsPayload() {
  return {
    enabled: llmEnabled.checked,
    provider: providerSelect.value,
    base_url: baseUrlInput.value.trim(),
    api_key: apiKeyInput.value.trim(),
    model: modelInput.value.trim(),
    temperature: Number(temperatureInput.value || 0.2),
    top_k: Number(topKInput.value || 5),
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

llmEnabled.addEventListener("change", updateRuntimeMode);

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
    askStatus.textContent = data.mode === "llm" ? "已由大模型生成回答" : "已返回本地检索摘要";
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
    settingsStatus.textContent = "模型设置已保存。";
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
    }
  })
  .catch(() => {
    showLogin();
  });
