/** AuthorBadge.tsx
 * 展示作者所属社群的颜色标签组件。
 *
 * AcadVex DBLP 数据集有 4 个社群（Louvain 划分）：
 *   0 → Database（蓝）
 *   1 → Data Mining（绿）
 *   2 → AI（紫）
 *   3 → Information Retrieval（橙）
 *
 * 超出范围的 community_id 显示为灰色 Unknown。
 */

import { cn } from "@/lib/utils";

interface AuthorBadgeProps {
    communityId: number | null | undefined;
    /** 是否显示社群 ID 数字 */
    showId?: boolean;
    /** 尺寸大小 */
    size?: "sm" | "md";
    className?: string;
}

const COMMUNITY_CONFIG: Record<number, { label: string; classes: string }> = {
    0: {
        label: "Database",
        classes: "bg-blue-100 text-blue-800 border-blue-200",
    },
    1: {
        label: "Data Mining",
        classes: "bg-green-100 text-green-800 border-green-200",
    },
    2: {
        label: "AI",
        classes: "bg-purple-100 text-purple-800 border-purple-200",
    },
    3: {
        label: "Info Retrieval",
        classes: "bg-orange-100 text-orange-800 border-orange-200",
    },
};

const UNKNOWN_CONFIG = {
    label: "Unknown",
    classes: "bg-gray-100 text-gray-600 border-gray-200",
};

export default function AuthorBadge({
    communityId,
    showId = false,
    size = "md",
    className,
}: AuthorBadgeProps) {
    const id = communityId ?? -1;
    const config = COMMUNITY_CONFIG[id] ?? UNKNOWN_CONFIG;

    const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-0.5 text-xs";

    return (
        <span
            className={cn(
                "inline-flex items-center rounded-full border font-semibold transition-colors",
                config.classes,
                sizeClasses,
                className
            )}
        >
            {config.label}
            {showId && id >= 0 && (
                <span className="ml-1 opacity-60">#{id}</span>
            )}
        </span>
    );
}

/** 导出颜色配置，供 NetworkGraph 节点着色使用 */
export const COMMUNITY_COLORS: Record<number, string> = {
    0: "#3b82f6", // blue-500
    1: "#22c55e", // green-500
    2: "#a855f7", // purple-500
    3: "#f97316", // orange-500
};
