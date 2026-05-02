/** AuthorInfluence.tsx
 * 作者网络影响力指标组件。
 *
 * 功能：
 *   1. 接收 authorId，调用 /api/authors/{id}/influence
 *   2. 显示三个中心性指标：
 *      - degree_centrality（度中心性）：合作网络广度
 *      - betweenness_centrality（介数中心性）：桥梁作用
 *      - closeness_centrality（紧密中心性）：网络核心位置
 *   3. 显示定性评级（高度活跃/中度活跃/较少合作，关键桥梁/一定桥梁作用/局部连接）
 *   4. 可视化进度条展示指标值
 */

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import ErrorMessage from "@/components/ui/ErrorMessage";
import { TrendingUp, Users, FileText } from "lucide-react";

interface InfluenceData {
    author_id: number;
    name: string;
    degree_centrality: number;
    betweenness_centrality: number;
    closeness_centrality: number;
    degree: number;
    paper_count: number;
    activity_level: string;
    bridge_role: string;
}

interface AuthorInfluenceProps {
    authorId: number | null;
}

export function AuthorInfluence({ authorId }: AuthorInfluenceProps) {
    const [data, setData] = useState<InfluenceData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!authorId) {
            setData(null);
            return;
        }

        const fetchInfluence = async () => {
            setLoading(true);
            setError("");

            try {
                const response = await fetch(`/api/authors/${authorId}/influence`);

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

        fetchInfluence();
    }, [authorId]);

    if (!authorId) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" />
                        网络影响力
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground text-center py-4">
                        选择作者后查看影响力指标
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    网络影响力
                </CardTitle>
            </CardHeader>

            <CardContent className="space-y-4">
                {/* 加载骨架 */}
                {loading && (
                    <div className="space-y-3">
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-full" />
                        <div className="flex gap-2">
                            <Skeleton className="h-6 w-20 rounded-full" />
                            <Skeleton className="h-6 w-24 rounded-full" />
                        </div>
                    </div>
                )}

                {/* 错误提示 */}
                {!loading && error && (
                    <ErrorMessage
                        message={error}
                        onRetry={() => authorId && setData(null)}
                    />
                )}

                {/* 影响力指标 */}
                {!loading && !error && data && (
                    <>
                        {/* 作者基本信息 */}
                        <div className="pb-3 border-b">
                            <div className="font-medium text-sm mb-2">{data.name}</div>
                            <div className="flex gap-3 text-xs text-muted-foreground">
                                <div className="flex items-center gap-1">
                                    <Users className="h-3 w-3" />
                                    <span>{data.degree} 位合作者</span>
                                </div>
                                <div className="flex items-center gap-1">
                                    <FileText className="h-3 w-3" />
                                    <span>{data.paper_count} 篇论文</span>
                                </div>
                            </div>
                        </div>

                        {/* 中心性指标 */}
                        <div className="space-y-3">
                            {/* 度中心性 */}
                            <div>
                                <div className="flex items-center justify-between mb-1.5">
                                    <span className="text-sm font-medium">度中心性</span>
                                    <span className="text-xs text-muted-foreground">
                                        {data.degree_centrality.toFixed(6)}
                                    </span>
                                </div>
                                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-blue-500 transition-all"
                                        style={{
                                            width: `${Math.min(
                                                100,
                                                data.degree_centrality * 5000
                                            )}%`,
                                        }}
                                    />
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                    合作网络广度 → {data.activity_level}
                                </p>
                            </div>

                            {/* 介数中心性 */}
                            <div>
                                <div className="flex items-center justify-between mb-1.5">
                                    <span className="text-sm font-medium">介数中心性</span>
                                    <span className="text-xs text-muted-foreground">
                                        {data.betweenness_centrality.toFixed(6)}
                                    </span>
                                </div>
                                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-green-500 transition-all"
                                        style={{
                                            width: `${Math.min(
                                                100,
                                                data.betweenness_centrality * 2000
                                            )}%`,
                                        }}
                                    />
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                    桥梁作用 → {data.bridge_role}
                                </p>
                            </div>

                            {/* 紧密中心性 */}
                            <div>
                                <div className="flex items-center justify-between mb-1.5">
                                    <span className="text-sm font-medium">紧密中心性</span>
                                    <span className="text-xs text-muted-foreground">
                                        {data.closeness_centrality.toFixed(6)}
                                    </span>
                                </div>
                                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-purple-500 transition-all"
                                        style={{
                                            width: `${Math.min(
                                                100,
                                                data.closeness_centrality * 200
                                            )}%`,
                                        }}
                                    />
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                    网络核心位置（值越高越核心）
                                </p>
                            </div>
                        </div>

                        {/* 综合评级 */}
                        <div className="flex gap-2 pt-2 border-t">
                            <Badge variant="secondary">{data.activity_level}</Badge>
                            <Badge variant="outline">{data.bridge_role}</Badge>
                        </div>
                    </>
                )}
            </CardContent>
        </Card>
    );
}
