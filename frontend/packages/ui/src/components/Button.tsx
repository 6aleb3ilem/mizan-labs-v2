import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

import { cn } from "../cn";
import { Spinner } from "./Motion";

/**
 * Buttons (SPEC §21.3).
 *
 * The interaction detail that matters most is the press: a 1.5 % dip on `:active`, applied in
 * 100 ms, is the difference between a control that feels connected to the pointer and one that
 * feels like a picture of a button. Colour transitions are equally fast — a slow hover fade
 * makes a toolbar feel laggy.
 *
 * Only `transform`, `background-color`, `border-color` and `box-shadow` transition, so no state
 * change ever triggers layout.
 */
export const buttonVariants = cva(
  [
    "relative inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-control font-medium select-none",
    "transition-[transform,background-color,border-color,box-shadow,color] duration-[var(--mz-duration-instant)] ease-out",
    "active:not-disabled:scale-[var(--mz-press-scale)]",
    "disabled:opacity-50 disabled:pointer-events-none",
    "focus-visible:outline-2 focus-visible:outline-offset-2",
  ].join(" "),
  {
    variants: {
      variant: {
        // The inset highlight gives the filled button a lit top edge rather than a flat fill.
        primary: "bg-primary text-primary-on shadow-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.14)] hover:bg-primary-hover",
        secondary: "bg-subtle text-text hover:bg-line",
        outline: "border border-line bg-surface text-text shadow-1 hover:bg-subtle hover:border-line",
        ghost: "text-text hover:bg-subtle",
        danger: "bg-danger text-white shadow-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.14)] hover:brightness-95",
        link: "text-primary underline-offset-4 hover:underline px-0 h-auto active:not-disabled:scale-100",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-9 px-3.5 text-base",
        lg: "h-11 px-5 text-md",
        icon: "h-9 w-9 p-0",
        "icon-sm": "h-8 w-8 p-0",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    loading?: boolean;
    leftIcon?: ReactNode;
    rightIcon?: ReactNode;
  };

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, loading = false, leftIcon, rightIcon, children, disabled, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {/*
        The label stays mounted and only fades while saving, so the button keeps its width. A
        button that shrinks to fit a spinner drags the rest of the toolbar with it, and the
        pointer ends up over a different control than the one that was clicked.
      */}
      <span
        className={cn(
          "inline-flex items-center gap-2 transition-opacity duration-[var(--mz-duration-fast)] ease-out",
          loading && "opacity-0",
        )}
      >
        {leftIcon}
        {children}
        {rightIcon}
      </span>
      {loading && (
        <span className="absolute inset-0 grid place-items-center">
          {/* No delay here: the press already told the user something started. */}
          <Spinner size={size === "lg" ? 18 : 15} delay={0} />
        </span>
      )}
    </button>
  );
});
