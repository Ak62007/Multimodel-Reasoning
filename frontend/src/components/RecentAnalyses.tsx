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
        className="underline hover:text-neutral-700"
      >
        Recent analyses ({recent.length})
      </button>
      {open && (
        <ul className="mt-2 mx-auto max-w-xs rounded border border-neutral-200 bg-white text-left">
          {recent.map((r) => (
            <li
              key={r.id}
              className="flex items-center justify-between px-3 py-2 hover:bg-neutral-50 border-b border-neutral-100 last:border-0"
            >
              <button
                type="button"
                className="truncate text-left text-neutral-800 hover:underline flex-1"
                onClick={() => navigate(`/report/${r.id}`)}
              >
                {r.filename}
              </button>
              <button
                type="button"
                aria-label={`Forget ${r.filename}`}
                className="ml-2 text-neutral-400 hover:text-neutral-700"
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
