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
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    document.title = "MMR — Upload";
  }, []);

  const submit = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file selected");
      return jobsApi.createJob(file);
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
    <main className="mx-auto max-w-xl px-4 pt-10 pb-12">
      <button
        type="button"
        onClick={() => navigate("/")}
        className="text-xs text-neutral-500 transition hover:text-sand"
        data-testid="back-to-intro"
      >
        ← About
      </button>
      <header className="text-center mb-8 mt-6">
        <h1 className="font-display text-4xl font-light tracking-tight text-stone-100">
          Analyze an interview
        </h1>
        <p className="mt-2 text-sm text-neutral-500">
          Drop in a recording and MMR reads face, voice and words.
        </p>
      </header>

      <section className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-6 space-y-5">
        <div
          className={`group rounded-xl border border-dashed p-8 text-center cursor-pointer transition ${
            file
              ? "border-sand/40 bg-sand/[0.04]"
              : "border-white/15 hover:border-sand/40 hover:bg-white/[0.03]"
          }`}
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
            <div className="text-sm">
              <div className="font-medium text-neutral-100">{file.name}</div>
              <div className="mt-1 text-neutral-500">
                {(file.size / (1024 * 1024)).toFixed(1)} MB · click to replace
              </div>
            </div>
          ) : (
            <div className="text-sm text-neutral-400">
              <div>Drop a video here, or click to browse</div>
              <div className="mt-1 font-mono text-[11px] text-neutral-600">
                .mp4 · .mov · .avi · .webm
              </div>
            </div>
          )}
        </div>

        <p className="flex items-center gap-2 text-xs text-neutral-500">
          <span className="h-1 w-1 rounded-full bg-sand/70" />
          The interviewee is detected automatically — no setup needed.
        </p>

        <button
          type="button"
          disabled={!file || submit.isPending}
          onClick={() => submit.mutate()}
          className="w-full rounded-xl bg-sand/[0.12] py-2.5 text-sm font-semibold text-sand ring-1 ring-inset ring-sand/40 shadow-[0_0_30px_-8px_rgba(203,180,145,0.55)] transition duration-300 hover:bg-sand/[0.18] hover:text-[#e7d8b8] hover:ring-sand/60 disabled:cursor-not-allowed disabled:bg-white/[0.03] disabled:text-neutral-600 disabled:ring-white/10 disabled:shadow-none"
          data-testid="start-button"
        >
          {submit.isPending ? "Uploading…" : "Start analysis"}
        </button>
      </section>

      <div className="mt-6">
        <RecentAnalyses />
      </div>
    </main>
  );
}
