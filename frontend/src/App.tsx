import { Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import AuditResults from "./pages/AuditResults";
import Dashboard from "./pages/Dashboard";
import Evaluation from "./pages/Evaluation";
import History from "./pages/History";
import Landing from "./pages/Landing";
import NewAudit from "./pages/NewAudit";
import NotFound from "./pages/NotFound";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/audits/new" element={<NewAudit />} />
        <Route path="/audits" element={<History />} />
        <Route path="/audits/:id" element={<AuditResults />} />
        <Route path="/evaluation" element={<Evaluation />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/methodology" element={<Settings />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
