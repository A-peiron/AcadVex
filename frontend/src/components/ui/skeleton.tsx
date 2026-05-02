/**
 * src/components/ui/skeleton.tsx
 * shadcn/ui Skeleton 组件 — 加载占位符（骨架屏）
 */
import { cn } from "@/lib/utils"

/**
 * Skeleton — 骨架屏占位符
 *
 * 用于数据加载时显示灰色动画占位块，提升用户体验。
 *
 * 用法：
 *   <Skeleton className="h-12 w-12 rounded-full" />  // 圆形头像占位
 *   <Skeleton className="h-4 w-[250px]" />           // 文本行占位
 *   <Skeleton className="h-32 w-full" />             // 卡片占位
 *
 * 动画原理：
 *   animate-pulse — Tailwind 内置动画，opacity 在 0.5~1 之间循环
 */
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  )
}

export { Skeleton }
