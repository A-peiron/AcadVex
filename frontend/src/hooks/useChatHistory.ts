/**
 * useChatHistory.ts
 * -----------------
 * 聊天历史持久化 Hook（基于 localStorage）。
 *
 * 功能：
 *   1. 保存聊天消息到 localStorage
 *   2. 加载历史会话列表
 *   3. 恢复指定会话的消息
 *   4. 清除历史记录
 *   5. 自动生成会话标题（基于首条用户消息）
 *
 * 数据结构：
 *   {
 *     sessions: [
 *       {
 *         id: "uuid",
 *         title: "首条用户消息（截断到 50 字符）",
 *         messages: [{ role: "user" | "assistant", content: string }, ...],
 *         timestamp: number,
 *         lastUpdated: number
 *       },
 *       ...
 *     ]
 *   }
 */

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "acadvex_chat_history";
const MAX_SESSIONS = 50; // 最多保存 50 个会话
const MAX_TITLE_LENGTH = 50;

export interface ChatMessage {
    role: "user" | "assistant";
    content: string;
}

export interface ChatSession {
    id: string;
    title: string;
    messages: ChatMessage[];
    timestamp: number;
    lastUpdated: number;
}

interface ChatHistoryData {
    sessions: ChatSession[];
}

/**
 * 生成会话标题（基于首条用户消息）
 */
function generateTitle(messages: ChatMessage[]): string {
    const firstUserMsg = messages.find((m) => m.role === "user");
    if (!firstUserMsg) return "新对话";

    const content = firstUserMsg.content.trim();
    if (content.length <= MAX_TITLE_LENGTH) return content;
    return content.slice(0, MAX_TITLE_LENGTH) + "...";
}

/**
 * 从 localStorage 加载历史数据
 */
function loadFromStorage(): ChatHistoryData {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return { sessions: [] };
        return JSON.parse(raw);
    } catch {
        return { sessions: [] };
    }
}

/**
 * 保存到 localStorage
 */
function saveToStorage(data: ChatHistoryData): void {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (error) {
        console.error("Failed to save chat history:", error);
    }
}

/**
 * 聊天历史 Hook
 */
export function useChatHistory() {
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
    const [sessions, setSessions] = useState<ChatSession[]>([]);

    // 初始化：加载历史会话
    useEffect(() => {
        const data = loadFromStorage();
        setSessions(data.sessions);
    }, []);

    /**
     * 创建新会话
     */
    const createSession = (): string => {
        const newSession: ChatSession = {
            id: crypto.randomUUID(),
            title: "新对话",
            messages: [],
            timestamp: Date.now(),
            lastUpdated: Date.now(),
        };

        const data = loadFromStorage();
        data.sessions.unshift(newSession); // 新会话放在最前面

        // 限制会话数量
        if (data.sessions.length > MAX_SESSIONS) {
            data.sessions = data.sessions.slice(0, MAX_SESSIONS);
        }

        saveToStorage(data);
        setSessions(data.sessions);
        setCurrentSessionId(newSession.id);

        return newSession.id;
    };

    /**
     * 保存消息到指定会话
     */
    const saveMessage = useCallback((message: ChatMessage, sessionId: string): void => {
        saveMessageToSession(sessionId, message);
    }, []);

    /**
     * 保存消息到指定会话
     */
    const saveMessageToSession = (sessionId: string, message: ChatMessage): void => {
        const data = loadFromStorage();
        const session = data.sessions.find((s) => s.id === sessionId);

        if (!session) return;

        session.messages.push(message);
        session.lastUpdated = Date.now();

        // 如果是首条用户消息，更新标题
        if (session.messages.length === 1 && message.role === "user") {
            session.title = generateTitle(session.messages);
        }

        saveToStorage(data);
        setSessions(data.sessions);
    };

    /**
     * 加载指定会话的消息
     */
    const loadSession = useCallback((sessionId: string): ChatMessage[] => {
        const data = loadFromStorage();
        const session = data.sessions.find((s) => s.id === sessionId);
        return session?.messages || [];
    }, []);

    /**
     * 切换到指定会话
     */
    const switchSession = (sessionId: string): ChatMessage[] => {
        setCurrentSessionId(sessionId);
        return loadSession(sessionId);
    };

    /**
     * 删除指定会话
     */
    const deleteSession = (sessionId: string): void => {
        const data = loadFromStorage();
        data.sessions = data.sessions.filter((s) => s.id !== sessionId);
        saveToStorage(data);
        setSessions(data.sessions);

        if (currentSessionId === sessionId) {
            setCurrentSessionId(null);
        }
    };

    /**
     * 清除所有历史记录
     */
    const clearAllHistory = (): void => {
        localStorage.removeItem(STORAGE_KEY);
        setSessions([]);
        setCurrentSessionId(null);
    };

    /**
     * 获取所有会话列表（按最后更新时间降序）
     */
    const getAllSessions = (): ChatSession[] => {
        return [...sessions].sort((a, b) => b.lastUpdated - a.lastUpdated);
    };

    return {
        currentSessionId,
        sessions: getAllSessions(),
        createSession,
        saveMessage,
        loadSession,
        switchSession,
        deleteSession,
        clearAllHistory,
    };
}
