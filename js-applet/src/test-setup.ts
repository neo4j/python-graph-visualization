import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });

class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

vi.stubGlobal("ResizeObserver", ResizeObserver);
vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
  callback(0);
  return 0;
});
vi.stubGlobal("cancelAnimationFrame", vi.fn());
const canvasContextStub = {
  clearRect: vi.fn(),
  drawImage: vi.fn(),
  fillRect: vi.fn(),
  getImageData: vi.fn(),
  measureText: vi.fn(() => ({ width: 0 })),
  putImageData: vi.fn(),
  restore: vi.fn(),
  save: vi.fn(),
  scale: vi.fn(),
  setTransform: vi.fn(),
} as unknown as CanvasRenderingContext2D;

HTMLCanvasElement.prototype.getContext = vi.fn(
  () => canvasContextStub
) as unknown as typeof HTMLCanvasElement.prototype.getContext;

afterEach(() => {
  cleanup();
  document.body.innerHTML = "";
  document.head.innerHTML = "";
});
