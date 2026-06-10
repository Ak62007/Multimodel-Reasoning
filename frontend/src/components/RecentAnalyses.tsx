import { useState } from "react";
import { getRecentJobs } from "../lib/storage";

interface RecentAnalysesProps {
  onSelect: (jobId: string) => void;
}

export default function RecentAnalyses({ onSelect }: RecentAnalysesProps) {
  const [open, setOpen] = useState(false);
  const recent = getRecentJobs();
  if (recent.length === 0) {
    return null;
  }
  return (
    <div className="mt-4 text-center">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-sm text-neutral-500 hover:text-neutral-700"
      >
        Recent analyses ({recent.length})
      </button>
      {open && (
        <ul className="mt-2 inline-block rounded-md border border-neutral-200 bg-white text-left shadow-sm">
          {recent.map((entry) => (
            <li key={entry.id} className="border-b border-neutral-100 last:border-0">
              <button
                type="button"
                className="block w-full px-4 py-2 text-sm hover:bg-neutral-50"
                onClick={() => onSelect(entry.id)}
              >
                <span className="font-medium">{entry.filename}</span>
                <span className="ml-2 text-xs text-neutral-500">
                  {new Date(entry.completedAt).toLocaleString()}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
