/** AuthorCard.tsx
 * 作者信息卡片（shadcn/ui Card + Badge + Skeleton 重构版）。
 *
 * 功能：
 *   1. 接收外部传入的 externalAuthorId（点击 NetworkGraph 节点或搜索框选择时自动触发）
 *   2. 展示：姓名、社群 Badge、研究领域、关键词列表、度数、论文数
 *   3. 加载中显示 Skeleton；出错显示 ErrorMessage
 */

import { useState, useEffect } from "react";
import {
    Card,
    CardHeader,
    CardTitle,
    CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import AuthorBadge from "@/components/ui/AuthorBadge";
import ErrorMessage from "@/components/ui/ErrorMessage";
import { Users, FileText } from "lucide-react";

interface AuthorInfo {
    id: number;
    name: string;
    community_id: number;
    research_area: string;
    keywords: string[];
    degree: number;
    paper_count: number;
}

interface AuthorCardProps {
    externalAuthorId?: number | null;
}

export function AuthorCard({ externalAuthorId }: AuthorCardProps) {
    const [authorInfo, setAuthorInfo] = useState<AuthorInfo | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const fetchAuthor = async (id: number) => {
        setLoading(true);
        setError("");
        setAuthorInfo(null);

        try {
            const response = await fetch(`/api/authors/${id}`);

            if (!response.ok) {
                setError(
                    response.status === 404
                        ? `作者 ID ${id} 不存在`
                        : "查询失败，请稍后重试"
                );
                return;
            }

            const data = await response.json();
            setAuthorInfo(data);
        } catch {
            setError("网络错误，请检查连接");
        } finally {
            setLoading(false);
        }
    };

    // 外部 ID 变化时自动查询（点击 NetworkGraph 节点或搜索框选择触发）
    useEffect(() => {
        if (externalAuthorId !== null && externalAuthorId !== undefined) {
            fetchAuthor(externalAuthorId);
        }
    }, [externalAuthorId]);

    return (
        <Card className="rounded-lg">
            {/* ── 标题栏 ── */}
            <CardHeader className="pb-3">
                <CardTitle className="text-base">作者详情</CardTitle>
            </CardHeader>

            {/* ── 内容区 ── */}
            <CardContent className="space-y-4">
                {/* 加载骨架 */}
                {loading && (
                    <div className="space-y-3">
                        <div className="flex items-center gap-3">
                            <Skeleton className="h-5 w-32" />
                            <Skeleton className="h-5 w-20 rounded-full" />
                        </div>
                        <Skeleton className="h-4 w-48" />
                        <div className="flex flex-wrap gap-1.5">
                            {Array.from({ length: 5 }).map((_, i) => (
                                <Skeleton key={i} className="h-5 w-16 rounded-full" />
                            ))}
                        </div>
                        <div className="flex gap-4">
                            <Skeleton className="h-4 w-20" />
                            <Skeleton className="h-4 w-20" />
                        </div>
                    </div>
                )}

                {/* 错误提示 */}
                {!loading && error && (
                    <ErrorMessage
                        message={error}
                        onRetry={() => externalAuthorId && fetchAuthor(externalAuthorId)}
                    />
                )}

                {/* 作者信息 */}
                {!loading && authorInfo && (
                    <div className="space-y-3">
                        {/* 姓名 + 社群 */}
                        <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="text-base font-semibold leading-none">
                                {authorInfo.name}
                            </h3>
                            <AuthorBadge
                                communityId={authorInfo.community_id}
                                showId
                            />
                            <span className="text-xs text-muted-foreground">
                                ID: {authorInfo.id}
                            </span>
                        </div>

                        {/* 研究领域 */}
                        <div className="text-sm text-muted-foreground">
                            <span className="font-medium text-foreground">研究领域：</span>
                            {authorInfo.research_area}
                        </div>

                        {/* 关键词 */}
                        {authorInfo.keywords.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                                {authorInfo.keywords.map((kw) => (
                                    <Badge key={kw} variant="secondary" className="text-xs">
                                        {kw}
                                    </Badge>
                                ))}
                            </div>
                        )}

                        {/* 统计指标 */}
                        <div className="flex gap-4 text-sm text-muted-foreground">
                            <div className="flex items-center gap-1">
                                <Users className="h-3.5 w-3.5" />
                                <span>{authorInfo.degree} 位合作者</span>
                            </div>
                            <div className="flex items-center gap-1">
                                <FileText className="h-3.5 w-3.5" />
                                <span>{authorInfo.paper_count} 篇论文</span>
                            </div>
                        </div>
                    </div>
                )}

                {/* 空状态 */}
                {!loading && !error && !authorInfo && (
                    <p className="text-sm text-muted-foreground text-center py-4">
                        点击网络图节点或使用搜索框查看作者详情
                    </p>
                )}
            </CardContent>
        </Card>
    );
}
