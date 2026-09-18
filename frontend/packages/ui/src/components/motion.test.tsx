import "@testing-library/jest-dom/vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Button } from "./Button";
import { Logo, LogoMark } from "./Logo";
import { AnimatedNumber, Skeleton, Spinner } from "./Motion";
import { ToastProvider, useToast } from "./Toast";

describe("Button", () => {
  it("keeps its label mounted while loading so the width does not change", () => {
    const { rerender } = render(<Button>Enregistrer</Button>);
    const label = screen.getByText("Enregistrer");
    rerender(<Button loading>Enregistrer</Button>);
    // Same node, faded rather than swapped for a spinner.
    expect(screen.getByText("Enregistrer")).toBe(label);
    expect(screen.getByRole("button")).toHaveAttribute("aria-busy", "true");
  });
});

describe("Spinner", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("shows nothing until the delay has passed, so a fast request never flashes one", () => {
    render(<Spinner delay={400} label="Chargement" />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(400));
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders immediately when the delay is waived", () => {
    render(<Spinner delay={0} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});

describe("Skeleton", () => {
  it("is hidden from assistive technology: it stands in for content that is not there yet", () => {
    const { container } = render(<Skeleton shape="text" width="40%" />);
    const node = container.firstElementChild!;
    expect(node).toHaveAttribute("aria-hidden");
    expect(node).toHaveClass("mz-skeleton");
  });
});

describe("AnimatedNumber", () => {
  it("renders the exact value when motion is reduced", () => {
    render(<AnimatedNumber value={1234} duration={0} />);
    expect(screen.getByText("1,234")).toBeInTheDocument();
  });

  it("applies a formatter and keeps tabular figures so the width never shifts", () => {
    const { container } = render(<AnimatedNumber value={42} duration={0} format={(v) => `${v} essais`} />);
    expect(screen.getByText("42 essais")).toBeInTheDocument();
    expect(container.firstElementChild).toHaveClass("tabular");
  });
});

function ToastTrigger() {
  const toast = useToast();
  return (
    <>
      <button type="button" onClick={() => toast.success("Devis envoyé")}>
        push success
      </button>
      <button type="button" onClick={() => toast.error("Envoi impossible")}>
        push error
      </button>
    </>
  );
}

describe("Toast stack", () => {
  it("announces toasts in a polite live region", () => {
    render(
      <ToastProvider label="Notifications">
        <ToastTrigger />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("push success"));
    expect(screen.getByText("Devis envoyé")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Notifications" })).toBeInTheDocument();
    expect(screen.getByText("Devis envoyé").closest("li")).toHaveAttribute("role", "status");
  });

  it("stacks newest in front and lets a toast be dismissed", async () => {
    render(
      <ToastProvider>
        <ToastTrigger />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("push success"));
    fireEvent.click(screen.getByText("push error"));

    const items = screen.getAllByRole("status");
    expect(items).toHaveLength(2);
    // Newest first: it is drawn on top of the stack.
    expect(items[0]).toHaveTextContent("Envoi impossible");
    expect(Number(items[0]!.style.zIndex)).toBeGreaterThan(Number(items[1]!.style.zIndex));

    fireEvent.click(screen.getAllByRole("button", { name: "Close" })[0]!);
    await waitFor(() => expect(screen.queryByText("Envoi impossible")).not.toBeInTheDocument());
    expect(screen.getByText("Devis envoyé")).toBeInTheDocument();
  });

  it("holds an error carrying an action open instead of expiring it", () => {
    vi.useFakeTimers();
    function Trigger() {
      const toast = useToast();
      return (
        <button
          type="button"
          onClick={() => toast.show({ title: "Échec", tone: "danger", action: { label: "Réessayer", onClick: () => {} } })}
        >
          push
        </button>
      );
    }
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("push"));
    act(() => void vi.advanceTimersByTime(60_000));
    expect(screen.getByText("Échec")).toBeInTheDocument();
    vi.useRealTimers();
  });
});

describe("Logo", () => {
  it("carries one accessible name and hides the decorative mark inside it", () => {
    const { container } = render(<Logo label="Mizan Labs" />);
    expect(screen.getByRole("img", { name: "Mizan Labs" })).toBeInTheDocument();
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden");
  });

  it("is purely decorative when rendered beside a visible product name", () => {
    render(<LogoMark />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
