import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getRecentJobs, removeRecentJob } from "../lib/storage";

export function RecentAnalyses() {
  const navigate = useNavigate();
  const [recent, setRecent] = useState(getRecentJobs);
  const [open, setOpen] = useState(false);

  if (recent.length === 0) return null;

  return (
    <div className="text-center text-xs text-neutral-500" data-testid="recent-analyses">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="transition hover:text-sand"
      >
        Recent analyses ({recent.length})
      </button>
      {open && (
        <ul className="mt-2 mx-auto max-w-xs overflow-hidden rounded-xl border border-white/[0.07] bg-white/[0.02] text-left">
          {recent.map((r) => (
            <li
              key={r.id}
              className="flex items-center justify-between border-b border-white/[0.05] px-3 py-2 transition last:border-0 hover:bg-white/[0.03]"
            >
              <button
                type="button"
                className="flex-1 truncate text-left text-neutral-300 hover:text-sand"
                onClick={() => navigate(`/report/${r.id}`)}
              >
                {r.filename}
              </button>
              <button
                type="button"
                aria-label={`Forget ${r.filename}`}
                className="ml-2 text-neutral-600 hover:text-neutral-300"
                onClick={() => {
                  removeRecentJob(r.id);
                  setRecent(getRecentJobs());
                }}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
