/** AuthorSearch.tsx
 * 作者姓名模糊搜索组件（Combobox 实时搜索）。
 *
 * 功能：
 *   1. 输入姓名关键词（如 "Wei"），实时调用 /api/authors/search
 *   2. 显示匹配结果列表（最多 10 条）
 *   3. 点击结果 → 触发 onSelectAuthor 回调（更新 NetworkGraph + AuthorCard）
 *   4. 防抖 300ms 避免频繁请求
 *   5. 显示加载状态和错误提示
 */

import { useState, useEffect, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import AuthorBadge from "@/components/ui/AuthorBadge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { Search, X } from "lucide-react";

interface SearchResult {
    id: number;
    name: string;
    community_id: number;
    research_area: string;
    paper_count: number;
    degree: number;
}

interface AuthorSearchProps {
    onSelectAuthor: (authorId: number) => void;
}

export function AuthorSearch({ onSelectAuthor }: AuthorSearchProps) {
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [showDropdown, setShowDropdown] = useState(false);
    const debounceTimer = useRef<number | null>(null);
    const wrapperRef = useRef<HTMLDivElement>(null);

    // 点击外部关闭下拉框
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    // 防抖搜索
    useEffect(() => {
        if (debounceTimer.current) {
            clearTimeout(debounceTimer.current);
        }

        if (!query.trim()) {
            setResults([]);
            setShowDropdown(false);
            return;
        }

        debounceTimer.current = window.setTimeout(async () => {
            setLoading(true);
            setError("");

            try {
                const response = await fetch(
                    `/api/authors/search?q=${encodeURIComponent(query.trim())}&limit=10`
                );

                if (!response.ok) {
                    setError("搜索失败，请稍后重试");
                    setResults([]);
                    return;
                }

                const data = await response.json();
                setResults(data);
                setShowDropdown(true);
            } catch {
                setError("网络错误，请检查连接");
                setResults([]);
            } finally {
                setLoading(false);
            }
        }, 300);

        return () => {
            if (debounceTimer.current) {
                clearTimeout(debounceTimer.current);
            }
        };
    }, [query]);

    const handleSelect = (author: SearchResult) => {
        setQuery(author.name);
        setShowDropdown(false);
        onSelectAuthor(author.id);
    };

    const handleClear = () => {
        setQuery("");
        setResults([]);
        setShowDropdown(false);
        setError("");
    };

    return (
        <div ref={wrapperRef} className="relative w-full">
            {/* 搜索输入框 */}
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => results.length > 0 && setShowDropdown(true)}
                    placeholder="搜索作者姓名（如 Wei Chen）"
                    className="pl-9 pr-9"
                />
                {query && (
                    <button
                        onClick={handleClear}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                        <X className="h-4 w-4" />
                    </button>
                )}
            </div>

            {/* 加载指示器 */}
            {loading && (
                <div className="absolute right-12 top-1/2 -translate-y-1/2">
                    <LoadingSpinner size="sm" />
                </div>
            )}

            {/* 下拉结果列表 */}
            {showDropdown && (results.length > 0 || error) && (
                <Card className="absolute z-50 w-full mt-1 max-h-80 overflow-y-auto shadow-lg">
                    {error && (
                        <div className="p-3 text-sm text-destructive">
                            {error}
                        </div>
                    )}

                    {results.length > 0 && (
                        <div className="py-1">
                            {results.map((author) => (
                                <button
                                    key={author.id}
                                    onClick={() => handleSelect(author)}
                                    className="w-full px-3 py-2 text-left hover:bg-accent transition-colors"
                                >
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="font-medium text-sm">
                                            {author.name}
                                        </span>
                                        <AuthorBadge
                                            communityId={author.community_id}
                                            size="sm"
                                        />
                                        <span className="text-xs text-muted-foreground">
                                            ID: {author.id}
                                        </span>
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        {author.research_area}
                                    </div>
                                    <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
                                        <span>{author.degree} 位合作者</span>
                                        <span>{author.paper_count} 篇论文</span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}

                    {!error && results.length === 0 && query.trim() && !loading && (
                        <div className="p-3 text-sm text-muted-foreground text-center">
                            未找到匹配的作者
                        </div>
                    )}
                </Card>
            )}
        </div>
    );
}
