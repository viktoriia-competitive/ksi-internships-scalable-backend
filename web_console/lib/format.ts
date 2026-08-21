const DATE_TIME = new Intl.DateTimeFormat(undefined, {
  dateStyle: "short",
  timeStyle: "medium",
});

export function formatDateTime(iso: string): string {
  const instant = Date.parse(iso);
  return Number.isFinite(instant) ? DATE_TIME.format(new Date(instant)) : iso;
}
