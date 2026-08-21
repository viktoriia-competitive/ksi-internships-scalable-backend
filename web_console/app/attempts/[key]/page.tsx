import { AttemptDetails } from "@/features/attempts/AttemptDetails";

type Props = { params: Promise<{ key: string }> };

export default async function AttemptDetailPage({ params }: Props) {
  const { key } = await params;
  return <AttemptDetails attemptKey={key} />;
}
