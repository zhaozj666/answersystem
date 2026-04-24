const apiBase = "";

const fileCountEl = document.getElementById("fileCount");
const chunkCountEl = document.getElementById("chunkCount");
const lastIndexedAtEl = document.getElementById("lastIndexedAt");
const kbStatusEl = document.getElementById("kbStatus");

const reindexBtn = document.getElementById("reindexBtn");
const reindexResult = document.getElementById("reindexResult");

const questionInput = document.getElementById("questionInput");
const askBtn = document.getElementById("askBtn");
const askStatus = document.getElementById("askStatus");
const answerText = document.getElementById("answerText");
const sourcesEl = document.getElementById("sources");

function formatTime(iso) {
  if (!iso) return "暂无";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("zh-CN", { hour12: false });
}

function setAnswer(text, isEmpty = false) {
  answerText.textContent = text;
  answerText.classList.toggle("empty", isEmpty);
}

function renderSources(sources = []) {
  sourcesEl.innerHTML = "";

  if (!sources.length) {
    sourcesEl.innerHTML = '<p class="muted">暂无引用来源</p>';
    return;
  }

  sources.forEach((item) => {
    const div = document.createElement("div");
    div.className = "source-item";

    const score = typeof item.score === "number" ? item.score.toFixed(2) : item.score;
    div.innerHTML = `
      <div class="source-meta">
        <span class="source-file">${escapeHtml(item.file || "未知文档")}</span>
        <span class="source-score">匹配度 ${escapeHtml(String(score ?? "-"))}</span>
      </div>
      <div class="snippet">${escapeHtml(item.snippet || "无片段预览")}</div>
    `;
    sourcesEl.appendChild(div);
  });
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadStatus() {
  const res = await fetch(`${apiBase}/api/status`);
  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.error || "状态读取失败");
  }

  fileCountEl.textContent = data.file_count ?? 0;
  chunkCountEl.textContent = data.chunk_count ?? 0;
  lastIndexedAtEl.textContent = formatTime(data.last_indexed_at);
  kbStatusEl.textContent = data.is_index_ready ? "知识库已就绪" : "知识库未建立索引";
}

reindexBtn.addEventListener("click", async () => {
  reindexBtn.disabled = true;
  reindexResult.textContent = "正在重建索引，请稍候...";

  try {
    const res = await fetch(`${apiBase}/api/reindex`, { method: "POST" });
    const data = await res.json();

    if (!res.ok) {
      reindexResult.innerHTML = `<span class="notice">重建失败：${escapeHtml(data.error || "未知错误")}</span>`;
      return;
    }

    const errors = (data.errors || []).length
      ? `；部分文件读取失败：${data.errors.map((e) => `${e.file}: ${e.error}`).join(" | ")}`
      : "";

    reindexResult.textContent = `索引完成：${data.file_count} 个文件，${data.chunk_count} 个片段${errors}`;
    await loadStatus();
  } catch (err) {
    reindexResult.innerHTML = `<span class="notice">重建失败：${escapeHtml(err.message)}</span>`;
  } finally {
    reindexBtn.disabled = false;
  }
});

askBtn.addEventListener("click", async () => {
  const question = questionInput.value.trim();

  if (!question) {
    askStatus.textContent = "请输入问题后再提问。";
    questionInput.focus();
    return;
  }

  askBtn.disabled = true;
  askStatus.textContent = "正在检索制度文档...";
  setAnswer("正在整理命中的制度依据...", true);
  renderSources([]);

  try {
    const res = await fetch(`${apiBase}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();

    if (!res.ok) {
      askStatus.textContent = `提问失败：${data.error || "未知错误"}`;
      setAnswer("请稍后重试，或先检查后端服务是否正常运行。", true);
      return;
    }

    setAnswer(data.answer || "未返回回答", !data.answer);
    renderSources(data.sources || []);
    askStatus.textContent = (data.sources || []).length ? "检索完成" : "未检索到明确依据";
  } catch (err) {
    askStatus.textContent = `提问失败：${err.message}`;
    setAnswer("请确认已通过 http://127.0.0.1:8000 访问页面，并且后端服务正在运行。", true);
  } finally {
    askBtn.disabled = false;
  }
});

document.querySelectorAll(".quick-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    questionInput.value = btn.textContent.trim();
    questionInput.focus();
  });
});

loadStatus().catch((err) => {
  kbStatusEl.textContent = "状态读取失败";
  askStatus.textContent = `状态读取失败：${err.message}`;
});
