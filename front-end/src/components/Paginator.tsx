type Props = {
  offset: number;
  limit: number;
  total: number;
  onChange: (offset: number) => void;
  /** What is being paged, for the accessible label (e.g. "pages", "links"). */
  label: string;
};

/** "51-100 of 120" with previous / next controls, disabled at either end. */
export function Paginator({ offset, limit, total, onChange, label }: Props) {
  const first = total === 0 ? 0 : offset + 1;
  const last = Math.min(offset + limit, total);
  const button =
    "rounded border border-zinc-300 px-3 py-1 text-sm disabled:opacity-40 dark:border-zinc-700";

  return (
    <nav aria-label={`${label} pagination`} className="flex items-center gap-3">
      <button
        type="button"
        className={button}
        disabled={offset === 0}
        onClick={() => onChange(Math.max(0, offset - limit))}
      >
        Previous
      </button>
      <span className="text-sm tabular-nums">
        {first}-{last} of {total}
      </span>
      <button
        type="button"
        className={button}
        disabled={offset + limit >= total}
        onClick={() => onChange(offset + limit)}
      >
        Next
      </button>
    </nav>
  );
}
