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
      }}
    >
      <h3>React Component Test</h3>
      <p>{message}</p>
      <button onClick={() => alert("React button clicked!")}>Click me!</button>
    </div>
  );
};
