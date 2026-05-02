/**
 * ForceGraphVisualization.tsx
 * ---------------------------
 * 基于 react-force-graph（WebGL/Canvas 2D）的学术合作网络可视化组件。
 * - 启动时自动加载全图概览（最多 300 节点）
 * - 社群着色（4 种颜色）
 * - 节点大小映射到 degree
 * - 边粗细映射到合作权重
 * - 点击节点触发 onNodeClick 回调
 * - Hover tooltip
 * - 社群过滤按钮
 */

import { useState, useRef, useCallback, useEffect } from "react";
import { ForceGraph2D } from "react-force-graph";
import { forceCollide } from "d3-force";

// ── 类型定义 ────────────────────────────────────────────────────────────────

interface FgNode {
    id: number;
    name: string;
    community_id: number;
    research_area: string;
    paper_count: number;
    degree: number;
    x?: number;
    y?: number;
    fx?: number;
    fy?: number;
    hopDistance?: number;  // 距离中心作者的跳数（0=中心，1=直接邻居，2=二度邻居）
}

interface FgLink {
    source: number | FgNode;
    target: number | FgNode;
    value: number;
}

interface GraphData {
    nodes: FgNode[];
    links: FgLink[];
}

interface RawNode {
    id: number;
    name: string;
    community_id: number;
    research_area: string;
    paper_count: number;
    degree: number;
    symbolSize?: number;
    itemStyle?: { color: string };
    label?: unknown;
}

interface RawLink {
    source: number;
    target: number;
    value: number;
    lineStyle?: unknown;
}

interface RawGraphData {
    nodes: RawNode[];
    links: RawLink[];
}

interface ForceGraphVisualizationProps {
    onNodeClick?: (authorId: number) => void;
    selectedAuthorId?: number | null;  // 外部选中的作者 ID（搜索或推荐点击）
}

// ── 常量 ─────────────────────────────────────────────────────────────────────

const COMMUNITY_COLORS: Record<number, string> = {
    0: "#5470c6",
    1: "#91cc75",
    2: "#fac858",
    3: "#ee6666",
};

const COMMUNITY_NAMES: Record<number, string> = {
    0: "Database",
    1: "Data Mining",
    2: "AI",
    3: "Info Retrieval",
};

const NODE_BASE_R = 3;
const NODE_MAX_R = 14;

// ── 工具函数 ──────────────────────────────────────────────────────────────────

function degreeToRadius(degree: number, maxDegree: number): number {
    if (maxDegree === 0) return NODE_BASE_R;
    const ratio = Math.sqrt(degree / maxDegree);
    return NODE_BASE_R + ratio * (NODE_MAX_R - NODE_BASE_R);
}

function normalizeGraphData(raw: RawGraphData): GraphData {
    return {
        nodes: raw.nodes.map((n) => ({
            id: n.id,
            name: n.name,
            community_id: n.community_id,
            research_area: n.research_area,
            paper_count: n.paper_count,
            degree: n.degree ?? 0,
        })),
        links: raw.links.map((l) => ({
            source: l.source,
            target: l.target,
            value: l.value,
        })),
    };
}

// ── 组件 ─────────────────────────────────────────────────────────────────────

