import { Routes, Route, Navigate } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import ProjectDetail from "./components/ProjectDetail";
import NotFound from "./pages/NotFound";
import "./App.css";

export default function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects/:projectId" element={<ProjectDetail />} />
        <Route path="/404" element={<NotFound />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </div>
  );
}
