<div align="center">

<img src="assets/logo.svg" width="140" alt="AcadVex" />

<h1>AcadVex</h1>

<p><strong>学术合作网络 AI Agent 分析平台</strong></p>

<p>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white&style=flat-square" alt="Python"/></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white&style=flat-square" alt="FastAPI"/></a>
  <a href="https://react.dev"><img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black&style=flat-square" alt="React"/></a>
  <a href="https://langchain-ai.github.io/langgraph/"><img src="https://img.shields.io/badge/LangGraph-Agent-FF6B35?style=flat-square" alt="LangGraph"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-22C55E?style=flat-square" alt="Apache 2.0"/></a>
</p>

<p>
  <a href="README.md">English</a> ·
  <a href="#-快速开始">快速开始</a> ·
  <a href="#-系统架构">系统架构</a> ·
  <a href="#-扩展指南">扩展指南</a>
</p>

</div>

---

AcadVex 将预训练的 **FPGCL** 图神经网络包装进对话式 AI Agent。用自然语言描述你的研究需求——Agent 自动识别意图、路由到对应 Skill、调用 GNN 推理或 RAG 检索，以流式文字答案和交互式合作网络图呈现结果。

> **FPGCL** = Feat+ID 内容特征 + HAEGNN-MGPG 并行门控编码器 + IHGCL 对比学习。  
> Recall@20：**0.584**（DBLP）/ **0.860**（ACM）——**较 IHGCL 基线提升 +261%**。  
> 模型训练代码位于配套仓库 **[FPGCL](https://github.com/A-peiron/FPGCL)**。

---

## 功能特性

| | 功能 | 说明 |
|---|---|---|
| 🔮 | **合作潜力预测** | 调用预训练 FPGCL 模型（HAEGNN-MGPG + IHGCL）为任意作者对打分 |
| 🕸️ | **力导向网络图** | WebGL 渲染 4,057 节点 @ 60fps；全图与 2-hop 自我网络模式；拖拽固定、社群着色 |
| 🤖 | **17 工具 AI Agent** | ReAct 循环 + 7 个意图 Skill——每次查询只暴露相关工具子集 |
| 📚 | **混合 RAG** | ChromaDB 语义检索 + BM25 关键词匹配 + RRF 融合，支持冷启动作者发现 |
| ⚡ | **流式输出** | 逐 token SSE 输出，实时显示工具调用状态 |
| 🔭 | **全链路可观测性** | Langfuse 追踪每次 Agent 调用——工具、延迟、token 消耗 |
| 🛡️ | **安全防护** | Prompt 注入过滤（12 条正则规则）、2 KB 请求体上限、Skill 级工具白名单 |
| 💬 | **聊天历史** | localStorage 多会话持久化——刷新页面对话不丢失 |
| 🔌 | **易于扩展** | 注册表模式的工具与 Skill——两步新增能力 |

---

## 系统架构

![AcadVex 系统架构](assets/architecture.png)

---

## 技术栈

```
LLM            DeepSeek V3                 OpenAI 兼容 · 国内直连
Agent          LangGraph + 手写 ReAct      状态图 · Skill 路由 · SqliteSaver checkpoint
后端           FastAPI + Pydantic v2        异步 · 自动 OpenAPI 文档 · 严格 schema 验证
流式           Server-Sent Events           逐 token 输出，StreamingResponse + EventSource
前端           TypeScript + React 19        shadcn/ui + Tailwind CSS · react-force-graph WebGL
RAG            ChromaDB + BM25 + RRF        混合检索：语义 + 关键词融合
可观测性       Langfuse（自托管）           全链路 trace：工具 · 延迟 · token 消耗
图模型         FPGCL（HAEGNN-MGPG+IHGCL）  预训练于 DBLP/ACM 学术合作图
```

---

## 快速开始

**环境要求：** Docker Desktop · DeepSeek API Key

### 方式 A — Docker（推荐）

```bash
git clone https://github.com/A-peiron/AcadVex.git
cd AcadVex

cp .env.example .env            # 填入 DEEPSEEK_API_KEY

docker-compose up --build       # 后端 → :8000  前端 → :8080
```

打开 `http://localhost:8080`。

### 方式 B — 本地开发

**额外要求：** Python 3.10+ · Node.js 18+

```bash
git clone https://github.com/A-peiron/AcadVex.git
cd AcadVex

# 后端
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # 填入 DEEPSEEK_API_KEY
python -m uvicorn api.main:app --reload            # → http://localhost:8000/docs

# 前端（新终端）
cd frontend && npm install && npm run dev          # → http://localhost:5173
```

> **数据文件：** 先在 [FPGCL](https://github.com/A-peiron/FPGCL) 仓库运行 `export_for_app.py` 生成 `data/embeddings/` 和 `data/graph_stats/`，再执行 `python scripts/build_author_vectordb.py`。

---

## 项目结构

```
AcadVex/
├── agent/
│   ├── tools/
│   │   ├── __init__.py          ← TOOL_REGISTRY（17 个工具）
│   │   ├── collab_tools.py      ← predict_collaboration · search_author · network_stats
│   │   ├── author_tools.py      ← 6 个个人分析工具
│   │   ├── community_tools.py   ← 3 个社群分析工具
│   │   ├── network_tools.py     ← find_collab_path · suggest_team · overview
│   │   └── rag_tools.py         ← search_knowledge（ChromaDB + BM25）
│   ├── skills/
│   │   ├── __init__.py          ← SKILL_REGISTRY（7 个 Skill）
│   │   ├── collab.py            ← 触发词：合作 · 预测
│   │   ├── community.py         ← 触发词：社群 · 研究方向
│   │   ├── author_analysis.py   ← 触发词：影响力 · 新锐 · 对比
│   │   ├── team_formation.py    ← 触发词：组队 · 路径 · 六度
│   │   ├── research_landscape.py← 触发词：全局 · 概览 · 趋势
│   │   ├── collab_search.py     ← 触发词：找学者 · 搜索
│   │   └── general.py           ← 兜底 Skill
│   ├── loop.py                  ← 手写 ReAct 循环（流式 SSE + Langfuse）
│   ├── graph.py                 ← LangGraph 状态图（Skill 路由 + SqliteSaver）
│   └── prompts.py
├── api/
│   ├── main.py                  ← FastAPI 应用 · lifespan · CORS · SecurityMiddleware
│   ├── schemas.py               ← Pydantic 模型
│   ├── middleware/
│   │   ├── security.py          ← Prompt 注入过滤（12 条规则，2 KB 上限）
│   │   └── rate_limit.py        ← slowapi 限流（20 次/分钟/IP）
│   └── routes/
│       ├── chat.py              ← POST /api/chat/stream（SSE）
│       ├── authors.py           ← 搜索 · 详情 · 推荐 · 论文 · 影响力
│       ├── graph.py             ← 全图 · 自我网络
│       └── recommendations.py  ← POST /api/recommendations/by-keywords
├── frontend/src/
│   ├── App.tsx                  ← 双 Tab 布局（网络探索 + AI 对话）
│   ├── components/
│   │   ├── ForceGraphVisualization.tsx  ← WebGL 力导向图（4,057 节点 @ 60fps）
│   │   ├── ChatPanel.tsx        ← SSE 流式聊天 + ReactMarkdown
│   │   ├── ChatHistorySidebar.tsx       ← localStorage 多会话侧边栏
│   │   ├── AuthorCard / AuthorSearch / CollabRecommendations
│   │   ├── PaperList / AuthorInfluence
│   │   └── ErrorBoundary.tsx
│   └── hooks/
│       ├── useSSE.ts            ← SSE 流式 + 工具调用事件解析
│       └── useChatHistory.ts    ← localStorage 多会话持久化
├── model/inference.py           ← FPGCL 点积打分
├── rag/
│   ├── retriever.py             ← 三阶段混合检索（ChromaDB + BM25 + CrossEncoder）
│   └── build_index.py
├── memory/store.py              ← SqliteSaver 长期对话记忆
├── data/                        ← 见 data/README.md
├── scripts/                     ← 预计算中心性、社群主题、向量索引
├── tests/                       ← pytest 单元 + 集成 + 端到端测试
├── Dockerfile                   ← 后端镜像
├── frontend/Dockerfile          ← 前端多阶段构建（nginx）
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

---

## API 参考

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/stream` | SSE 流式 AI 对话 |
| GET | `/api/authors/search?q=Wei` | 姓名模糊搜索 |
| GET | `/api/authors/{id}` | 作者详情 |
| GET | `/api/authors/{id}/recommendations` | FPGCL Top-K 合作者推荐 |
| GET | `/api/authors/{id}/papers?page=&page_size=` | 分页论文列表 |
| GET | `/api/authors/{id}/influence` | 度 / 介数 / 接近中心性 |
| GET | `/api/graph/full` | 全图（4,057 节点 + 边） |
| GET | `/api/graph/ego?author_id=X&hops=2` | N-hop 自我网络 |
| POST | `/api/recommendations/by-keywords` | 冷启动关键词混合检索 |

---

## 扩展指南

**新增工具** — 两步，无需改动其他文件：
```
1.  agent/tools/my_tool.py      （复制 _template.py，实现工具函数）
2.  agent/tools/__init__.py     （在 TOOL_REGISTRY 中注册一行）
```

**新增 Skill** — 同样模式：
```
1.  agent/skills/my_skill.py    （复制 _template.py，设置 system_prompt + allowed_tools）
2.  agent/skills/__init__.py    （在 SKILL_REGISTRY 中注册一行）
```

更大的扩展请见 [`extensions/README.md`](extensions/README.md)：HITL 中断、MCP Server、云部署、安全加固。

---

## 安全说明

| 风险 | 防护措施 |
|------|---------|
| Prompt 注入 | 12 条正则过滤规则，到达 LLM 前拦截 · 系统提示与用户输入硬隔离 |
| 请求滥用 | `/api/chat` 请求体 2 KB 上限 · Skill 级 `allowed_tools` 白名单 |
| 工具滥用 | 最多 10 次 ReAct 迭代 · 工具错误返回结构化 JSON，不崩溃循环 |

---

## Roadmap

- [x] 结构化日志（structlog）· 指数退避重试（tenacity）· 限流（slowapi）· `/health` 端点
- [x] 聊天 UI 工具调用状态提示 · 停止生成按钮 · 消息复制 · 错误 Toast + 重试
- [x] Docker + docker-compose · 单元测试（pytest）· `.env.example`
- [ ] Demo 视频 · 答辩演示脚本

---

## 关联仓库

| 仓库 | 说明 |
|------|------|
| [FPGCL](https://github.com/A-peiron/FPGCL) | GNN 训练代码——HAEGNN-MGPG 编码器 + IHGCL 对比学习 |

---

<div align="center">
<sub>MIT License · 毕业研究项目 · 欢迎 PR</sub>
</div>
