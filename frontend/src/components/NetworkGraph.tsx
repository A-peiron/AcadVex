import { useState, useRef } from "react";
import ReactECharts from "echarts-for-react";

interface GraphNode {
    id: number;
    name: string;
    symbolSize: number;
    itemStyle: { color: string };
    label: { show: boolean; fontSize?: number; fontWeight?: string };
    community_id: number;
    research_area: string;
    paper_count: number;
    degree: number;
}

interface GraphLink {
    source: number;
    target: number;
    value: number;
    lineStyle: { width: number };
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

interface NetworkGraphProps {
    onNodeClick?: (authorId: number) => void;
}

// 社群配色（与后端保持一致）
const COMMUNITY_COLORS: Record<number, string> = {
    0: "#5470c6",
    1: "#91cc75",
    2: "#fac858",
    3: "#ee6666",
};

export function NetworkGraph({ onNodeClick }: NetworkGraphProps) {
    const [authorId, setAuthorId] = useState("");
    const [graphData, setGraphData] = useState<GraphData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [highlightCommunity, setHighlightCommunity] = useState<number | null>(null);

    const echartsRef = useRef<ReactECharts>(null);

    const fetchGraph = async () => {
        if (!authorId.trim()) return;

        setLoading(true);
        setError("");
        setGraphData(null);
        setHighlightCommunity(null);

        try {
            const response = await fetch(`/api/graph?author_id=${authorId}&max_nodes=50`);

            if (!response.ok) {
                if (response.status === 404) {
                    setError(`作者 ID ${authorId} 不存在`);
                } else {
                    setError("查询失败，请稍后重试");
                }
                return;
            }

            const data = await response.json();
            setGraphData(data);
        } catch (err) {
            setError("网络错误，请检查连接");
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter") fetchGraph();
    };

    // 社群高亮：通过 React 状态驱动，修改节点数据后重新渲染
    const handleHighlightCommunity = (communityId: number) => {
        const nextCommunity = highlightCommunity === communityId ? null : communityId;
        setHighlightCommunity(nextCommunity);
    };

    // ECharts 配置
    const getOption = () => {
        if (!graphData) return {};

        return {
            title: {
                text: "学术合作网络",
                left: "center",
                top: 10,
            },
            tooltip: {
                formatter: (params: any) => {
                    if (params.dataType === "node") {
                        const node = params.data;
                        return `
                            <strong>${node.name}</strong><br/>
                            ID: ${node.id}<br/>
                            研究领域: ${node.research_area}<br/>
                            社群: ${node.community_id}<br/>
                            论文数: ${node.paper_count}<br/>
                            合作者数: ${node.degree}
                        `;
                    } else if (params.dataType === "edge") {
                        return `合作强度: ${params.data.value}`;
                    }
                    return "";
                },
            },
            series: [
                {
                    type: "graph",
                    layout: "force",
                    data: graphData.nodes.map(node => ({
                        ...node,
                        id: String(node.id),
                        itemStyle: {
                            color: COMMUNITY_COLORS[node.community_id] ?? "#999",
                            opacity: highlightCommunity === null || node.community_id === highlightCommunity ? 1 : 0.2,
                        },
                    })),
                    links: graphData.links.map(link => ({
                        ...link,
                        source: String(link.source),
                        target: String(link.target),
                    })),
                    roam: true,
                    label: {
                        show: true,
                        position: "right",
                        formatter: "{b}",
                    },
                    force: {
                        repulsion: 200,
                        gravity: 0.1,
                        edgeLength: 100,
                        layoutAnimation: true,
                    },
                    emphasis: {
                        focus: "adjacency",
                        lineStyle: { width: 5 },
                    },
                },
            ],
        };
    };

    // ECharts 事件回调对象
    const onEvents = {
        click: (params: any) => {
            if (params.dataType === "node") {
                const nodeId = Number(params.data.id);
                onNodeClick?.(nodeId);
            }
        },
    };

    // 提取图中出现的所有社群 ID（用于渲染高亮按钮）
    const communityIds = graphData
        ? [...new Set(graphData.nodes.map(n => n.community_id))].sort()
        : [];

    const communityNames: Record<number, string> = {
        0: "Database",
        1: "Data Mining",
        2: "AI",
        3: "Info Retrieval",
    };

    return (
        <div style={{ padding: "20px", border: "1px solid #ddd", borderRadius: "8px" }}>
            <h2>合作网络可视化</h2>

            <div style={{ marginBottom: "20px" }}>
                <input
                    type="text"
                    value={authorId}
                    onChange={(e) => setAuthorId(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="输入作者 ID（如 42）"
                    style={{
                        padding: "8px",
                        width: "200px",
                        marginRight: "10px",
                        border: "1px solid #ccc",
                        borderRadius: "4px",
                    }}
                />
                <button
                    onClick={fetchGraph}
                    disabled={loading || !authorId.trim()}
                    style={{
                        padding: "8px 16px",
                        backgroundColor: loading ? "#ccc" : "#007bff",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: loading ? "not-allowed" : "pointer",
                    }}
                >
                    {loading ? "加载中..." : "查询"}
                </button>
            </div>

            {error && (
                <div style={{ color: "red", marginBottom: "10px" }}>{error}</div>
            )}

            {graphData && (
                <div>
                    <div style={{ marginBottom: "10px", display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        <span style={{ color: "#666", fontSize: "13px" }}>
                            节点: {graphData.nodes.length} | 边: {graphData.links.length}
                        </span>
                        <span style={{ color: "#999", fontSize: "13px" }}>| 社群高亮：</span>
                        {communityIds.map(cid => (
                            <button
                                key={cid}
                                onClick={() => handleHighlightCommunity(cid)}
                                style={{
                                    padding: "3px 10px",
                                    borderRadius: "12px",
                                    border: `2px solid ${COMMUNITY_COLORS[cid] ?? "#999"}`,
                                    backgroundColor: highlightCommunity === cid ? COMMUNITY_COLORS[cid] : "white",
                                    color: highlightCommunity === cid ? "white" : COMMUNITY_COLORS[cid],
                                    cursor: "pointer",
                                    fontSize: "12px",
                                    fontWeight: "bold",
                                }}
                            >
                                {communityNames[cid] ?? `社群 ${cid}`}
                            </button>
                        ))}
                    </div>
                    <ReactECharts
                        ref={echartsRef}
                        option={getOption()}
                        onEvents={onEvents}
                        notMerge={false}
                        lazyUpdate={true}
                        style={{ height: "600px", width: "100%" }}
                        opts={{ renderer: "canvas" }}
                    />
                </div>
            )}

            {!graphData && !loading && !error && (
                <div style={{ color: "#999", textAlign: "center", padding: "40px" }}>
                    输入作者 ID 查看其合作网络
                </div>
            )}
        </div>
    );
}
