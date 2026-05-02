/**
 * src/components/ui/toaster.tsx
 * Toaster 全局容器 — 在 App 根组件中引入，用于显示所有 toast 通知
 */
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@/components/ui/toast"
import { useToast } from "@/hooks/use-toast"

/**
 * Toaster — 全局 Toast 容器组件
 *
 * 用法（在 App.tsx 中）：
 *   import { Toaster } from "@/components/ui/toaster"
 *
 *   function App() {
 *     return (
 *       <>
 *         <YourComponents />
 *         <Toaster />
 *       </>
 *     )
 *   }
 *
 * 在任意组件中触发 toast：
 *   import { useToast } from "@/hooks/use-toast"
 *
 *   const { toast } = useToast()
 *   toast({
 *     title: "操作成功",
 *     description: "数据已保存",
 *   })
 */
export function Toaster() {
  const { toasts } = useToast()

  return (
    <ToastProvider>
      {toasts.map(function ({ id, title, description, action, ...props }) {
        return (
          <Toast key={id} {...props}>
            <div className="grid gap-1">
              {title && <ToastTitle>{title}</ToastTitle>}
              {description && (
                <ToastDescription>{description}</ToastDescription>
              )}
            </div>
            {action}
            <ToastClose />
          </Toast>
        )
      })}
      <ToastViewport />
    </ToastProvider>
  )
}
