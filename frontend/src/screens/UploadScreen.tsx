import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import { jobsApi } from "../api/jobs";
import { setActiveJobId } from "../lib/storage";
import { RecentAnalyses } from "../components/RecentAnalyses";

const ACCEPT = ".mp4,.mov,.avi,.webm,.parquet";

export default function UploadScreen() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [speakerLabel, setSpeakerLabel] = useState("B");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    document.title = "MMR — Upload";
  }, []);

  const submit = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file selected");
      return jobsApi.createJob(file, speakerLabel);
    },
    onSuccess: (job) => {
      setActiveJobId(job.id);
      navigate(`/analyzing/${job.id}`);
    },
    onError: (err: Error) => {
      toast.error(err.message ?? "Upload failed");
    },
  });

  return (
    <main className="mx-auto max-w-xl px-4 pt-16 pb-12">
      <header className="text-center mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">MMR</h1>
        <p className="mt-2 text-sm text-neutral-600">
          Multimodal behavioral analysis for interview videos
        </p>
      </header>

      <section className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm space-y-5">
        <div
          className="border-2 border-dashed border-neutral-300 rounded-lg p-8 text-center hover:bg-neutral-50 cursor-pointer transition"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files[0];
            if (f) setFile(f);
          }}
          data-testid="dropzone"
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            data-testid="file-input"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) setFile(f);
            }}
          />
          {file ? (
            <div className="text-sm text-neutral-700">
              <div className="font-medium">{file.name}</div>
              <div className="text-neutral-500 mt-1">
                {(file.size / (1024 * 1024)).toFixed(1)} MB
              </div>
            </div>
          ) : (
            <div className="text-sm text-neutral-500">
              <div>Drop a video here, or click to browse</div>
              <div className="mt-1 text-xs">
                .mp4, .mov, .avi, .webm
              </div>
            </div>
          )}
        </div>

        <details
          open={advancedOpen}
          onToggle={(e) => setAdvancedOpen((e.currentTarget as HTMLDetailsElement).open)}
        >
          <summary className="text-xs text-neutral-500 cursor-pointer select-none">
            Advanced
          </summary>
          <div className="mt-3 space-y-2 pl-2">
            <label className="block text-xs">
              <span className="text-neutral-600">Speaker label</span>
              <input
                type="text"
                value={speakerLabel}
                onChange={(e) => setSpeakerLabel(e.target.value)}
                className="mt-1 block w-20 rounded border border-neutral-300 px-2 py-1 text-sm"
                data-testid="speaker-label"
              />
            </label>
          </div>
        </details>

        <button
          type="button"
          disabled={!file || submit.isPending}
          onClick={() => submit.mutate()}
          className="w-full rounded-lg bg-neutral-900 text-white py-2.5 text-sm font-medium hover:bg-neutral-800 disabled:bg-neutral-300 disabled:cursor-not-allowed transition"
          data-testid="start-button"
        >
          {submit.isPending ? "Uploading…" : "Start Analysis"}
        </button>
      </section>

      <div className="mt-6">
        <RecentAnalyses />
      </div>
    </main>
  );
}
