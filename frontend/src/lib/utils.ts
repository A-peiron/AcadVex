/**
 * src/lib/utils.ts
 * shadcn/ui 工具函数：合并 Tailwind class 名称，处理条件样式冲突
 */
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * cn() — 合并多个 className，并用 tailwind-merge 解决冲突
 *
 * 用法：
 *   cn("px-2 py-1", isActive && "bg-primary", className)
 *   → 合并后的 class 字符串，冲突规则以最后出现为准
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
