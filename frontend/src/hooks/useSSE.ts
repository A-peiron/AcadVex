import { useState, useRef } from "react";
import { toast } from "@/hooks/use-toast";

const TOOL_LABELS: Record<string, string> = {
    search_author: "正在搜索作者",
    get_author_influence: "正在分析影响力",
    find_collab_opportunities: "正在查找合作机会",
    suggest_team: "正在组建团队",
    find_collab_path: "正在查找合作路径",
    compare_authors: "正在对比作者",
    get_collab_strength: "正在计算合作强度",
    find_rising_stars: "正在发现新锐学者",
    get_community_leaders: "正在分析社群领袖",
    get_network_overview: "正在获取网络概览",
};

export function useSSE(initialMessages: string[] = [], getSessionId: (() => string | null) | null = null, onComplete?: (userMsg: string, assistantMsg: string) => void) {
    const [messages, setMessages] = useState<string[]>(initialMessages);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [toolStatus, setToolStatus] = useState<string | null>(null);
    const abortRef = useRef<AbortController | null>(null);

    const stopGeneration = () => {
        abortRef.current?.abort();
    };

    const sendMessage = async () => {
        if (!input.trim() || loading) return;

        const userMessage = input;
        setMessages((prev) => [...prev, `你：${userMessage}`, "助手："]);
        setInput("");
        setLoading(true);
        setToolStatus(null);

        const controller = new AbortController();
        abortRef.current = controller;

        // 获取当前 sessionId
        const currentSessionId = getSessionId ? getSessionId() : null;

        let assistantText = "";
        try {
            const response = await fetch("/api/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: userMessage,
                    session_id: currentSessionId
                }),
                signal: controller.signal,
            });

            if (!response.body) throw new Error("响应体为空");

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop()!;

                for (const part of parts) {
                    const dataLine = part.split('\n').find(l => l.startsWith('data: '));
                    if (!dataLine) continue;
                    try {
                        const event = JSON.parse(dataLine.slice(6));
                        if (event.type === 'token') {
                            assistantText += event.content;
                            setMessages((prev) => {
                                const next = [...prev];
                                next[next.length - 1] = `助手：${assistantText}`;
                                return next;
                            });
                        } else if (event.type === 'tool_call') {
                            setToolStatus(TOOL_LABELS[event.name] ?? `正在执行 ${event.name}`);
                        } else if (event.type === 'done') {
                            setToolStatus(null);
                        } else if (event.type === 'error') {
                            toast({ title: "请求失败", description: event.content, variant: "destructive" });
                        }
                    } catch {
                        // 忽略解析失败的帧
                    }
                }
            }
            // 流结束后保存消息对
            if (assistantText) {
                onComplete?.(userMessage, assistantText);
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                // 用户主动停止
                if (assistantText) {
                    // 有部分内容：保存已生成的内容
                    onComplete?.(userMessage, assistantText);
                } else {
                    // 无内容（工具调用阶段被截断）：把空气泡替换为提示，避免永久转圈
                    setMessages((prev) => {
                        const next = [...prev];
                        next[next.length - 1] = "助手：（已停止，请重新提问）";
                        return next;
                    });
                }
            } else {
                toast({
                    title: "请求失败",
                    description: error instanceof Error ? error.message : "未知错误",
                    variant: "destructive",
                });
                setMessages((prev) => [
                    ...prev,
                    `错误：${error instanceof Error ? error.message : "请求失败"}`,
                ]);
            }
        } finally {
            abortRef.current = null;
            setLoading(false);
            setToolStatus(null);
        }
    };

    return { messages, setMessages, input, setInput, loading, toolStatus, sendMessage, stopGeneration };
}

