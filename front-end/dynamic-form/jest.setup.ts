import "@testing-library/jest-dom";
import ResizeObserver from "resize-observer-polyfill";

jest.mock("next/router", () => ({
  useRouter: () => ({
    push: jest.fn(),
    prefetch: jest.fn(),
    query: {},
    asPath: "/",
    route: "/",
  }),
}));

if (typeof global.structuredClone === "undefined") {
  global.structuredClone = (val: unknown) => {
    if (val === undefined) return undefined;
    return JSON.parse(JSON.stringify(val));
  };
}

global.ResizeObserver = ResizeObserver;

class IntersectionObserverMock {
  observe = jest.fn();
  disconnect = jest.fn();
  unobserve = jest.fn();
}
Object.defineProperty(global, "IntersectionObserver", {
  writable: true,
  configurable: true,
  value: IntersectionObserverMock,
});

global.requestAnimationFrame = (cb: TimerHandler) => setTimeout(cb, 16);
global.cancelAnimationFrame = (id: number) => clearTimeout(id);

Element.prototype.scrollTo = jest.fn();
Element.prototype.scrollIntoView = jest.fn();

global.URL.createObjectURL = jest.fn(() => "blob:http://localhost");
global.URL.revokeObjectURL = jest.fn();

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: unknown) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }),
});
