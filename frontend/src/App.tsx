/** App.tsx
 * 应用根组件（两个顶层 Tab）。
 *
 * Tab 1: 网络 + 分析（长页面可滚动，完全联动）
 *   - 力导向图（固定高度，点击节点更新下方所有信息）
 *   - 作者姓名搜索（也会更新下方所有信息）
 *   - 作者详情 / 推荐合作者 / 论文列表 / 影响力指标
 *
 * Tab 2: AI 对话（全屏）
 */

import { useState, useRef, useCallback } from "react";
import ChatPanel from "./components/ChatPanel";
import { ChatHistorySidebar } from "./components/ChatHistorySidebar";
import { useChatHistory } from "./hooks/useChatHistory";
import { AuthorCard } from "./components/AuthorCard";
import { AuthorSearch } from "./components/AuthorSearch";
import { CollabRecommendations } from "./components/CollabRecommendations";
import { PaperList } from "./components/PaperList";
import { AuthorInfluence } from "./components/AuthorInfluence";
import { ForceGraphVisualization } from "./components/ForceGraphVisualization";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Network, MessageSquare } from "lucide-react";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Toaster } from "@/components/ui/toaster";

export default function App() {
    const [selectedAuthorId, setSelectedAuthorId] = useState<number | null>(null);
    const authorSectionRef = useRef<HTMLDivElement>(null);

    const {
        currentSessionId,
        sessions,
        createSession,
        switchSession,
        deleteSession,
        clearAllHistory,
        saveMessage,
    } = useChatHistory();

    // 当前会话的消息（用于恢复 ChatPanel）
    const [chatKey, setChatKey] = useState(0);
    const [restoredMessages, setRestoredMessages] = useState<string[]>([]);

    // 创建新会话的回调
    const handleNeedSession = useCallback((): string => {
        return createSession();
    }, [createSession]);

    // 点击节点/搜索后，更新 ID 并滚动到作者详情区域
    const handleSelectAuthor = (id: number) => {
        setSelectedAuthorId(id);
        // 稍作延迟等待数据加载，再滚动
        setTimeout(() => {
            authorSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 100);
    };

    return (
        <ErrorBoundary>
            <div className="flex h-screen w-screen flex-col overflow-hidden bg-background text-foreground">
                <Tabs defaultValue="explore" className="flex flex-col flex-1 overflow-hidden">
                    <TabsList className="w-full justify-start rounded-none border-b px-4 h-12 shrink-0">
                        <TabsTrigger value="explore" className="gap-2">
                            <Network className="h-4 w-4" />
                            网络探索
                        </TabsTrigger>
                        <TabsTrigger value="chat" className="gap-2">
                            <MessageSquare className="h-4 w-4" />
                            AI 对话
                        </TabsTrigger>
                    </TabsList>

                    {/* ── Tab 1: 网络探索（长页面，可滚动） ── */}
                    <TabsContent
                        value="explore"
                        className="flex-1 m-0 overflow-y-auto data-[state=active]:block data-[state=inactive]:hidden"
                    >
                        {/* 力导向图（可滚动，占据更大高度） */}
                        <div className="relative bg-background border-b" style={{ height: "80vh" }}>
                            {/* 搜索栏叠加在图上方 */}
                            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 w-80">
                                <AuthorSearch onSelectAuthor={handleSelectAuthor} />
                            </div>
                            <ForceGraphVisualization
                                onNodeClick={handleSelectAuthor}
                                selectedAuthorId={selectedAuthorId}
                            />
                        </div>

                        {/* 作者信息区域（向下滚动查看） */}
                        <div ref={authorSectionRef} className="max-w-5xl mx-auto px-4 py-6 space-y-4">
                            <AuthorCard externalAuthorId={selectedAuthorId} />
                            <CollabRecommendations
                                authorId={selectedAuthorId}
                                onSelectAuthor={handleSelectAuthor}
                            />
                            <PaperList authorId={selectedAuthorId} />
                            <AuthorInfluence authorId={selectedAuthorId} />
                        </div>
                    </TabsContent>

                    {/* ── Tab 2: AI 对话（全屏，左侧历史 + 右侧聊天） ── */}
                    <TabsContent
                        value="chat"
                        className="flex-1 min-h-0 m-0 data-[state=active]:flex data-[state=inactive]:hidden"
                    >
                        <div className="flex w-full h-full">
                            {/* 左侧：聊天历史侧边栏 */}
                            <div className="w-64 shrink-0 border-r">
                                <ChatHistorySidebar
                                    sessions={sessions}
                                    currentSessionId={currentSessionId}
                                    onSelectSession={(sessionId) => {
                                        const msgs = switchSession(sessionId);
                                        // 把历史消息转成 ChatPanel 的字符串格式
                                        const restored = msgs.flatMap((m) => [
                                            m.role === "user" ? `你：${m.content}` : `助手：${m.content}`,
                                        ]);
                                        setRestoredMessages(restored);
                                        setChatKey((k) => k + 1);
                                    }}
                                    onDeleteSession={deleteSession}
                                    onCreateSession={() => {
                                        createSession();
                                        setRestoredMessages([]);
                                        setChatKey((k) => k + 1);
                                    }}
                                    onClearAll={() => {
                                        clearAllHistory();
                                        setRestoredMessages([]);
                                        setChatKey((k) => k + 1);
                                    }}
                                />
                            </div>

                            {/* 右侧：聊天面板 */}
                            <div className="flex-1 min-h-0 overflow-hidden">
                                <ChatPanel
                                    key={chatKey}
                                    sessionId={currentSessionId}
                                    initialMessages={restoredMessages}
                                    onNeedSession={handleNeedSession}
                                    onSaveMessage={saveMessage}
                                />
                            </div>
                        </div>
                    </TabsContent>
                </Tabs>
                <Toaster />
            </div>
        </ErrorBoundary>
    );
}
