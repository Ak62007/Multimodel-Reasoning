import { useEffect, useState } from "react";
import UploadScreen from "./screens/UploadScreen";
import AnalyzingScreen from "./screens/AnalyzingScreen";
import ReportScreen from "./screens/ReportScreen";
import { getActiveJobId, setActiveJobId } from "./lib/storage";

type Mode = "upload" | "analyzing" | "report";

export default function App() {
  const [mode, setMode] = useState<Mode>("upload");
  const [jobId, setJobId] = useState<string | null>(null);

  // Resume active job from localStorage on first load.
  useEffect(() => {
    const stored = getActiveJobId();
    if (stored) {
      setJobId(stored);
      setMode("analyzing");
    }
  }, []);

  function startAnalyzing(newJobId: string) {
    setActiveJobId(newJobId);
    setJobId(newJobId);
    setMode("analyzing");
  }

  function showReport(reportJobId: string) {
    setJobId(reportJobId);
    setMode("report");
  }

  function reset() {
    setActiveJobId(null);
    setJobId(null);
    setMode("upload");
  }

  if (mode === "upload") {
    return <UploadScreen onJobCreated={startAnalyzing} onViewRecent={showReport} />;
  }
  if (mode === "analyzing" && jobId) {
    return (
      <AnalyzingScreen
        jobId={jobId}
        onSucceeded={() => setMode("report")}
        onFailed={() => setMode("report")}
        onCancel={reset}
      />
    );
  }
  if (mode === "report" && jobId) {
    return <ReportScreen jobId={jobId} onNewAnalysis={reset} />;
  }
  return <UploadScreen onJobCreated={startAnalyzing} onViewRecent={showReport} />;
}
