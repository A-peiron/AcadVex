/** PaperList.tsx
 * 作者论文列表组件（支持分页）。
 *
 * 功能：
 *   1. 接收 authorId，调用 /api/authors/{id}/papers
 *   2. 显示论文列表（标题、venue、ID）
 *   3. 支持分页（默认每页 20 条）
 *   4. 按 venue 分组排序（同会议的论文相邻）
 */

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import ErrorMessage from "@/components/ui/ErrorMessage";
import { FileText, ChevronLeft, ChevronRight } from "lucide-react";

interface Paper {
    id: number;
    title: string;
    venue: string;
}

interface PaperListResponse {
    total: number;
    page: number;
    page_size: number;
    papers: Paper[];
}

interface PaperListProps {
    authorId: number | null;
    pageSize?: number;
}

export function PaperList({ authorId, pageSize = 20 }: PaperListProps) {
    const [data, setData] = useState<PaperListResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [currentPage, setCurrentPage] = useState(1);

    useEffect(() => {
        if (!authorId) {
            setData(null);
            setCurrentPage(1);
            return;
        }

        const fetchPapers = async () => {
            setLoading(true);
            setError("");

            try {
                const response = await fetch(
                    `/api/authors/${authorId}/papers?page=${currentPage}&page_size=${pageSize}`
                );

                if (!response.ok) {
                    setError(
                        response.status === 404
                            ? "作者不存在"
                            : "加载失败，请稍后重试"
                    );
                    setData(null);
                    return;
                }

                const result = await response.json();
                setData(result);
            } catch {
                setError("网络错误，请检查连接");
                setData(null);
            } finally {
                setLoading(false);
            }
        };

        fetchPapers();
    }, [authorId, currentPage, pageSize]);

    // 切换页码时重置到第一页
    useEffect(() => {
        setCurrentPage(1);
    }, [authorId]);

    if (!authorId) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        论文列表
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground text-center py-4">
                        选择作者后查看论文列表
                    </p>
                </CardContent>
            </Card>
        );
    }

    const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    论文列表
                    {data && (
                        <span className="text-xs font-normal text-muted-foreground">
                            （共 {data.total} 篇）
                        </span>
                    )}
                </CardTitle>
            </CardHeader>

            <CardContent className="space-y-3">
                {/* 加载骨架 */}
                {loading && (
                    <div className="space-y-3">
                        {Array.from({ length: 5 }).map((_, i) => (
                            <div key={i} className="space-y-1.5">
                                <Skeleton className="h-4 w-full" />
                                <Skeleton className="h-3 w-24" />
                            </div>
                        ))}
                    </div>
                )}

                {/* 错误提示 */}
                {!loading && error && (
                    <ErrorMessage
                        message={error}
                        onRetry={() => authorId && setData(null)}
                    />
                )}

                {/* 论文列表 */}
                {!loading && !error && data && data.papers.length > 0 && (
                    <>
                        <div className="space-y-3">
                            {data.papers.map((paper, index) => (
                                <div
                                    key={paper.id}
                                    className="pb-3 border-b last:border-0 last:pb-0"
                                >
                                    <div className="flex items-start gap-2 mb-1">
                                        <span className="text-xs font-mono text-muted-foreground shrink-0 mt-0.5">
                                            {(currentPage - 1) * pageSize + index + 1}.
                                        </span>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm leading-relaxed">
                                                {paper.title || "未知标题"}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 ml-6">
                                        <Badge variant="outline" className="text-xs">
                                            {paper.venue || "未知会议"}
                                        </Badge>
                                        <span className="text-xs text-muted-foreground">
                                            ID: {paper.id}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* 分页控制 */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between pt-2 border-t">
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                                    disabled={currentPage === 1}
                                >
                                    <ChevronLeft className="h-4 w-4 mr-1" />
                                    上一页
                                </Button>

                                <span className="text-xs text-muted-foreground">
                                    第 {currentPage} / {totalPages} 页
                                </span>

                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() =>
                                        setCurrentPage((p) => Math.min(totalPages, p + 1))
                                    }
                                    disabled={currentPage === totalPages}
                                >
                                    下一页
                                    <ChevronRight className="h-4 w-4 ml-1" />
                                </Button>
                            </div>
                        )}
                    </>
                )}

                {/* 空状态 */}
                {!loading && !error && data && data.papers.length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-4">
                        该作者暂无论文记录
                    </p>
                )}
            </CardContent>
        </Card>
    );
}
