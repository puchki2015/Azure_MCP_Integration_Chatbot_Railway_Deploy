import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  children: ReactNode;
};

export function Button({ variant = "primary", className = "", children, ...props }: Props) {
  return (
    <button
      className={[
        "button",
        `button--${variant}`,
        className
      ].join(" ")}
      {...props}
    >
      {children}
    </button>
  );
}
