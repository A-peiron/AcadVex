<div align="center">

<h2>AcadVex Frontend</h2>

<p>
  <a href="https://react.dev"><img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black&style=flat-square" alt="React"/></a>
  <a href="https://www.typescriptlang.org"><img src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white&style=flat-square" alt="TypeScript"/></a>
  <a href="https://vitejs.dev"><img src="https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white&style=flat-square" alt="Vite"/></a>
  <a href="https://tailwindcss.com"><img src="https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?logo=tailwindcss&logoColor=white&style=flat-square" alt="Tailwind"/></a>
</p>

<p><a href="README.md">English</a></p>

</div>

---

双 Tab 交互界面：**学术网络可视化** + **AI 流式对话**。

## 功能亮点

| | 功能 | 技术 |
|---|---|---|
| 🕸️ | **力导向网络图** | react-force-graph WebGL，4,057 节点 @ 60fps，拖拽固定、社群着色 |
| 🤖 | **流式 AI 对话** | SSE token-by-token 输出，实时工具调用状态提示 |
| 💬 | **多会话历史** | localStorage 持久化，刷新不丢失，侧边栏切换 |
| 🛑 | **停止生成** | 随时中断 AI 输出，已生成内容保留 |
| 📋 | **消息复制** | Hover 气泡显示复制按钮，Toast 确认 |
| ⚠️ | **错误处理** | 全局 ErrorBoundary + 右上角 Toast 提示，不白屏 |

---

## 快速开始

```bash
npm install
npm run dev        # 开发服务器 → http://localhost:5173
```

需要后端运行在 `http://localhost:8000`（Vite 已配置代理）。

## 生产构建

```bash
npm run build      # 输出到 dist/
```

Docker 部署时，多阶段 `Dockerfile` 自动构建并由 nginx 提供服务。

---

## 目录结构

```
src/
├── App.tsx                          ← 双 Tab 布局入口
├── components/
│   ├── ForceGraphVisualization.tsx  ← WebGL 力导向图（全图 / ego 网络）
│   ├── NetworkGraph.tsx             ← 网络探索 Tab 容器
│   ├── ChatPanel.tsx                ← SSE 流式聊天面板
│   ├── ChatHistorySidebar.tsx       ← 多会话侧边栏
│   ├── AuthorCard.tsx               ← 作者详情卡片
│   ├── AuthorSearch.tsx             ← 作者搜索下拉
│   ├── AuthorInfluence.tsx          ← 中心性指标展示
│   ├── CollabRecommendations.tsx    ← FPGCL 推荐列表
│   ├── PaperList.tsx                ← 分页论文列表
│   └── ErrorBoundary.tsx            ← 全局错误边界
├── hooks/
│   ├── useSSE.ts                    ← SSE 事件解析（token / tool_call / done）
│   └── useChatHistory.ts            ← localStorage 多会话管理
└── lib/utils.ts                     ← shadcn/ui 工具函数
```

---

## 技术栈

```
UI 框架     React 19 + TypeScript
样式        Tailwind CSS + shadcn/ui
图可视化    react-force-graph（WebGL Three.js）
Markdown    ReactMarkdown + remark-gfm
构建工具    Vite 6
```
