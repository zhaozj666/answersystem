# 内部规章制度智能问答助手

一个面向**公司全体员工**的中文制度问答系统本地演示版。系统基于固定目录中的 PDF/Word/TXT/MD 文档进行检索，并返回带引用来源的答案。

## 1. 本地演示（当前阶段）

### 1.1 环境要求
- Python 3.10+

### 1.2 安装依赖
```bash
pip install -r requirements.txt

PYTHONPATH=src python -c "import flask; print(getattr(flask, '__version__', 'flask_ok'))"
```
> 说明：当前仓库为离线演示版，`flask/pypdf/docx` 最小实现已内置在 `src/` 下，不依赖二进制 wheel 文件。


### 1.3 投放文档（固定文件夹）
请将制度文档放入：

```text
docs/policies/
```

支持格式：
- `.pdf`
- `.docx`
- `.txt`
- `.md`

建议命名方式（便于后续管理）：
- `员工手册_v2026-01-01.pdf`
- `差旅报销制度_v2026-02-15.docx`

### 1.4 启动（可复现命令）

```bash
python src/app.py
```


### 1.5 首页可访问性验证
保持服务运行后，另开一个终端执行：
```bash
curl -i http://127.0.0.1:8000
```
预期返回 `HTTP/1.0 200 OK` 或 `HTTP/1.1 200 OK`。


浏览器访问：
```text
http://127.0.0.1:8000
```


### 1.6 使用流程

1. 将文档复制到 `docs/policies/`。
2. 打开页面后点击「重建索引」。
3. 输入员工问题并查看回答与引用来源。

---

## 2. 你后续在哪里补充文档？

你只需要把新制度文件继续放到固定目录：

```text
docs/policies/
```

然后在页面点击一次「重建索引」即可生效，无需改代码。

---

## 3. 当前版本说明

- 仅中文界面与中文问答。
- 回答由本地检索拼接生成，并附带来源片段。
- 如果检索不到依据，会提示补充制度文件或联系对应部门。

---

## 4. 后续部署建议（README 指南）

> 你当前没有部署资源，因此建议先完成本地演示验收，再进入云部署。

### 路线A：最低运维成本（推荐）
适合尽快让全员试用。

1. **容器化服务**（本项目打包为 Docker 镜像）
2. 部署到云容器平台（如阿里云/腾讯云/华为云容器服务）
3. 文档目录挂载云存储（对象存储或文件存储）
4. 配置企业域名 + HTTPS
5. 接入企业微信/飞书入口（可选）

### 路线B：公司内网私有部署
适合对数据隔离要求高的场景。

1. 在公司内网 Linux 服务器部署 Python 服务
2. 使用 Nginx 反向代理并启用 HTTPS
3. 文档目录挂载内网共享盘
4. 结合 AD/SSO 做员工登录鉴权（后续迭代）

### 上线前建议清单
- 准备制度文件正式版本与生效日期
- 准备 30~50 条验收问题（请假、报销、设备领用等）
- 对答案做人工抽检（准确性/引用是否正确）
- 明确免责声明：最终以制度原文和审批结果为准

---

## 5. 常见问题

### Q1: 文档更新后为何回答没变？
A: 需要重新点击页面中的「重建索引」。

### Q2: 回答不够精准怎么办？
A: 可在问题中增加条件（城市、岗位、费用类型、审批节点等），并补充更完整的制度文档。

### Q3: 是否可以接入大模型？
A: 可以。在后续迭代中可接入企业可用的大模型 API，用于摘要生成与多轮对话增强。

## 6. 发布到 GitHub 并创建拉取请求（PR）

### 6.1 首次推送到 GitHub
```bash
git init
git add .
git commit -m "feat: 初始化内部规章制度智能问答助手"
git branch -M main
git remote add origin <你的仓库地址>
git push -u origin main
```

### 6.2 开发新功能并提交到分支
```bash
git checkout -b feat/xxx
git add .
git commit -m "feat: 你的功能说明"
git push -u origin feat/xxx
```

### 6.3 创建 Pull Request（两种方式）

#### 方式A：GitHub 网页
1. 推送分支后，打开仓库页面。
2. 点击 `Compare & pull request`。
3. 填写标题和描述并提交。

#### 方式B：GitHub CLI（推荐）
先安装并登录：
```bash
gh auth login
```

创建 PR：
```bash
gh pr create --base main --head feat/xxx --title "feat: 你的功能标题" --body "变更说明"
```

查看 PR 列表：
```bash
gh pr list
```

### 6.4 本项目已支持 PR 流程
- 已提供 `.github/pull_request_template.md`，创建 PR 时会自动带出模板。
- 已提供 `.github/workflows/ci.yml`，PR 提交后会自动执行基础检查（安装依赖、语法检查、首页可访问性 smoke test）。

