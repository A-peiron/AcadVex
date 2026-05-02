/**
 * src/components/ui/badge.tsx
 * shadcn/ui Badge 组件 — 标签徽章
 */
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

/**
 * badgeVariants — 定义徽章的样式变体
 *
 * variant:
 *   default     — 实心主色背景（紫色）
 *   secondary   — 灰色背景
 *   destructive — 红色背景
 *   outline     — 透明背景 + 边框
 *
 * 用法：
 *   <Badge>默认</Badge>
 *   <Badge variant="secondary">社群标签</Badge>
 *   <Badge variant="outline">轮廓</Badge>
 */
const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
