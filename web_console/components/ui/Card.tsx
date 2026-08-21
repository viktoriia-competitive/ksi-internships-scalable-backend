import Link from "next/link";
import type { ReactNode } from "react";

type CardAction = {
  href: string;
  label: string;
};

type CardProps = {
  title: string;
  subtitle?: string;
  actionHref?: string;
  actionLabel?: string;
  children: ReactNode;
};

function CardHeading({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: CardAction;
}) {
  return (
    <header className="card-header">
      <div>
        <h2 className="card-title">{title}</h2>
        {subtitle && <p className="card-subtitle">{subtitle}</p>}
      </div>
      {action && (
        <Link href={action.href} className="card-action">
          {action.label}
        </Link>
      )}
    </header>
  );
}

export function Card({ title, subtitle, actionHref, actionLabel, children }: CardProps) {
  const action =
    actionHref && actionLabel ? { href: actionHref, label: actionLabel } : undefined;

  return (
    <section className="card">
      <CardHeading title={title} subtitle={subtitle} action={action} />
      <div className="card-body">{children}</div>
    </section>
  );
}
