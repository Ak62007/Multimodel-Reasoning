import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { uploadJob } from "../api/jobs";
import RecentAnalyses from "../components/RecentAnalyses";

interface UploadScreenProps {
  onJobCreated: (jobId: string) => void;
  onViewRecent: (jobId: string) => void;
}

const ACCEPTED = ".mp4,.mov,.avi,.webm";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadScreen({ onJobCreated, onViewRecent }: UploadScreenProps) {
  const [file, setFile] = useState<File | null>(null);
  const [speakerLabel, setSpeakerLabel] = useState("B");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    document.title = "MMR — Upload";
  }, []);

  const mutation = useMutation({
    mutationFn: (vars: { file: File; speaker: string }) =>
      uploadJob(vars.file, vars.speaker),
    onSuccess: (job) => {
      onJobCreated(job.id);
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    },
  });

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    mutation.mutate({ file, speaker: speakerLabel });
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-reading flex-col items-center px-4 py-16">
      <div className="w-full rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-neutral-900">MMR</h1>
        <p className="mt-2 text-sm text-neutral-600">
          Multimodal behavioral analysis for interview videos.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <label
            htmlFor="video-input"
            className={[
              "block cursor-pointer rounded-lg border-2 border-dashed px-6 py-10 text-center transition",
              isDragging ? "border-neutral-900 bg-neutral-50" : "border-neutral-300 hover:border-neutral-400",
            ].join(" ")}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            data-testid="dropzone"
          >
            <input
              id="video-input"
              ref={inputRef}
              data-testid="file-input"
              type="file"
              accept={ACCEPTED}
              className="sr-only"
              onChange={(e) => {
                if (e.target.files?.[0]) setFile(e.target.files[0]);
              }}
            />
            {file ? (
              <div>
                <p className="text-sm font-medium text-neutral-900">{file.name}</p>
                <p className="mt-1 text-xs text-neutral-500">{formatSize(file.size)}</p>
              </div>
            ) : (
              <div>
                <p className="text-sm text-neutral-700">
                  Drag a video here or <span className="underline">browse</span>
                </p>
                <p className="mt-1 text-xs text-neutral-500">
                  Accepts .mp4, .mov, .avi, .webm
                </p>
              </div>
            )}
          </label>

          <details
            className="rounded-md border border-neutral-200 px-3 py-2 text-sm"
            open={advancedOpen}
            onToggle={(e) => setAdvancedOpen((e.target as HTMLDetailsElement).open)}
          >
            <summary className="cursor-pointer text-neutral-600">Advanced</summary>
            <div className="mt-3 flex items-center gap-2">
              <label htmlFor="speaker-label" className="text-neutral-600">
                Speaker label
              </label>
              <input
                id="speaker-label"
                type="text"
                value={speakerLabel}
                maxLength={3}
                onChange={(e) => setSpeakerLabel(e.target.value.toUpperCase())}
                className="w-16 rounded-md border border-neutral-300 px-2 py-1 text-center"
              />
            </div>
          </details>

          <button
            type="submit"
            disabled={!file || mutation.isPending}
            data-testid="start-analysis"
            className="w-full rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
          >
            {mutation.isPending ? "Uploading…" : "Start Analysis"}
          </button>
        </form>

        <RecentAnalyses onSelect={onViewRecent} />
      </div>
    </main>
  );
}
