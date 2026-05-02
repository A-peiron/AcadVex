/**
 * ChatHistorySidebar.tsx
 * ----------------------
 * 聊天历史侧边栏组件。
 *
 * 功能：
 *   1. 显示历史会话列表（按最后更新时间降序）
 *   2. 点击会话 → 恢复对话
 *   3. 删除单个会话
 *   4. 清除所有历史
 *   5. 创建新会话
 *   6. 高亮当前会话
 */

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { History, Plus, Trash2, MessageSquare } from "lucide-react";
import type { ChatSession } from "@/hooks/useChatHistory";

interface ChatHistorySidebarProps {
    sessions: ChatSession[];
    currentSessionId: string | null;
    onSelectSession: (sessionId: string) => void;
    onDeleteSession: (sessionId: string) => void;
    onCreateSession: () => void;
    onClearAll: () => void;
}

export function ChatHistorySidebar({
    sessions,
    currentSessionId,
    onSelectSession,
    onDeleteSession,
    onCreateSession,
    onClearAll,
}: ChatHistorySidebarProps) {
    /**
     * 格式化时间戳为相对时间
     */
    const formatRelativeTime = (timestamp: number): string => {
        const now = Date.now();
        const diff = now - timestamp;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return "刚刚";
        if (minutes < 60) return `${minutes} 分钟前`;
        if (hours < 24) return `${hours} 小时前`;
        if (days < 7) return `${days} 天前`;
        return new Date(timestamp).toLocaleDateString("zh-CN");
    };

    return (
        <Card className="h-full flex flex-col rounded-none border-0 border-r">
            {/* 标题栏 */}
            <CardHeader className="pb-3 border-b shrink-0">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                        <History className="h-4 w-4" />
                        聊天历史
                    </CardTitle>
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={onCreateSession}
                        className="h-7 px-2"
                    >
                        <Plus className="h-4 w-4" />
                    </Button>
                </div>
            </CardHeader>

            {/* 会话列表 */}
            <CardContent className="flex-1 p-0 overflow-hidden">
                {sessions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center p-4">
                        <MessageSquare className="h-12 w-12 text-muted-foreground mb-3 opacity-50" />
                        <p className="text-sm text-muted-foreground">
                            暂无聊天记录
                        </p>
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={onCreateSession}
                            className="mt-3"
                        >
                            <Plus className="h-4 w-4 mr-1" />
                            开始新对话
                        </Button>
                    </div>
                ) : (
                    <>
                        <ScrollArea className="h-full">
                            <div className="p-2 space-y-1">
                                {sessions.map((session) => {
                                    const isActive = session.id === currentSessionId;
                                    return (
                                        <div
                                            key={session.id}
                                            className={`
                                                group relative p-3 rounded-lg border transition-colors cursor-pointer
                                                ${
                                                    isActive
                                                        ? "bg-accent border-primary"
                                                        : "hover:bg-accent/50 border-transparent"
                                                }
                                            `}
                                            onClick={() => onSelectSession(session.id)}
                                        >
                                            {/* 标题 */}
                                            <div className="flex items-start gap-2 mb-1.5">
                                                <MessageSquare className="h-4 w-4 shrink-0 mt-0.5 text-muted-foreground" />
                                                <p className="text-sm font-medium leading-tight flex-1 line-clamp-2">
                                                    {session.title}
                                                </p>
                                            </div>

                                            {/* 元信息 */}
                                            <div className="flex items-center justify-between text-xs text-muted-foreground ml-6">
                                                <span>
                                                    {formatRelativeTime(session.lastUpdated)}
                                                </span>
                                                <Badge variant="secondary" className="text-xs">
                                                    {session.messages.length} 条
                                                </Badge>
                                            </div>

                                            {/* 删除按钮 */}
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onDeleteSession(session.id);
                                                }}
                                                className="
                                                    absolute top-2 right-2 p-1 rounded
                                                    opacity-0 group-hover:opacity-100
                                                    hover:bg-destructive/10 hover:text-destructive
                                                    transition-opacity
                                                "
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </button>
                                        </div>
                                    );
                                })}
                            </div>
                        </ScrollArea>

                        {/* 底部操作栏 */}
                        <div className="p-2 border-t shrink-0">
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={onClearAll}
                                className="w-full text-xs text-muted-foreground hover:text-destructive"
                            >
                                <Trash2 className="h-3.5 w-3.5 mr-1" />
                                清除所有历史
                            </Button>
                        </div>
                    </>
                )}
            </CardContent>
        </Card>
    );
}
