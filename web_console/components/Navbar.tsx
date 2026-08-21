"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Overview" },
  { href: "/challenges", label: "Challenges" },
  { href: "/attempts", label: "Attempts" },
];

function BoltMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 fill-none stroke-current" strokeWidth="2">
      <path d="M13.5 2 5 13h6l-.5 9L19 10h-6l.5-8Z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-ink-950/95 text-white backdrop-blur-xl">
      <div className="shell flex min-h-16 items-center justify-between gap-4 py-2">
        <div className="flex min-w-0 items-center gap-5 sm:gap-8">
          <Link href="/" className="group flex shrink-0 items-center gap-2.5" aria-label="Runline home">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-500 text-white shadow-[0_8px_24px_rgba(255,107,53,0.28)] transition group-hover:-rotate-3 group-hover:scale-105">
              <BoltMark />
            </span>
            <div className="hidden leading-none sm:block">
              <div className="text-[15px] font-black tracking-[-0.03em]">RUNLINE</div>
              <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.22em] text-slate-500">online judge</div>
            </div>
          </Link>

          <nav className="flex items-center gap-1 rounded-xl border border-white/10 bg-white/[0.04] p-1">
            {links.map((link) => {
              const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-lg px-3 py-2 text-xs font-bold transition sm:px-4 ${
                    active ? "bg-white text-ink-950" : "text-slate-400 hover:bg-white/[0.06] hover:text-white"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="hidden items-center gap-2 text-xs text-slate-500 md:flex">
          <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_0_4px_rgba(52,211,153,0.10)]" />
          <span className="font-mono">judge network</span>
        </div>
      </div>
    </header>
  );
}