export function ForceGraphVisualization({ onNodeClick, selectedAuthorId }: ForceGraphVisualizationProps) {
    const [graphData, setGraphData] = useState<GraphData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [highlightCommunity, setHighlightCommunity] = useState<number | null>(null);
    const [hoveredNode, setHoveredNode] = useState<FgNode | null>(null);
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
    const [pinnedNodes, setPinnedNodes] = useState<Set<number>>(new Set());  // 固定的节点 ID

    const containerRef = useRef<HTMLDivElement>(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const graphRef = useRef<any>(null);

    // ── 响应式尺寸 ──────────────────────────────────────────────────────────
    useEffect(() => {
        const obs = new ResizeObserver((entries) => {
            for (const entry of entries) {
                const { width, height } = entry.contentRect;
                setDimensions({
                    width: Math.floor(width),
                    height: Math.max(Math.floor(height), 300),
                });
            }
        });
        if (containerRef.current) obs.observe(containerRef.current);
        return () => obs.disconnect();
    }, []);

    // ── 自动加载全图概览 ────────────────────────────────────────────────────
    useEffect(() => {
        const loadOverview = async () => {
            setLoading(true);
            setError("");
            try {
                // 加载全图（所有节点和边）
                const resp = await fetch("/api/graph/full");
                if (!resp.ok) throw new Error("fetch failed");
                const raw: RawGraphData = await resp.json();
                setGraphData(normalizeGraphData(raw));
            } catch {
                setError("网络图加载失败，请刷新重试");
            } finally {
                setLoading(false);
            }
        };
        loadOverview();
    }, []);

    // ── 双击节点时，加载该节点的 ego-network ──────────────────────────
    const loadEgoNetwork = useCallback(async (authorId: number) => {
        setLoading(true);
        setError("");
        try {
            // 加载 2-hop ego-network（最多 150 节点）
            const resp = await fetch(`/api/graph/ego?author_id=${authorId}&hops=2&max_nodes=150`);
            if (!resp.ok) {
                if (resp.status === 404) {
                    setError(`作者 ID ${authorId} 不存在`);
                } else {
                    throw new Error("fetch failed");
                }
                return;
            }
            const raw: RawGraphData = await resp.json();
            const normalized = normalizeGraphData(raw);

            // 计算每个节点的跳数（BFS）
            const hopDistances = new Map<number, number>();
            hopDistances.set(authorId, 0);

            // 构建邻接表
            const adj = new Map<number, Set<number>>();
            for (const link of normalized.links) {
                const src = typeof link.source === 'number' ? link.source : link.source.id;
                const tgt = typeof link.target === 'number' ? link.target : link.target.id;
                if (!adj.has(src)) adj.set(src, new Set());
                if (!adj.has(tgt)) adj.set(tgt, new Set());
                adj.get(src)!.add(tgt);
                adj.get(tgt)!.add(src);
            }

            // BFS 计算跳数
            const queue: number[] = [authorId];
            while (queue.length > 0) {
                const node = queue.shift()!;
                const dist = hopDistances.get(node)!;
                for (const neighbor of adj.get(node) || []) {
                    if (!hopDistances.has(neighbor)) {
                        hopDistances.set(neighbor, dist + 1);
                        queue.push(neighbor);
                    }
                }
            }

            // 将跳数注入节点
            for (const node of normalized.nodes) {
                node.hopDistance = hopDistances.get(node.id) ?? 2;
            }

            setGraphData(normalized);
        } catch {
            setError("加载作者网络失败");
        } finally {
            setLoading(false);
        }
    }, []);

    // ── 当外部选中作者时（搜索），加载该作者的 ego-network ──────────────────
    useEffect(() => {
        if (selectedAuthorId === null || selectedAuthorId === undefined) return;
        loadEgoNetwork(selectedAuthorId);
    }, [selectedAuthorId, loadEgoNetwork]);

    // ── 自定义力模拟参数（让图散开，避免花朵形）──────────────────────────
    const handleEngineStop = useCallback(() => {
        // 仿真结束后自动 fit 视图
        graphRef.current?.zoomToFit(400, 40);
    }, []);

    // 配置 d3-force 参数
    useEffect(() => {
        const fg = graphRef.current;
        if (!fg || !graphData) return;

        // 调整 d3-force 参数
        // 增大斥力，让节点充分分散；缩短 link distance 让社群内部聚集
        fg.d3Force("charge")?.strength(-120).distanceMax(300);
        fg.d3Force("link")?.distance((link: FgLink) => {
            // 同社群节点距离短，跨社群距离长
            const src = link.source as FgNode;
            const tgt = link.target as FgNode;
            if (src?.community_id !== undefined && tgt?.community_id !== undefined) {
                return src.community_id === tgt.community_id ? 40 : 120;
            }
            return 80;
        });
        // 添加社群聚类力（同社群节点向各自质心靠拢）
        fg.d3Force("cluster", clusterForce(0.15));
        fg.d3Force("collision", forceCollide<FgNode>().radius((n: FgNode) =>
            degreeToRadius(n.degree, 50) + 2
        ).strength(0.8));
    }, [graphData]);

    // 最大 degree
    const maxDegree = graphData
        ? Math.max(...graphData.nodes.map((n) => n.degree), 1)
        : 1;

    // ── 节点颜色（带社群过滤透明效果 + 跳数透明度）───────────────────────────
    const getNodeColor = useCallback(
        (node: FgNode) => {
            const base = COMMUNITY_COLORS[node.community_id] ?? "#999";

            // 社群过滤：非高亮社群降低透明度
            if (highlightCommunity !== null && node.community_id !== highlightCommunity) {
                return base + "30";  // ~19% 不透明
            }

            // 跳数透明度（仅在 ego-network 模式下生效）
            if (node.hopDistance !== undefined) {
                const alphaMap: Record<number, string> = {
                    0: "FF",  // 100% - 中心作者
                    1: "CC",  // 80% - 1-hop 邻居
                    2: "99",  // 60% - 2-hop 邻居
                };
                return base + (alphaMap[node.hopDistance] ?? "99");
            }

            return base;  // 全图模式：完全不透明
        },
        [highlightCommunity]
    );

    // ── 节点绘制 ───────────────────────────────────────────────────────────
    const paintNode = useCallback(
        (node: FgNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const r = degreeToRadius(node.degree, maxDegree);
            const color = getNodeColor(node);
            const isHovered = hoveredNode?.id === node.id;
            const isPinned = pinnedNodes.has(node.id);

            ctx.beginPath();
            ctx.arc(node.x!, node.y!, r, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();

            if (isHovered) {
                ctx.strokeStyle = "#ffffff";
                ctx.lineWidth = 2 / globalScale;
                ctx.stroke();
            }

            // 固定节点显示图钉标识
            if (isPinned) {
                ctx.strokeStyle = "#ff6b6b";
                ctx.lineWidth = 2.5 / globalScale;
                ctx.stroke();
            }

            // 仅在 zoom 较大或 hover 时显示标签
            if (globalScale > 2.5 || isHovered) {
                const fontSize = Math.max(10 / globalScale, 2.5);
                ctx.font = `${isHovered ? "bold " : ""}${fontSize}px Sans-Serif`;
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillStyle = "#333";
                ctx.fillText(node.name, node.x!, node.y! + r + fontSize * 0.8);
            }
        },
        [maxDegree, getNodeColor, hoveredNode, pinnedNodes]
    );

    // ── 边样式 ─────────────────────────────────────────────────────────────
    const getLinkWidth = useCallback(
        (link: FgLink) => {
            const w = Math.min(0.5 + link.value * 0.3, 3);
            if (highlightCommunity !== null) {
                const src = link.source as FgNode;
                const tgt = link.target as FgNode;
                if (
                    src?.community_id !== undefined &&
                    tgt?.community_id !== undefined &&
                    src.community_id !== highlightCommunity &&
                    tgt.community_id !== highlightCommunity
                ) {
                    return 0.15;
                }
            }
            return w;
        },
        [highlightCommunity]
    );

    const getLinkColor = useCallback(
        (link: FgLink) => {
            if (highlightCommunity !== null) {
                const src = link.source as FgNode;
                const tgt = link.target as FgNode;
                if (
                    src?.community_id !== undefined &&
                    tgt?.community_id !== undefined &&
                    (src.community_id === highlightCommunity || tgt.community_id === highlightCommunity)
                ) {
                    return "rgba(100,100,100,0.6)";
                }
                return "rgba(180,180,180,0.1)";
            }
            return "rgba(150,150,150,0.3)";
        },
        [highlightCommunity]
    );

    const getNodePointerArea = useCallback(
        (node: FgNode) => degreeToRadius(node.degree, maxDegree) + 3,
        [maxDegree]
    );

    const communityIds = graphData
        ? [...new Set(graphData.nodes.map((n) => n.community_id))].sort()
        : [];

    // ── 渲染 ──────────────────────────────────────────────────────────────
    return (
        <div className="relative w-full h-full flex flex-col bg-background">
            {/* 统计 + 社群过滤（顶部工具条） */}
            {graphData && (
                <div className="absolute bottom-3 left-3 z-10 flex flex-wrap gap-2 items-center bg-background/80 backdrop-blur-sm px-3 py-1.5 rounded-lg border text-xs text-muted-foreground">
                    <span>节点 {graphData.nodes.length} · 边 {graphData.links.length}</span>
                    <span className="text-border">|</span>
                    {communityIds.map((cid) => {
                        const active = highlightCommunity === cid;
                        return (
                            <button
                                key={cid}
                                onClick={() => setHighlightCommunity(active ? null : cid)}
                                className="px-2 py-0.5 rounded-full border text-xs font-semibold transition-all"
                                style={{
                                    borderColor: COMMUNITY_COLORS[cid] ?? "#999",
                                    backgroundColor: active ? (COMMUNITY_COLORS[cid] ?? "#999") : "transparent",
                                    color: active ? "white" : (COMMUNITY_COLORS[cid] ?? "#999"),
                                }}
                            >
                                {COMMUNITY_NAMES[cid] ?? `社群${cid}`}
                            </button>
                        );
                    })}
                    {/* 图例 */}
                    <span className="text-border">|</span>
                    <span className="text-muted-foreground">节点大小 = 合作者数</span>
                </div>
            )}

            {/* Hover tooltip */}
            {hoveredNode && (
                <div
                    className="fixed pointer-events-none z-50 bg-popover text-popover-foreground border rounded-lg shadow-lg p-2 text-xs leading-relaxed"
                    style={{
                        top: mousePos.y,
                        left: mousePos.x,
                        transform: "translate(14px, -50%)",
                        maxWidth: "200px",
                    }}
                >
                    <div className="font-semibold">{hoveredNode.name}</div>
                    <div className="text-muted-foreground">
                        {COMMUNITY_NAMES[hoveredNode.community_id] ?? `社群${hoveredNode.community_id}`}
                    </div>
                    <div>{hoveredNode.research_area}</div>
                    <div>{hoveredNode.paper_count} 篇论文 · {hoveredNode.degree} 合作者</div>
                </div>
            )}

            {/* 图形区域 */}
            <div
                ref={containerRef}
                className="flex-1 w-full overflow-hidden"
                onMouseMove={(e) => setMousePos({ x: e.clientX, y: e.clientY })}
            >
                {graphData ? (
                    <ForceGraph2D<FgNode, FgLink>
                        ref={graphRef}
                        graphData={graphData}
                        width={dimensions.width}
                        height={dimensions.height}
                        nodeId="id"
                        nodeVal={(n) => degreeToRadius(n.degree, maxDegree) ** 2}
                        nodeColor={getNodeColor}
                        nodeCanvasObject={paintNode}
                        nodePointerAreaPaint={(node, color, ctx) => {
                            const r = getNodePointerArea(node);
                            ctx.beginPath();
                            ctx.arc(node.x!, node.y!, r, 0, 2 * Math.PI);
                            ctx.fillStyle = color;
                            ctx.fill();
                        }}
                        linkSource="source"
                        linkTarget="target"
                        linkWidth={getLinkWidth}
                        linkColor={getLinkColor}
                        onNodeClick={(node) => onNodeClick?.(node.id)}
                        onNodeDragEnd={(node) => {
                            // 拖拽结束后固定节点位置
                            node.fx = node.x;
                            node.fy = node.y;
                            setPinnedNodes((prev) => new Set(prev).add(node.id));
                        }}
                        onNodeRightClick={(node, event) => {
                            event.preventDefault();
                            // 右键点击：切换固定状态
                            if (pinnedNodes.has(node.id)) {
                                node.fx = undefined;
                                node.fy = undefined;
                                setPinnedNodes((prev) => {
                                    const next = new Set(prev);
                                    next.delete(node.id);
                                    return next;
                                });
                            } else {
                                node.fx = node.x;
                                node.fy = node.y;
                                setPinnedNodes((prev) => new Set(prev).add(node.id));
                            }
                        }}
                        onNodeHover={(node) => {
                            setHoveredNode(node ?? null);
                            document.body.style.cursor = node ? "pointer" : "default";
                        }}
                        onEngineStop={handleEngineStop}
                        // 物理仿真：慢冷却让布局更充分
                        d3AlphaDecay={0.01}
                        d3VelocityDecay={0.25}
                        cooldownTicks={200}
                        enableNodeDrag={true}
                        enableZoomInteraction={true}
                        backgroundColor="transparent"
                    />
                ) : loading ? (
                    <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm gap-2">
                        <span className="inline-block w-5 h-5 border-2 border-border border-t-primary rounded-full animate-spin" />
                        加载中…
                    </div>
                ) : error ? (
                    <div className="absolute inset-0 flex items-center justify-center text-destructive text-sm">
                        {error}
                    </div>
                ) : null}
            </div>
        </div>
    );
}

// ── 社群聚类力 ────────────────────────────────────────────────────────────────

/**
 * 自定义 d3-force：让同社群节点向各自质心靠拢，产生 4 个社群簇
 * strength: 0~1，越大聚集越紧
 */
function clusterForce(strength: number) {
    // 4 个社群质心（初始四角分布，仿真过程中动态更新）
    const centroids: Record<number, { x: number; y: number }> = {
        0: { x: -200, y: -200 },
        1: { x:  200, y: -200 },
        2: { x: -200, y:  200 },
        3: { x:  200, y:  200 },
    };

    function force(alpha: number) {
        // 更新各社群质心
        const counts: Record<number, number> = {};
        const sums: Record<number, { x: number; y: number }> = {};

        for (const n of (force as any).nodes as FgNode[]) {
            const c = n.community_id;
            if (!sums[c]) { sums[c] = { x: 0, y: 0 }; counts[c] = 0; }
            sums[c].x += n.x ?? 0;
            sums[c].y += n.y ?? 0;
            counts[c]++;
        }
        for (const c in sums) {
            centroids[Number(c)] = {
                x: sums[c].x / counts[c],
                y: sums[c].y / counts[c],
            };
        }

        // 将每个节点向其社群质心拉近
        for (const n of (force as any).nodes as FgNode[]) {
            const c = centroids[n.community_id];
            if (!c) continue;
            const dx = c.x - (n.x ?? 0);
            const dy = c.y - (n.y ?? 0);
            (n as any).vx = ((n as any).vx ?? 0) + dx * strength * alpha;
            (n as any).vy = ((n as any).vy ?? 0) + dy * strength * alpha;
        }
    }

    force.initialize = (nodes: FgNode[]) => {
        (force as any).nodes = nodes;
    };

    return force;
}
