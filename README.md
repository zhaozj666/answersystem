# 内部制度知识库问答助手

这是一个本地运行的企业制度问答系统。它会读取本地 `docs/policies/` 目录中的制度文档，完成切分、索引和检索，再结合可选的大模型生成最终回答。

项目当前已经包含：

- 基于 Flask 的后端接口
- 单页前端界面
- 本地账号登录与管理员设置
- 文档切分、索引、检索、问答链路
- 可切换的回答模型配置
- 可单独配置的 Embedding 配置
- 基础测试用例

## 功能概览

- 支持制度文档导入：`PDF`、`DOCX`、`TXT`、`MD`
- 支持管理员登录、普通用户问答、历史记录查看
- 支持重建知识库索引
- 支持切换 `GPT`、`DeepSeek`、`Qwen`、`Ollama`
- 支持单独配置 Embedding，不和回答模型强绑定
- 在未配置真实 Embedding 时，可回退到本地轻量检索

## 项目结构

```text
answersystem/
├─ backend/                  # Flask 后端
│  ├─ app.py
│  └─ services/              # 认证、索引、检索、问答、设置等服务
├─ frontend/                 # 前端页面
│  ├─ index.html
│  ├─ css/style.css
│  └─ js/app.js
├─ docs/                     # 本地文档目录
│  └─ policies/              # 制度文件放这里（已忽略，不上传 GitHub）
├─ runtime/                  # 运行时数据（已忽略）
├─ tests/                    # 测试用例
├─ README.md
└─ requirements.txt
```

## 本地文档约定

制度文件请放到下面这个目录：

```text
docs/policies/
```

支持格式：

- `PDF`
- `DOCX`
- `TXT`
- `MD`

注意：

- `docs/policies/` 中的内容默认不提交到 GitHub
- `.agents/` 下的 skill / policies 等本地辅助文件也不会上传
- 这意味着你可以在本地放真实制度文档，但不会被这次仓库发布带上去

## 运行环境

- Python 3.10 或更高版本
- Windows 本地环境优先
- 如需调用云模型，需要对应厂商的 API Key
- 如需本地大模型，需要本机安装 Ollama

## 安装依赖

如果你使用正式依赖：

```bash
python -m pip install -r backend/requirements.txt
```

仓库根目录也保留了一个极简 `requirements.txt` 说明文件，用于标注当前本地演示版的依赖策略。

## 启动方式

在项目根目录运行：

```bash
python backend/app.py
```

启动后打开：

```text
http://127.0.0.1:8000
```

不要直接双击 `frontend/index.html`，应始终通过 Flask 服务访问。

## 默认管理员账号

- 手机号：`15100000000`
- 密码：`123456`

登录后管理员可以：

- 查看知识库状态
- 重建索引
- 配置回答模型
- 配置 Embedding
- 管理账号

## RAG 与模型说明

系统把“检索”和“回答”拆成两套能力：

- `Embedding`：负责把文档和问题转换成向量，影响“找得准不准”
- `回答模型`：负责根据检索结果生成自然语言答案，影响“说得自然不自然”

二者可以不是同一个提供方。

### 默认回答模型配置

系统内置以下回答模型槽位：

- `gpt`
- `deepseek`
- `qwen`
- `ollama`

默认值位于 `backend/services/settings_service.py`，当前默认模型包括：

- GPT: `gpt-4o-mini`
- DeepSeek: `deepseek-chat`
- Qwen: `qwen-plus`
- Ollama: `qwen2.5:3b`

同一时间只允许启用一个回答模型。

### 默认 Embedding 配置

默认 Embedding 配置为：

```text
provider = qwen
base_url = https://dashscope.aliyuncs.com/compatible-mode/v1
model = text-embedding-v4
enabled = false
```

如果没有启用真实 Embedding，系统会回退到本地轻量检索方案，便于本地演示或低依赖启动。

## 什么时候要重建索引

以下情况建议重建索引：

- 新增、删除、修改了制度文件
- 切换了 Embedding 模型
- 修改了 Embedding 的 `provider / base_url / model`
- 从 fallback 检索切换到真实 Embedding

以下情况通常不需要重建索引：

- 只切换回答模型
- 只调整回答温度、上下文条数等参数

## 常用接口

- `GET /api/health`：健康检查
- `GET /api/auth/session`：当前登录状态
- `POST /api/auth/login`：登录
- `POST /api/auth/logout`：退出登录
- `GET /api/me`：当前用户信息
- `GET /api/history`：问答历史
- `GET /api/status`：知识库状态
- `POST /api/reindex`：重建索引
- `GET /api/settings`：读取模型设置
- `POST /api/settings`：保存模型设置
- `POST /api/ask`：提交问题

## 测试

可在项目根目录运行：

```bash
python -m unittest discover -s tests
```

当前测试覆盖了以下关键点：

- 后端 Python 文件可编译
- 前端 HTML 与 JS 的 DOM 约定一致
- 文档扫描、切分、索引、向量持久化
- 检索回退逻辑
- 问答链路的返回结构

## 发布说明

本次仓库发布默认不会上传以下内容：

- `.agents/`
- `docs/policies/`
- `runtime/`
- 本地索引和运行时文件

如果你要给其他人使用这个项目，只需要让对方在本地自行创建 `docs/policies/`，再放入他们自己的制度文件即可。
