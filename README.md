# 内部规章制度智能问答助手

这是一个面向企业内部员工的本地知识库问答系统。系统会读取 `docs/policies/` 中的制度文档（PDF / DOCX / TXT / MD），建立 RAG 索引，并基于检索结果回答问题。

系统现在区分两类模型：

- `Embedding`：把文档和问题转成向量，决定检索是否准确
- `回答模型`：把检索到的制度片段整理成最终回答

二者可以不同。

## 1. 项目结构

```text
answersystem/
├─ backend/
│  ├─ app.py
│  └─ services/
├─ frontend/
│  ├─ index.html
│  ├─ css/style.css
│  └─ js/app.js
├─ docs/
│  └─ policies/
├─ runtime/
└─ tests/
```

## 2. 制度文档放在哪里

请把公司制度文档放到：

```text
docs/policies/
```

支持格式：

- PDF
- DOCX
- TXT
- MD

## 3. 如何安装依赖

确保本机已安装 Python 3.10 及以上版本：

```bat
cd Desktop\answersystem
python -m pip install -r backend/requirements.txt
```

## 4. 如何启动程序

```bat
cd Desktop\answersystem
python backend/app.py
```

启动成功后，在浏览器打开：

```text
http://127.0.0.1:8000
```

不要直接双击 `frontend/index.html`，必须先启动后端，再通过上面的地址访问。

## 5. 默认管理员账号

- 手机号：`15100000000`
- 密码：`123456`

管理员可以进入“系统设置”查看 Embedding 配置、回答模型配置、重建索引和管理账号。

## 6. 如何重建索引

1. 确保文档已经放入 `docs/policies/`
2. 登录管理员账号
3. 进入“系统设置”
4. 点击“重建索引”

页面会显示：

- 文档数
- 片段数
- 最近索引时间
- `embedding_provider`
- `embedding_model`
- `embedding_quality`
- `fallback_reason`

以下情况必须重建索引：

- 文档内容更新
- 更换 Embedding 模型
- 从 fallback embedding 切换为真实 Embedding
- 修改 Embedding 的 `provider / base_url / model`

以下情况通常不需要重建索引：

- 只切换回答模型
- 只调整回答模型温度

## 7. 如何提问

在问答页输入问题，例如：

- 什么是正式员工？
- 试用期是多久？
- 年假规则是什么？
- 迟到早退如何处理？

点击“提问”后，系统会显示：

- 回答内容
- 引用来源
- 当前回答模式
- 检索方式
- `embedding_model`
- `embedding_quality`
- 生成方式
- 使用模型

## 8. 如何配置 Embedding

### Embedding 是做什么的

- Embedding 用于生成文档向量，决定检索准确性
- 回答模型用于生成最终回答
- 二者可以不同
- 推荐中文制度问答使用 `Qwen text-embedding-v4`

### Embedding 设置项

- `provider`：向量模型来源
- `base_url`：Embedding 接口地址
- `api_key`：Embedding 访问密钥
- `model`：Embedding 模型名称
- `enabled`：是否启用真实 Embedding

### 默认推荐配置

```text
provider = qwen
base_url = https://dashscope.aliyuncs.com/compatible-mode/v1
model = text-embedding-v4
enabled = false
api_key = 由用户填写
```

### 推荐的 Qwen Embedding 配置

适合中文制度问答：

```text
provider = qwen
base_url = https://dashscope.aliyuncs.com/compatible-mode/v1
model = text-embedding-v4
enabled = true
api_key = 你的阿里云百炼 API Key
```

### 推荐的 OpenAI Embedding 配置

如果你希望使用 OpenAI 兼容向量模型，可配置：

```text
provider = openai_compatible
base_url = https://api.openai.com/v1
model = text-embedding-3-small
enabled = true
api_key = 你的 OpenAI API Key
```

也可以按需使用：

- `text-embedding-3-small`
- `text-embedding-3-large`

### fallback embedding 是什么

- fallback embedding 只用于本地测试或临时降级
- 它不是高质量 RAG 的正式方案
- 如果页面显示 `fallback 轻量检索`，说明当前检索效果可能较弱

生产环境或效果要求较高的场景，建议必须配置真实 Embedding。

## 9. 如何配置和切换回答模型

系统支持 4 种回答模型配置：

- GPT（云）
- DeepSeek（云）
- Qwen（云）
- Ollama（本地）

### 回答模型用途说明

- 大模型用于把检索到的制度内容总结成更自然的回答
- 不配置回答模型时，系统使用本地检索摘要回答
- Embedding 决定“找得准不准”，回答模型决定“说得自然不自然”
- 切换回答模型不需要重建索引

### 每个回答模型都可以配置

- `base_url`：接口地址
- `api_key`：访问密钥
- `model`：模型名称
- `enabled`：是否启用

