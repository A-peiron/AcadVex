<div align="center">

<img src="assets/logo.svg" width="140" alt="AcadVex" />

<h1>AcadVex</h1>

<p><strong>学术合作网络 AI Agent 分析平台</strong></p>

<p>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white&style=flat-square" alt="Python"/></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white&style=flat-square" alt="FastAPI"/></a>
  <a href="https://react.dev"><img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black&style=flat-square" alt="React"/></a>
  <a href="https://langchain-ai.github.io/langgraph/"><img src="https://img.shields.io/badge/LangGraph-Agent-FF6B35?style=flat-square" alt="LangGraph"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-22C55E?style=flat-square" alt="MIT"/></a>
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

> 模型训练代码位于配套仓库 **[FPGCL](https://github.com/A-peiron/FPGCL)**。

---

## 功能特性

| | 功能 | 说明 |
|---|---|---|
| 🔮 | **合作潜力预测** | 调用 FPGCL 模型（HAEGNN-MGPG + IHGCL）评分任意作者对 |
| 🕸️ | **社群分析** | 识别研究社群、成员排名、跨社群桥接研究者 |
| 📚 | **三阶段 RAG** | ChromaDB 向量检索 → BM25 关键词检索 → CrossEncoder 精排 |
| ⚡ | **流式输出** | FastAPI SSE 逐 token 实时响应 |
| 🔭 | **全链路可观测性** | Langfuse 记录每次 Agent 调用：工具、延迟、token 消耗 |
| 🛡️ | **安全防护** | Prompt 注入过滤、Pydantic 输出约束、Skill 工具白名单 |
| 🧠 | **长期记忆** | SQLite 跨会话保存用户研究偏好 |
| 🔌 | **易于扩展** | 注册表模式的工具与意图——两步新增能力 |

---

## 技术栈

```
LLM         DeepSeek V3 / Qwen-Plus     国内直连，OpenAI 兼容 API
Agent       LangGraph                   状态图 · Skill 路由 · SqliteSaver checkpoint
后端        FastAPI + Pydantic v2        异步 · 自动 OpenAPI 文档 · 严格 schema 验证
流式        Server-Sent Events           逐 token 输出，StreamingResponse + EventSource
前端        TypeScript + React + Vite   shadcn/ui 组件 · ECharts 力导向网络图
RAG         ChromaDB + BM25 + CE        三阶段：向量检索 → 关键词检索 → 精排
可观测性    Langfuse（自托管 Docker）   全链路 trace：工具 · 延迟 · token 消耗
记忆        SQLite                       跨会话用户偏好持久化
```

---

## 快速开始

**环境要求：** Python 3.10+ · Node.js 18+ · Docker Desktop · DeepSeek 或 Qwen API Key

```bash
# 克隆
git clone https://github.com/your-username/AcadVex.git
cd AcadVex

# Python 虚拟环境
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env            # 填入你的 API Key

# 启动 Langfuse 可观测性面板 → http://localhost:3000
docker-compose up -d

# 准备预计算数据（先在 FPGCL 仓库运行导出脚本）
# python ../FPGCL/export_for_app.py --dataset dblp --out ./data/

# 启动后端 → http://localhost:8000/docs
python -m api.main

# 启动前端 → http://localhost:5173
cd frontend && npm install && npm run dev
```

---

## 系统架构

![AcadVex 系统架构](assets/architecture.svg)

---

## 项目结构

```
AcadVex/
├── agent/
│   ├── tools/
│   │   ├── __init__.py          ← TOOL_REGISTRY
│   │   ├── collab_tools.py      ← FPGCL 推理封装
│   │   ├── community_tools.py
│   │   ├── author_tools.py
│   │   ├── network_tools.py
│   │   ├── rag_tools.py
│   │   └── _template.py         ← 复制此文件新增工具
│   ├── skills/
│   │   ├── __init__.py          ← SKILL_REGISTRY
│   │   ├── collab_skill.py
│   │   ├── community_skill.py
│   │   ├── author_skill.py
│   │   └── _template.py         ← 复制此文件新增 Skill
│   ├── loop.py                  ← 手写 ReAct 循环（学习用）
│   ├── graph.py                 ← LangGraph 状态图（生产版本）
│   └── prompts.py
├── api/                         ← FastAPI 后端
├── rag/                         ← 三阶段检索流水线
├── memory/                      ← SQLite 跨会话记忆
├── model/                       ← FPGCL 推理封装
├── data/                        ← 预计算数据【git 忽略】
├── frontend/                    ← TypeScript + React + ECharts
├── extensions/
│   └── README.md                ← HITL · MCP Server · 云部署 · 安全加固
├── tests/
│   └── demo_scenarios.py
├── assets/
│   └── logo.svg
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

---

## 扩展指南

**新增工具** — 两步，无需改动其他文件：
```
1.  agent/tools/my_tool.py      （复制 _template.py，实现工具函数）
2.  agent/tools/__init__.py     （在 TOOL_REGISTRY 中注册一行）
```

**新增意图（Skill）** — 同样模式：
```
1.  agent/skills/my_skill.py    （复制 _template.py，设置 system_prompt + allowed_tools）
2.  agent/skills/__init__.py    （在 SKILL_REGISTRY 中注册一行）
```

更大的扩展请见 [`extensions/README.md`](extensions/README.md)：HITL 中断、MCP Server、云部署、安全加固。

---

## 安全说明

| 风险 | 防护措施 |
|------|---------|
| Prompt 注入 | 输入关键词过滤（到达 LLM 前拦截）· 系统提示与用户输入硬隔离 |
| Prompt 泄露 | 系统提示不含敏感信息 · Pydantic `extra="forbid"` 约束所有输出 schema |
| 工具滥用 | Skill 级 `allowed_tools` 白名单 · LangGraph 最大工具调用深度限制 |

---

## 关联仓库

| 仓库 | 说明 |
|------|------|
| [FPGCL](https://github.com/your-username/FPGCL) | GNN 训练代码——HAEGNN-MGPG 编码器 + IHGCL 对比学习 |

---

<div align="center">
<sub>MIT License · 毕业研究项目 · 欢迎 PR</sub>
</div>
