/**
 * src/components/ui/input.tsx
 * shadcn/ui Input 组件 — 文本输入框
 */
import * as React from "react"
import { cn } from "@/lib/utils"

/**
 * Input — 标准文本输入框
 *
 * 样式特点：
 *   - 圆角边框、内边距
 *   - focus 时显示 ring（焦点环）
 *   - disabled 时降低透明度、禁用光标
 *   - 支持所有原生 <input> 属性（type, placeholder, value, onChange 等）
 *
 * 用法：
 *   <Input type="text" placeholder="请输入作者姓名" />
 *   <Input type="email" disabled />
 */
export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
