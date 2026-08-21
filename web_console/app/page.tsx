import { DashboardOverview } from "@/features/dashboard/DashboardOverview";
import { browseChallenges } from "@/lib/api/challenges";
import { browseAttempts } from "@/lib/api/attempts";

export default async function HomePage() {
  try {
    const [challenges, attempts] = await Promise.all([
      browseChallenges({ page: 1, size: 6, orderBy: "acceptedCount", direction: "desc" }),
      browseAttempts({ page: 1, size: 12 }),
    ]);
    return <DashboardOverview challenges={challenges.entries} attempts={attempts.entries} />;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return (
      <div className="dark-surface mx-auto max-w-3xl overflow-hidden p-8 sm:p-10">
        <p className="eyebrow">Connection error</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-white">Runline cannot reach the control API.</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">Start the control plane and refresh this page.</p>
        <pre className="mt-5 overflow-auto rounded-xl border border-white/10 bg-white/5 p-4 font-mono text-xs text-rose-300">{message}</pre>
      </div>
    );
  }
}
