export function ConfidenceBadge({
  score,
  category,
}: {
  score: number;
  category: string;
}) {
  const colors: Record<string, string> = {
    strong: "bg-green-100 text-green-800",
    probable: "bg-blue-100 text-blue-800",
    possible: "bg-amber-100 text-amber-800",
    unlikely: "bg-gray-100 text-gray-700",
  };
  return (
    <span className={`badge ${colors[category] || colors.unlikely}`}>
      {score.toFixed(0)}/100 · {category}
    </span>
  );
}

export function ReviewBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    confirmed: "bg-green-100 text-green-800",
    rejected: "bg-red-100 text-red-800",
    needs_more_info: "bg-amber-100 text-amber-800",
    duplicate: "bg-purple-100 text-purple-800",
    not_reviewed: "bg-gray-100 text-gray-700",
  };
  return (
    <span className={`badge ${map[status] || map.not_reviewed}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
