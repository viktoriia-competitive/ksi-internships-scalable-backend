import type { Metadata } from "next";
import { Navbar } from "@/components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Runline — Online Judge",
    template: "%s · Runline",
  },
  description: "A fast, queue-driven competitive programming execution_engine.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        <main className="shell py-6 sm:py-8 lg:py-10">{children}</main>
        <footer className="shell pb-8 pt-4">
          <div className="flex flex-col gap-2 border-t border-black/10 pt-5 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between">
            <span>Runline / queue-driven online judge</span>
            <span className="font-mono">API · PostgreSQL · Redis · isolated workers</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
