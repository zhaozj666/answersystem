# 内部规章制度智能问答助手（企业知识库版）

这是一个面向企业内部员工的**本地知识库问答系统**。  
系统会读取 `docs/policies/` 中的制度文档（PDF / DOCX / TXT / MD），建立索引，并回答如“请假流程、报销规则、正式员工定义”等问题。

> 适合非开发人员使用：你只需要按步骤安装依赖、启动后端、打开浏览器。

---

## 1. 项目结构（前后端分离）

```text
answersystem-main/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   └── services/
│       ├── document_loader.py
│       ├── index_service.py
│       └── qa_service.py
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── docs/
│   └── policies/
└── README.md
```

---

## 2. 文档放在哪里？

请把公司制度文档放在：

```text
docs/policies/
```

支持格式：
- PDF
- DOCX
- TXT
- MD

---

## 3. 如何安装 Python 依赖（Windows 命令）

> 先确保已安装 Python 3.10+。

```bat
cd Desktop\answersystem-main
python -m pip install -r backend/requirements.txt
```

---

## 4. 如何启动后端（Windows 命令）

```bat
cd Desktop\answersystem-main
python backend/app.py
```

启动成功后，终端会显示 Flask 运行信息。

---

## 5. 如何打开页面

在浏览器打开：

```text
http://127.0.0.1:8000
```

> 不建议直接双击 `frontend/index.html`。正确方式是：**先启动后端，再通过上述地址访问**。

---

## 6. 如何重建索引

1. 确保文档已放入 `docs/policies/`
2. 打开页面左侧点击 **“重建索引”**
3. 页面会显示：`索引完成：X 个文件，Y 个片段`

---

## 7. 如何提问

在页面输入问题，例如：
- 什么是公司的正式员工？
- 试用期是多久？
- 年假规则是什么？

点击“提问”，系统会显示：
- 回答内容
- 引用来源（文件名、片段、得分）

如果未命中，系统会提示：**未检索到明确依据**。

---

## 8. 可用 API（后端）

- `GET /api/health`：健康检查
- `GET /api/status`：查看知识库状态
- `POST /api/reindex`：重建索引
- `POST /api/ask`：提交问题

---

## 9. 常见问题

### Q1：页面打不开怎么办？
- 确认后端是否已启动（执行 `python backend/app.py`）
- 确认访问地址是否为 `http://127.0.0.1:8000`
- 查看终端是否有报错

### Q2：知识库为空怎么办？
- 检查 `docs/policies/` 是否有文件
- 点击“重建索引”
- 看重建结果中是否有错误信息

### Q3：PDF 读不到内容怎么办？
- 先确认 PDF 不是图片扫描版
- 重建索引时观察后端日志中的“文本长度”
- 若长度接近 0，建议导出为可复制文本版 PDF 后再试

### Q4：为什么回答不准确？
- 问题可能太短，请增加关键词（例如“正式员工定义”、“年假天数”）
- 请确保员工手册等核心制度已放入目录并成功建索引

---

## 10. 非开发人员最简流程（3 步）

1. 放文档到 `docs/policies/`
2. 运行 `python backend/app.py`
3. 打开 `http://127.0.0.1:8000`，点击“重建索引”，然后提问

