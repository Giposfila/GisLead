import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import NavBar from "./components/NavBar";
import ProgressStrip from "./components/ProgressStrip";
import { JobsProvider } from "./context/JobsContext";
import Campaigns from "./pages/Campaigns";
import Leads from "./pages/Leads";
import Settings from "./pages/Settings";
import Guide from "./pages/Guide";
import { ru } from "./i18n/ru";

export default function App() {
  const { pathname } = useLocation();
  return (
    <JobsProvider>
      <div className="app-shell">
        <a href="#main" className="skip-link">
          {ru.app.skip}
        </a>
        <NavBar />
        <main id="main" className="main-content">
          <ProgressStrip />
          <div className="route-view" key={pathname}>
            <Routes>
              <Route path="/" element={<Navigate to="/campaigns" replace />} />
              <Route path="/campaigns" element={<Campaigns />} />
              <Route path="/leads" element={<Leads />} />
              <Route path="/campaigns/:campaignId/leads" element={<Leads />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/guide" element={<Guide />} />
              <Route path="*" element={<Navigate to="/campaigns" replace />} />
            </Routes>
          </div>
          <footer className="workspace-footer">
            <span>
              LeadGis
              <span className="footer-star" aria-hidden="true">
                ✳
              </span>
              {ru.app.footer}
            </span>
            <span>
              <span className="status-dot" />
              {ru.app.local}
            </span>
          </footer>
        </main>
      </div>
    </JobsProvider>
  );
}
