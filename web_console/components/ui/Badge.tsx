import type { ReactNode } from "react";

type BadgeProps = {
  children: ReactNode;
  tone?: string;
  className?: string;
};

export function Badge({ children, tone, className }: BadgeProps) {
  const classes = ["badge", tone, className].filter(Boolean).join(" ");
  return <span className={classes}>{children}</span>;
}
