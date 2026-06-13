import { Route, Routes } from "react-router-dom";

import IntroScreen from "./screens/IntroScreen";
import UploadScreen from "./screens/UploadScreen";
import AnalyzingScreen from "./screens/AnalyzingScreen";
import ReportScreen from "./screens/ReportScreen";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<IntroScreen />} />
      <Route path="/upload" element={<UploadScreen />} />
      <Route path="/analyzing/:id" element={<AnalyzingScreen />} />
      <Route path="/report/:id" element={<ReportScreen />} />
    </Routes>
  );
}
