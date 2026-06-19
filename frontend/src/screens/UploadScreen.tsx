import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import { jobsApi } from "../api/jobs";
import type { Tier } from "../types/api";
import { setActiveJobId } from "../lib/storage";
import { RecentAnalyses } from "../components/RecentAnalyses";

const ACCEPT = ".mp4,.mov,.avi,.webm,.parquet";

export default function UploadScreen() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [tier, setTier] = useState<Tier>("free");
  const [geminiKey, setGeminiKey] = useState("");
  const [assemblyaiKey, setAssemblyaiKey] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    document.title = "MMR — Upload";
  }, []);

  const keysReady = geminiKey.trim() !== "" && assemblyaiKey.trim() !== "";

  const submit = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file selected");
      return jobsApi.createJob(file, {
        tier,
        geminiApiKey: geminiKey.trim(),
        assemblyaiApiKey: assemblyaiKey.trim(),
      });
    },
    onSuccess: (job) => {
      setActiveJobId(job.id);
      navigate(`/analyzing/${job.id}`);
    },
    onError: (err: Error) => {
      // Surface the server's friendly detail without the "HTTP 400:" prefix.
      const msg = (err.message ?? "Upload failed").replace(/^HTTP \d+:\s*/, "");
      toast.error(msg);
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

        <div className="space-y-2">
          <span className="text-xs font-medium uppercase tracking-wide text-stone-300">
            What kind of API key do you have?
          </span>
          <div className="grid grid-cols-2 gap-2" data-testid="tier-selector">
            <TierOption
              value="free"
              current={tier}
              onSelect={setTier}
              title="Free key"
              sub="A lighter, faster read that fits free-tier rate limits."
            />
            <TierOption
              value="paid"
              current={tier}
              onSelect={setTier}
              title="Paid key"
              sub="The full multi-agent depth — richest report."
            />
          </div>
        </div>

        <div className="space-y-3 rounded-xl border border-white/[0.07] bg-white/[0.015] p-4">
          <div className="flex items-baseline justify-between">
            <span className="text-xs font-medium uppercase tracking-wide text-stone-300">
              Your API keys
            </span>
            <span className="text-[11px] text-neutral-500">used only for this run · never stored</span>
          </div>
          <KeyField
            label="Gemini API key"
            value={geminiKey}
            onChange={setGeminiKey}
            placeholder="AIza…"
            href="https://aistudio.google.com/app/apikey"
            testid="gemini-key"
          />
          <KeyField
            label="AssemblyAI API key"
            value={assemblyaiKey}
            onChange={setAssemblyaiKey}
            placeholder="••••••••"
            href="https://www.assemblyai.com/dashboard/api-keys"
            testid="assemblyai-key"
          />
          <p
            className="border-t border-white/[0.06] pt-3 text-[11px] leading-relaxed text-neutral-500"
            data-testid="key-privacy-note"
          >
            <span className="text-stone-400">Your keys, your control.</span> They&apos;re sent only
            for this one analysis and used to call Google &amp; AssemblyAI directly — never saved to a
            database, file, or log. Tip: use a key you can revoke, and remove it when you&apos;re done.
          </p>
        </div>

        <p className="flex items-center gap-2 text-xs text-neutral-500">
          <span className="h-1 w-1 rounded-full bg-sand/70" />
          The interviewee is detected automatically — no setup needed.
        </p>

        <button
          type="button"
          disabled={!file || !keysReady || submit.isPending}
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

function TierOption({
  value,
  current,
  onSelect,
  title,
  sub,
}: {
  value: Tier;
  current: Tier;
  onSelect: (t: Tier) => void;
  title: string;
  sub: string;
}) {
  const active = current === value;
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      aria-pressed={active}
      data-testid={`tier-${value}`}
      className={`rounded-xl border p-3 text-left transition ${
        active
          ? "border-sand/50 bg-sand/[0.08] ring-1 ring-inset ring-sand/30"
          : "border-white/10 bg-white/[0.015] hover:border-white/20 hover:bg-white/[0.03]"
      }`}
    >
      <div
        className={`text-sm font-medium ${active ? "text-sand" : "text-stone-200"}`}
      >
        {title}
      </div>
      <div className="mt-1 text-[11px] leading-relaxed text-neutral-500">{sub}</div>
    </button>
  );
}

function KeyField({
  label,
  value,
  onChange,
  placeholder,
  href,
  testid,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  href: string;
  testid: string;
}) {
  return (
    <label className="block">
      <span className="flex items-center justify-between text-[11px] text-neutral-400">
        {label}
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="text-neutral-500 underline-offset-2 hover:text-sand hover:underline"
        >
          get a key ↗
        </a>
      </span>
      <input
        type="password"
        autoComplete="off"
        spellCheck={false}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 font-mono text-sm text-stone-200 placeholder:text-neutral-600 focus:border-sand/40 focus:outline-none focus:ring-1 focus:ring-sand/30"
        data-testid={testid}
      />
    </label>
  );
}
