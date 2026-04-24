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

async function loadStatus() {
  const res = await fetch(`${apiBase}/api/status`);
  const data = await res.json();
  fileCountEl.textContent = data.file_count ?? 0;
  chunkCountEl.textContent = data.chunk_count ?? 0;
  lastIndexedAtEl.textContent = formatTime(data.last_indexed_at);
  kbStatusEl.textContent = data.is_index_ready ? "已建立索引" : "未建立索引";
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
    div.innerHTML = `
      <div class="file">${item.file}（score: ${item.score}）</div>
      <div class="snippet">${item.snippet}</div>
    `;
    sourcesEl.appendChild(div);
  });
}

reindexBtn.addEventListener("click", async () => {
  reindexBtn.disabled = true;
  reindexResult.textContent = "正在重建索引，请稍候...";
  try {
    const res = await fetch(`${apiBase}/api/reindex`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) {
      reindexResult.textContent = `重建失败：${data.error || "未知错误"}`;
      return;
    }

    const msg = `索引完成：${data.file_count} 个文件，${data.chunk_count} 个片段`;
    const errors = (data.errors || []).length
      ? `；错误：${data.errors.map((e) => `${e.file}: ${e.error}`).join(" | ")}`
      : "";

    reindexResult.textContent = msg + errors;
    await loadStatus();
  } catch (err) {
    reindexResult.textContent = `重建失败：${err.message}`;
  } finally {
    reindexBtn.disabled = false;
  }
});

askBtn.addEventListener("click", async () => {
  const question = questionInput.value.trim();
  if (!question) {
    askStatus.textContent = "请输入问题后再提问。";
    return;
  }

  askBtn.disabled = true;
  askStatus.textContent = "正在检索制度文档……";
  answerText.textContent = "";
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
      return;
    }

    answerText.textContent = data.answer || "未返回回答";
    renderSources(data.sources || []);
    askStatus.textContent = "检索完成";
  } catch (err) {
    askStatus.textContent = `提问失败：${err.message}`;
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
