import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

const CHANNELS = [
  { n: "01", title: "What they show", body: "Gaze, blinks, jaw and micro-expressions." },
  { n: "02", title: "How they sound", body: "Loudness, pitch and vocal expressiveness." },
  { n: "03", title: "What they say", body: "Pace, filler words and pauses." },
];

const RECORDING_TIPS = [
  "Face clearly visible and well-lit — head-and-shoulders, looking toward the camera.",
  "One person on camera. Both sides can talk; the candidate is the one being filmed.",
  "Clean audio — a quiet room and a decent mic. Noise blurs the voice read.",
  "Steady shot, no heavy filters or virtual backgrounds that warp the face.",
  "A natural length — roughly 5 to 15 minutes of real conversation.",
];

export default function IntroScreen() {
  const navigate = useNavigate();

  useEffect(() => {
    document.title = "MMR — Multimodal Interview Analysis";
  }, []);

  return (
    <div className="grain relative min-h-screen w-full overflow-hidden">
      {/* one soft, warm glow — barely there */}
      <div
        aria-hidden
        className="animate-drift pointer-events-none absolute -top-56 left-1/2 h-[42rem] w-[42rem] -translate-x-1/2 rounded-full bg-sand/[0.06] blur-[150px]"
      />

      <div className="relative mx-auto max-w-3xl px-6">
        {/* top bar */}
        <header className="flex items-center justify-between py-7">
          <span className="font-mono text-[13px] tracking-[0.4em] text-stone-200">MMR</span>
          <span className="hidden font-mono text-[11px] uppercase tracking-[0.25em] text-stone-500 sm:block">
            behavioral signal
          </span>
        </header>

        {/* hero */}
        <section className="pt-16 sm:pt-24">
          <p className="animate-reveal flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.4em] text-sand/70">
            <span className="h-px w-8 bg-sand/40" />
            a closer read
          </p>
          <h1
            className="animate-reveal mt-7 font-display text-5xl font-light leading-[1.04] tracking-[-0.01em] text-stone-100 sm:text-7xl"
            style={{ animationDelay: "80ms" }}
          >
            Every interview
            <br />
            says <span className="italic text-sand">more</span> than its words.
          </h1>
          <p
            className="animate-reveal mt-8 max-w-xl text-lg leading-relaxed text-stone-400"
            style={{ animationDelay: "180ms" }}
          >
            MMR watches a recording the way an attentive coach would — reading face,
            voice and words at once — and marks the exact moments worth re-watching,
            each with{" "}
            <span className="text-stone-200">what happened, when, and why it matters.</span>
          </p>

          <Waveform />

          <div
            className="animate-fade-up mt-10 flex flex-wrap items-center gap-5"
            style={{ animationDelay: "360ms" }}
          >
            <button
              type="button"
              onClick={() => navigate("/upload")}
              className="group inline-flex items-center gap-2 rounded-full bg-sand px-7 py-3 text-sm font-semibold text-stone-950 transition hover:bg-[#d9c5a3]"
              data-testid="get-started"
            >
              Analyze a video
              <span className="transition-transform group-hover:translate-x-0.5">→</span>
            </button>
            <span className="font-mono text-[11px] uppercase tracking-wider text-stone-500">
              a clip in · minutes later, a read
            </span>
          </div>
        </section>

        {/* what it watches — editorial 3-up */}
        <section className="mt-28 sm:mt-40">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.3em] text-stone-500">
            What it watches
          </h2>
          <div className="mt-6 grid divide-y divide-white/[0.06] border-y border-white/[0.06] sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            {CHANNELS.map((c) => (
              <div key={c.n} className="px-1 py-6 sm:px-6 sm:first:pl-1 sm:last:pr-1">
                <span className="font-mono text-xs text-sand/60">{c.n}</span>
                <h3 className="mt-3 font-display text-xl font-light text-stone-100">
                  {c.title}
                </h3>
                <p className="mt-1.5 text-sm leading-relaxed text-stone-400">{c.body}</p>
              </div>
            ))}
          </div>
          <p className="mt-7 max-w-xl text-[15px] leading-relaxed text-stone-400">
            On their own, each channel is noise. What matters is where they{" "}
            <span className="italic text-stone-200">line up</span> — or quietly{" "}
            <span className="italic text-stone-200">pull apart.</span> That's the read.
          </p>
        </section>

        {/* record it right */}
        <section className="mt-28 border-t border-white/[0.06] pt-12 sm:mt-40" data-testid="recording-disclaimer">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h2 className="font-display text-2xl font-light text-stone-100">Record it right</h2>
            <span className="text-xs text-stone-500">— the read is only as good as the footage</span>
          </div>
          <ol className="mt-7 space-y-4">
            {RECORDING_TIPS.map((tip, i) => (
              <li key={tip} className="flex gap-4 text-[15px] leading-relaxed text-stone-300">
                <span className="mt-px font-mono text-xs text-sand/60">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span>{tip}</span>
              </li>
            ))}
          </ol>
        </section>

        {/* footer */}
        <section className="mt-28 flex flex-col items-center gap-6 pb-28 text-center sm:mt-40">
          <p className="font-display text-3xl font-light italic text-stone-200">
            Got a recording?
          </p>
          <button
            type="button"
            onClick={() => navigate("/upload")}
            className="inline-flex items-center gap-2 rounded-full border border-white/12 px-7 py-3 text-sm font-medium text-stone-100 transition hover:border-sand/40 hover:text-sand"
          >
            Read it →
          </button>
        </section>
      </div>
    </div>
  );
}

