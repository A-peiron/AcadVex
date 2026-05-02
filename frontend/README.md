<div align="center">

<h2>AcadVex Frontend</h2>

<p>
  <a href="https://react.dev"><img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black&style=flat-square" alt="React"/></a>
  <a href="https://www.typescriptlang.org"><img src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white&style=flat-square" alt="TypeScript"/></a>
  <a href="https://vitejs.dev"><img src="https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white&style=flat-square" alt="Vite"/></a>
  <a href="https://tailwindcss.com"><img src="https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?logo=tailwindcss&logoColor=white&style=flat-square" alt="Tailwind"/></a>
</p>

<p><a href="README_zh.md">中文文档</a></p>

</div>

---

Dual-tab UI: **Academic Network Visualization** + **AI Streaming Chat**.

## Features

| | Feature | Technology |
|---|---|---|
| 🕸️ | **Force-Directed Graph** | react-force-graph WebGL — 4,057 nodes @ 60fps, drag-to-pin, community coloring |
| 🤖 | **Streaming AI Chat** | SSE token-by-token output with real-time tool-call status indicators |
| 💬 | **Multi-Session History** | localStorage persistence — conversations survive page refresh, switchable sidebar |
| 🛑 | **Stop Generation** | Interrupt AI output at any time; already-streamed content is preserved |
| 📋 | **Message Copy** | Hover bubble reveals copy button; Toast confirms clipboard write |
| ⚠️ | **Error Handling** | Global ErrorBoundary + top-right Toast — no blank screen on failure |

---

## Quick Start

```bash
npm install
npm run dev        # dev server → http://localhost:5173
```

Requires the backend running at `http://localhost:8000` (Vite proxy is pre-configured).

## Production Build

```bash
npm run build      # outputs to dist/
```

For Docker deployment, the multi-stage `Dockerfile` builds automatically and serves via nginx.

---

## Directory Structure

```
src/
├── App.tsx                          ← dual-tab layout entry point
├── components/
│   ├── ForceGraphVisualization.tsx  ← WebGL force graph (full / ego-network modes)
│   ├── NetworkGraph.tsx             ← Network Explorer tab container
│   ├── ChatPanel.tsx                ← SSE streaming chat with ReactMarkdown
│   ├── ChatHistorySidebar.tsx       ← multi-session sidebar
│   ├── AuthorCard.tsx               ← author detail card
│   ├── AuthorSearch.tsx             ← author search dropdown
│   ├── AuthorInfluence.tsx          ← centrality metrics display
│   ├── CollabRecommendations.tsx    ← FPGCL recommendation list
│   ├── PaperList.tsx                ← paginated paper list
│   └── ErrorBoundary.tsx            ← global error boundary
├── hooks/
│   ├── useSSE.ts                    ← SSE event parser (token / tool_call / done)
│   └── useChatHistory.ts            ← localStorage multi-session management
└── lib/utils.ts                     ← shadcn/ui utility functions
```

---

## Tech Stack

```
UI Framework   React 19 + TypeScript
Styling        Tailwind CSS + shadcn/ui
Graph          react-force-graph (WebGL / Three.js)
Markdown       ReactMarkdown + remark-gfm
Build          Vite 6
```