### 各回答模型建议

- GPT：回答质量高，需要 OpenAI API Key
- DeepSeek：成本较低，中文与代码能力较好，需要 DeepSeek API Key
- Qwen：适合中文制度问答，需要通义千问 / 阿里云 API Key
- Ollama：本地离线运行，需要本机安装 Ollama

### Ollama 默认聊天配置

- `base_url`: `http://127.0.0.1:11434/v1`
- `api_key`: `ollama`
- `model`: `qwen2.5:3b`
- `enabled`: `false`

## 10. Ollama 低内存本地部署说明

这套默认方案优先考虑“先跑通本地 RAG”，不追求最高效果，也不会默认下载大模型。

### 默认低内存策略

- 本地低内存 Embedding 仅作为兜底方案：
  - `all-minilm`
  - `qwen3-embedding:0.6b`
  - 本地 fallback embedding
- Chat 默认模型：
  - `qwen2.5:3b`
- 不建议默认使用 7B 以上模型

### 如何安装 Ollama

先到 Ollama 官网安装本机版本：

```text
https://ollama.com/download
```

安装完成后，确保 Ollama 服务已启动。

### 推荐下载的轻量模型

```bat
ollama pull all-minilm
ollama pull qwen2.5:3b
```

如果你机器内存更紧张，也可以考虑：

```bat
ollama pull qwen2.5:1.5b
```

### 如何验证 Ollama 是否正常

```bat
curl http://127.0.0.1:11434/api/tags
```

如果能返回模型列表，说明 Ollama 服务可用。

### 低内存电脑推荐配置

- 8GB 内存：
  - 推荐 `all-minilm + qwen2.5:1.5b`
  - 或只使用本地检索
- 16GB 内存：
  - 推荐 `all-minilm / qwen3-embedding:0.6b + qwen2.5:3b`
- 低内存电脑不建议默认使用 7B 以上模型

### 系统的自动回退逻辑

- 如果真实 Embedding 没配置：系统会明确标记为 `fallback 轻量检索`
- 如果真实 Embedding 接口不可用：会回退到本地 fallback embedding，并返回 `fallback_reason`
- 如果没有安装 Ollama：不会崩溃，会回退到本地 fallback embedding 或本地检索摘要
- 如果 Ollama 没启动：不会崩溃，会返回友好提示并回退
- 如果模型没下载：不会崩溃，会返回友好提示并回退

## 11. 可用 API

- `GET /api/health`：健康检查
- `GET /api/status`：查看知识库状态
- `POST /api/reindex`：重建索引
- `GET /api/settings`：读取模型配置
- `POST /api/settings`：保存模型配置
- `POST /api/ask`：提交问题

## 12. 常见问题

### 页面打不开怎么办？

- 确认后端是否已经启动：`python backend/app.py`
- 确认访问地址是否是 `http://127.0.0.1:8000`
- 查看终端是否有报错

### 知识库为空怎么办？

- 检查 `docs/policies/` 是否有文档
- 点击“重建索引”
- 查看返回中的 `errors` 和 `fallback_reason`

### 如何判断当前是不是高质量 RAG？

看两个字段：

- `embedding_quality`
- `retrieval_type`

如果你看到：

- `embedding_quality = real`
- 页面显示 `真实 Embedding RAG`

说明当前索引是基于真实 Embedding 构建的。

如果你看到：

- `embedding_quality = fallback`
- 页面显示 `fallback 轻量检索`

说明当前只是轻量降级方案，不建议当作正式效果验收口径。

### 如何判断是否用了 Ollama embedding？

- 重建索引后看 `/api/reindex` 返回：
  - `embedding_provider = ollama`
  - `embedding_model = all-minilm` 或 `qwen3-embedding:0.6b`
- 如果看到 `embedding_provider = local_hash`，说明已经回退到本地 fallback embedding

### 什么时候一定要重建索引？

以下情况都需要：

- 文档新增、删除、修改
- 更换 Embedding 模型
- 新填写或切换 Embedding 的 `provider / base_url / model`

以下情况通常不需要：

- 只切换回答模型
- 只调整回答模型温度

### 如何判断 Ollama chat 是否生效？

- 提问后看 `/api/ask` 返回：
  - `generation_type = llm`
  - `used_model = qwen2.5:3b` 或你配置的模型名
- 如果看到 `generation_type = fallback`，说明大模型调用失败，已经回退到本地摘要

## 13. 最简使用流程

1. 把制度文档放到 `docs/policies/`
2. 运行 `python backend/app.py`
3. 打开 `http://127.0.0.1:8000`
4. 用管理员账号登录
5. 先按需配置真实 Embedding
6. 执行“重建索引”
7. 再按需配置回答模型
8. 回到问答页开始提问
