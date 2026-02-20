import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import { Component, type ErrorInfo, type ReactNode } from "react";

type ErrorBoundaryProps = { children: ReactNode };
type ErrorBoundaryState = { error: Error | null };

export class GraphErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[neo4j-viz] Rendering error:", error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div
          style={{
            padding: "24px",
            fontFamily: "system-ui, sans-serif",
            color: "#c0392b",
            background: "#fdf0ef",
            borderRadius: "8px",
            border: "1px solid #e6b0aa",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
          <h3 style={{ margin: "0 0 8px" }}>Graph rendering failed</h3>
          <pre
            style={{
              margin: 0,
              whiteSpace: "pre-wrap",
              fontSize: "13px",
              color: "#6c3428",
            }}
          >
            {this.state.error.message}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}
