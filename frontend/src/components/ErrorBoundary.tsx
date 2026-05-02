import React, { Component, type ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "./ui/button";

interface ErrorBoundaryProps {
    children: ReactNode;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error("ErrorBoundary caught an error:", error, errorInfo);
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null });
        window.location.reload();
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-background p-4">
                    <div className="max-w-md w-full space-y-4 text-center">
                        <div className="flex justify-center">
                            <AlertCircle className="h-16 w-16 text-destructive" />
                        </div>
                        <h1 className="text-2xl font-bold text-foreground">出错了</h1>
                        <p className="text-muted-foreground">
                            应用遇到了一个错误。请尝试刷新页面。
                        </p>
                        {this.state.error && (
                            <details className="text-left bg-muted p-3 rounded-lg text-xs">
                                <summary className="cursor-pointer font-semibold mb-2">
                                    错误详情
                                </summary>
                                <pre className="whitespace-pre-wrap break-words">
                                    {this.state.error.toString()}
                                </pre>
                            </details>
                        )}
                        <Button onClick={this.handleReset} className="w-full">
                            刷新页面
                        </Button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
