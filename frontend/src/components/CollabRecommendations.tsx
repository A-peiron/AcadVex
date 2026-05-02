/** CollabRecommendations.tsx
 * 合作者推荐组件（基于 FPGCL 点积相似度）。
 *
 * 功能：
 *   1. 接收 authorId，调用 /api/authors/{id}/recommendations
 *   2. 显示 Top-K 推荐结果（默认 10 条）
 *   3. 每个推荐卡片显示：姓名、相似度分数、社群、研究领域、共同关键词
 *   4. 点击推荐卡片 → 触发 onSelectAuthor（更新 NetworkGraph + AuthorCard）
 *   5. 支持调整 top_k 参数
 */

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import AuthorBadge from "@/components/ui/AuthorBadge";
import ErrorMessage from "@/components/ui/ErrorMessage";
import { Sparkles, Users, FileText } from "lucide-react";

interface Recommendation {
    id: number;
    name: string;
    score: number;
    community_id: number;
    research_area: string;
    paper_count: number;
    degree: number;
    common_keywords: string[];
}

interface CollabRecommendationsProps {
    authorId: number | null;
    topK?: number;
    onSelectAuthor?: (authorId: number) => void;
}

export function CollabRecommendations({
    authorId,
    topK = 10,
    onSelectAuthor,
}: CollabRecommendationsProps) {
    const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!authorId) {
            setRecommendations([]);
            return;
        }

        const fetchRecommendations = async () => {
            setLoading(true);
            setError("");

            try {
                const response = await fetch(
                    `/api/authors/${authorId}/recommendations?top_k=${topK}`
                );

                if (!response.ok) {
                    setError(
                        response.status === 404
                            ? "作者不存在"
                            : "推荐失败，请稍后重试"
                    );
                    setRecommendations([]);
                    return;
                }

                const data = await response.json();
                setRecommendations(data);
            } catch {
                setError("网络错误，请检查连接");
                setRecommendations([]);
            } finally {
                setLoading(false);
            }
        };

        fetchRecommendations();
    }, [authorId, topK]);

    if (!authorId) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                        <Sparkles className="h-4 w-4" />
                        合作者推荐
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground text-center py-4">
                        选择作者后查看推荐合作者
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                    <Sparkles className="h-4 w-4" />
                    合作者推荐（基于 FPGCL 模型）
                </CardTitle>
            </CardHeader>

            <CardContent className="space-y-3">
                {/* 加载骨架 */}
                {loading && (
                    <div className="space-y-3">
                        {Array.from({ length: 3 }).map((_, i) => (
                            <div key={i} className="p-3 border rounded-lg space-y-2">
                                <div className="flex items-center gap-2">
                                    <Skeleton className="h-4 w-32" />
                                    <Skeleton className="h-4 w-16 rounded-full" />
                                </div>
                                <Skeleton className="h-3 w-48" />
                                <div className="flex gap-2">
                                    <Skeleton className="h-4 w-20 rounded-full" />
                                    <Skeleton className="h-4 w-20 rounded-full" />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* 错误提示 */}
                {!loading && error && (
                    <ErrorMessage
                        message={error}
                        onRetry={() => authorId && setRecommendations([])}
                    />
                )}

                {/* 推荐列表 */}
                {!loading && !error && recommendations.length > 0 && (
                    <div className="space-y-2">
                        {recommendations.map((rec, index) => (
                            <button
                                key={rec.id}
                                onClick={() => onSelectAuthor?.(rec.id)}
                                className="w-full p-3 border rounded-lg hover:bg-accent transition-colors text-left"
                            >
                                {/* 排名 + 姓名 + 社群 */}
                                <div className="flex items-center gap-2 mb-1.5">
                                    <span className="text-xs font-mono text-muted-foreground w-6">
                                        #{index + 1}
                                    </span>
                                    <span className="font-medium text-sm">
                                        {rec.name}
                                    </span>
                                    <AuthorBadge
                                        communityId={rec.community_id}
                                        size="sm"
                                    />
                                    <Badge variant="outline" className="ml-auto text-xs">
                                        {rec.score.toFixed(4)}
                                    </Badge>
                                </div>

                                {/* 研究领域 */}
                                <div className="text-xs text-muted-foreground mb-1.5">
                                    {rec.research_area}
                                </div>

                                {/* 共同关键词 */}
                                {rec.common_keywords.length > 0 && (
                                    <div className="flex flex-wrap gap-1 mb-1.5">
                                        {rec.common_keywords.map((kw) => (
                                            <Badge
                                                key={kw}
                                                variant="secondary"
                                                className="text-xs"
                                            >
                                                {kw}
                                            </Badge>
                                        ))}
                                    </div>
                                )}

                                {/* 统计指标 */}
                                <div className="flex gap-3 text-xs text-muted-foreground">
                                    <div className="flex items-center gap-1">
                                        <Users className="h-3 w-3" />
                                        <span>{rec.degree}</span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <FileText className="h-3 w-3" />
                                        <span>{rec.paper_count}</span>
                                    </div>
                                </div>
                            </button>
                        ))}
                    </div>
                )}

                {/* 空状态 */}
                {!loading && !error && recommendations.length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-4">
                        暂无推荐结果
                    </p>
                )}
            </CardContent>
        </Card>
    );
}
