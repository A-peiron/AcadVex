/** ChatPanel.tsx
 * 聊天面板组件（Tailwind + shadcn/ui 重构版）。
 *
 * 布局：
 *   - 消息列表区域（flex-1，可滚动）
 *   - 底部输入栏（Input + Button 固定在底部）
 *
 * 样式来源：Tailwind CSS + shadcn/ui Button/Input 组件
 */

import { type KeyboardEvent, useRef, useEffect, useState, memo, useMemo, useCallback } from "react";
import { useSSE } from "../hooks/useSSE";
import type { ChatMessage } from "../hooks/useChatHistory";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { Send, Square, Loader2, Copy, Check } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useToast } from "@/hooks/use-toast";

interface ChatPanelProps {
    onMessagesChange?: (messages: string[]) => void;
    sessionId?: string | null;
    initialMessages?: string[];
    onNeedSession?: () => string;
    onSaveMessage?: (message: ChatMessage, sessionId: string) => void;
}

// 消息复制按钮（memo 优化）
const CopyButton = memo(({ text }: { text: string }) => {
    const [copied, setCopied] = useState(false);
    const { toast } = useToast();
    const handleCopy = useCallback(() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        toast({ title: "已复制到剪贴板" });
        setTimeout(() => setCopied(false), 2000);
    }, [text, toast]);
    return (
        <button
            onClick={handleCopy}
            className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-black/10"
            aria-label="复制"
        >
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
        </button>
    );
});
CopyButton.displayName = "CopyButton";

function ChatPanel({ sessionId, initialMessages, onNeedSession, onSaveMessage }: ChatPanelProps) {
    // 使用 ref 持有最新的 sessionId，避免 stale closure
    const sessionIdRef = useRef<string | null>(sessionId || null);
    const onSaveMessageRef = useRef(onSaveMessage);

    useEffect(() => { sessionIdRef.current = sessionId || null; }, [sessionId]);
    useEffect(() => { onSaveMessageRef.current = onSaveMessage; }, [onSaveMessage]);

    const { messages, input, setInput, loading, toolStatus, sendMessage: sendMessageSSE, stopGeneration } = useSSE(
        initialMessages ?? [],
        () => sessionIdRef.current,
        (userMsg, assistantMsg) => {
            if (!onSaveMessageRef.current || !sessionIdRef.current) return;
            onSaveMessageRef.current({ role: "user", content: userMsg }, sessionIdRef.current);
            onSaveMessageRef.current({ role: "assistant", content: assistantMsg }, sessionIdRef.current);
        }
    );
    const bottomRef = useRef<HTMLDivElement>(null);

    // 包装 sendMessage，在首次发送时创建 session
    const sendMessage = useCallback(() => {
        if (!sessionIdRef.current && onNeedSession) {
            const newSessionId = onNeedSession();
            sessionIdRef.current = newSessionId;
        }
        sendMessageSSE();
    }, [sendMessageSSE, onNeedSession]);

    // 每次消息更新后自动滚动到底部
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }, [sendMessage]);

    // useMemo 缓存渲染的消息列表
    const renderedMessages = useMemo(() => {
        return messages.map((msg, idx) => {
            const isUser = msg.startsWith("你：");
            const isError = msg.startsWith("错误：");
            const text = msg.replace(/^(你：|助手：|错误：)/, "");

            return (
                <div key={idx} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                    <div className={`relative group max-w-[85%] rounded-2xl px-4 py-2.5 text-sm break-words ${
                        isUser
                            ? "bg-primary text-primary-foreground rounded-br-sm"
                            : isError
                              ? "bg-destructive/10 text-destructive rounded-bl-sm"
                              : "bg-muted text-foreground rounded-bl-sm"
                    }`}>
                        {text ? (
                            isUser ? (
                                <div className="whitespace-pre-wrap">{text}</div>
                            ) : (
                                <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-headings:mt-3 prose-headings:mb-2 prose-table:text-xs">
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            table: ({ ...props }) => (
                                                <div className="overflow-x-auto my-2">
                                                    <table className="border-collapse border border-border" {...props} />
                                                </div>
                                            ),
                                            th: ({ ...props }) => (
                                                <th className="border border-border px-2 py-1 bg-muted font-semibold text-left" {...props} />
                                            ),
                                            td: ({ ...props }) => (
                                                <td className="border border-border px-2 py-1" {...props} />
                                            ),
                                            code: ({ className, children, ...props }) => {
                                                const isInline = !className?.includes('language-');
                                                return isInline ? (
                                                    <code className="bg-muted px-1 py-0.5 rounded text-xs" {...props}>{children}</code>
                                                ) : (
                                                    <code className="block bg-muted p-2 rounded text-xs overflow-x-auto" {...props}>{children}</code>
                                                );
                                            },
                                        }}
                                    >
                                        {text}
                                    </ReactMarkdown>
                                </div>
                            )
                        ) : (
                            <LoadingSpinner size="sm" />
                        )}
                        {text && <CopyButton text={text} />}
                    </div>
                </div>
            );
        });
    }, [messages]);

    return (
        <div className="flex h-full min-h-0 flex-col bg-background overflow-hidden">
            {/* ── 头部 ── */}
            <div className="shrink-0 border-b px-4 py-3">
                <h1 className="text-lg font-semibold tracking-tight">AcadVex Chat</h1>
                <p className="text-xs text-muted-foreground">
                    学术合作推荐 AI Agent
                </p>
            </div>

            {/* ── 消息列表 ── */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 scroll-smooth">
                {messages.length === 0 ? (
                    <div className="flex h-full items-center justify-center">
                        <div className="text-center space-y-2">
                            <p className="text-sm text-muted-foreground">
                                试试问我：
                            </p>
                            <div className="space-y-1">
                                {[
                                    "Author 42 和 Author 88 的合作潜力？",
                                    "帮我找做图神经网络的学者",
                                    "帮我组建一个 3 人研究团队",
                                ].map((hint) => (
                                    <button
                                        key={hint}
                                        className="block w-full rounded-md border border-dashed px-3 py-2 text-left text-sm text-muted-foreground hover:border-primary hover:text-primary transition-colors"
                                        onClick={() => setInput(hint)}
                                    >
                                        {hint}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                ) : (
                    renderedMessages
                )}
                <div ref={bottomRef} />
            </div>

            {/* ── 工具状态提示 ── */}
            {toolStatus && (
                <div className="shrink-0 flex items-center gap-2 px-4 py-2 bg-muted/50 text-sm text-muted-foreground border-t">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {toolStatus}
                </div>
            )}

            {/* ── 输入栏 ── */}
            <div className="shrink-0 border-t px-4 py-3">
                <div className="flex gap-2 items-end">
                    <Textarea
                        className="flex-1 min-h-[60px] max-h-[200px] resize-none"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="输入你的问题...（Shift+Enter 换行）"
                        disabled={loading}
                        rows={1}
                    />
                    {loading ? (
                        <Button onClick={stopGeneration} variant="destructive" size="icon" aria-label="停止">
                            <Square className="h-4 w-4" />
                        </Button>
                    ) : (
                        <Button onClick={sendMessage} disabled={!input.trim()} size="icon" aria-label="发送">
                            <Send className="h-4 w-4" />
                        </Button>
                    )}
                </div>
            </div>
        </div>
    );
}

export default memo(ChatPanel);
