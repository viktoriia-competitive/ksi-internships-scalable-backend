import Link from "next/link";
import { ChallengeWorkspace } from "@/features/challenge/ChallengeWorkspace";
import { readChallenge } from "@/lib/api/challenges";

type Props = { params: Promise<{ key: string }> };

export default async function ChallengeViewPage({ params }: Props) {
  const { key } = await params;
  try {
    return <ChallengeWorkspace challenge={await readChallenge(key)} />;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return (
      <div className="surface mx-auto max-w-2xl p-8 text-center sm:p-10">
        <p className="eyebrow">Challenge unavailable</p>
        <h1 className="mt-2 text-2xl font-black tracking-tight text-ink-950">Could not open {key}.</h1>
        <p className="mt-3 text-sm text-slate-500">{message}</p>
        <Link href="/challenges" className="btn-primary mt-6">← Back to catalog</Link>
      </div>
    );
  }
}
