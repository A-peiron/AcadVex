/**
 * src/components/ui/button.tsx
 * shadcn/ui Button 组件 — 支持多种变体和尺寸
 */
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

/**
 * buttonVariants — 定义按钮的所有样式变体
 *
 * variant:
 *   default    — 实心主色背景（紫色）
 *   destructive— 红色，用于删除/危险操作
 *   outline    — 透明背景 + 边框
 *   secondary  — 次要灰色背景
 *   ghost      — 纯透明，仅 hover 显示背景
 *   link       — 文字链接样式
 *
 * size:
 *   default    — 标准高度 40px
 *   sm         — 小号 36px
 *   lg         — 大号 44px
 *   icon       — 正方形，用于图标按钮
 */
const buttonVariants = cva(
  // 基础样式：flex 布局、圆角、字体、过渡动画、禁用状态
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:     "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:     "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary:   "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost:       "hover:bg-accent hover:text-accent-foreground",
        link:        "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm:      "h-9 rounded-md px-3",
        lg:      "h-11 rounded-md px-8",
        icon:    "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size:    "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** asChild=true 时，将样式注入到子元素（如 <Link>）而非渲染 <button> */
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
