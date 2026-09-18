import "@testing-library/jest-dom/vitest";

/*
 * jsdom implements neither ResizeObserver nor matchMedia, both of which the design system uses
 * for real work: the toast stack measures its toasts to place them, and the motion helpers read
 * `prefers-reduced-motion`. Stubbing them here keeps that behaviour testable rather than pushing
 * defensive branches into components that never need them in a browser.
 */
if (!("ResizeObserver" in globalThis)) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

if (!globalThis.matchMedia) {
  globalThis.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener() {},
    removeEventListener() {},
    addListener() {},
    removeListener() {},
    dispatchEvent: () => false,
  })) as unknown as typeof globalThis.matchMedia;
}
