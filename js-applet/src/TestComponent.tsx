import { GraphVisualization } from "@neo4j-ndl/react";
import React from "react";

interface TestComponentProps {
  message?: string;
}

export const TestComponent: React.FC<TestComponentProps> = ({
  message = "Hello from React!",
}) => {
  return (
    <div
      style={{
        padding: "10px",
        border: "1px solid #ccc",
        borderRadius: "4px",
        backgroundColor: "#f9f9f9",
        height: "500px",
        width: "500px",
      }}
    >
      <h3>React Component Test</h3>
      <p>{message}</p>
      <GraphVisualization
        nodes={[
          { id: "1", labels: ["Node 1"], properties: {} },
          { id: "2", labels: ["Node 2"], properties: {} },
        ]}
        rels={[{ id: "1", type: "REL 1", properties: {}, from: "1", to: "2" }]}
      />
    </div>
  );
};