/** An abstract waveform of the interview with a soft light passing over it and
 *  two marked moments — the product's "go watch this" idea, in monochrome. */
function Waveform() {
  const bars = 76;
  const marks = [
    { left: "31%", label: "01:12" },
    { left: "68%", label: "04:38" },
  ];

  return (
    <div
      className="animate-fade-up relative mt-16 overflow-hidden rounded-2xl border border-white/[0.06] bg-white/[0.015] p-6"
      style={{ animationDelay: "240ms" }}
    >
      <div className="mb-6 flex items-center justify-between font-mono text-[11px] uppercase tracking-[0.2em] text-stone-500">
        <span>interview · waveform</span>
        <span className="flex items-center gap-1.5 text-sand/80">
          <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-sand" />
          reading
        </span>
      </div>

      <div className="relative flex h-24 items-center gap-[3px]">
        {/* marked moments */}
        {marks.map((m) => (
          <div
            key={m.label}
            aria-hidden
            className="absolute top-0 bottom-0 z-10 w-2 -translate-x-1/2"
            style={{ left: m.left }}
          >
            {/* line, dot, and label all centered on the same column (left-1/2) */}
            <div className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-sand/25" />
            {/* centered with -ml (not translate) so the pulse scale-animation
                doesn't override the centering transform and drift the dot */}
            <div className="absolute -top-1 left-1/2 -ml-1 h-2 w-2 animate-pulse-dot rounded-full bg-sand shadow-[0_0_12px_2px_rgba(203,180,145,0.4)]" />
            <div className="absolute -bottom-7 left-1/2 -translate-x-1/2 whitespace-nowrap font-mono text-[10px] text-sand/70">
              {m.label}
            </div>
          </div>
        ))}

        {/* the waveform */}
        {Array.from({ length: bars }).map((_, i) => (
          <span
            key={i}
            className="animate-bar flex-1 rounded-full bg-stone-100/[0.13]"
            style={{
              height: `${Math.round(barHeight(i, bars) * 100)}%`,
              animationDelay: `${(i % 9) * 0.1}s`,
              animationDuration: `${1.5 + (i % 5) * 0.2}s`,
            }}
          />
        ))}

        {/* soft passing light */}
        <div
          aria-hidden
          className="animate-sweep pointer-events-none absolute inset-y-0 z-0 w-2/5 bg-gradient-to-r from-transparent via-white/[0.05] to-transparent blur-md"
        />
      </div>
      <div className="h-6" />
    </div>
  );
}

/** Deterministic 0.18–1.0 waveform height — organic, no randomness. */
function barHeight(i: number, n: number): number {
  const a = Math.sin(i * 0.55 + 1.7);
  const b = Math.sin(i * 0.19 + 0.4);
  const env = Math.sin((i / n) * Math.PI); // taper at the edges
  const v = (a * 0.55 + b * 0.45 + 1) / 2;
  return 0.18 + 0.82 * v * (0.45 + 0.55 * env);
}
