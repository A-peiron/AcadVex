/** LoadingSpinner.tsx
 * 通用加载动画组件。
 * 提供三种尺寸（sm / md / lg）和可选标签文字。
 */

import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
    size?: "sm" | "md" | "lg";
    label?: string;
    className?: string;
}

const sizeMap = {
    sm: "h-4 w-4 border-2",
    md: "h-8 w-8 border-2",
    lg: "h-12 w-12 border-4",
};

export default function LoadingSpinner({
    size = "md",
    label,
    className,
}: LoadingSpinnerProps) {
    return (
        <div className={cn("flex flex-col items-center justify-center gap-2", className)}>
            <div
                className={cn(
                    "animate-spin rounded-full border-muted border-t-primary",
                    sizeMap[size]
                )}
                role="status"
                aria-label={label ?? "加载中"}
            />
            {label && (
                <p className="text-sm text-muted-foreground">{label}</p>
            )}
        </div>
    );
}
