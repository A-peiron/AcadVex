/** ErrorMessage.tsx
 * 通用错误提示组件。
 * 支持 title + message 两级文案，以及可选的重试按钮。
 */

import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface ErrorMessageProps {
    title?: string;
    message: string;
    onRetry?: () => void;
    className?: string;
}

export default function ErrorMessage({
    title = "出错了",
    message,
    onRetry,
    className,
}: ErrorMessageProps) {
    return (
        <div
            className={cn(
                "flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center",
                className
            )}
        >
            <AlertCircle className="h-8 w-8 text-destructive" />
            <div>
                <p className="font-semibold text-destructive">{title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{message}</p>
            </div>
            {onRetry && (
                <Button variant="outline" size="sm" onClick={onRetry}>
                    重试
                </Button>
            )}
        </div>
    );
}
