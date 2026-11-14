import { Navigate, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import ProgressStrip from "./components/ProgressStrip";
import { JobsProvider } from "./context/JobsContext";
import Campaigns from "./pages/Campaigns";
import Leads from "./pages/Leads";
import Settings from "./pages/Settings";
import Guide from "./pages/Guide";
import { ru } from "./i18n/ru";

export default function App() {
  return (
    <JobsProvider>
      <div className="app-shell">
        <a href="#main" className="skip-link">
          {ru.app.skip}
        </a>
        <NavBar />
        <main id="main" className="main-content">
          <ProgressStrip />
          <Routes>
            <Route path="/" element={<Navigate to="/campaigns" replace />} />
            <Route path="/campaigns" element={<Campaigns />} />
            <Route path="/leads" element={<Leads />} />
            <Route path="/campaigns/:campaignId/leads" element={<Leads />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/guide" element={<Guide />} />
            <Route path="*" element={<Navigate to="/campaigns" replace />} />
          </Routes>
        </main>
      </div>
    </JobsProvider>
  );
}
