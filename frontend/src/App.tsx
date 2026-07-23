import { Navigate, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import ProgressStrip from "./components/ProgressStrip";
import { JobsProvider } from "./context/JobsContext";
import Campaigns from "./pages/Campaigns";
import Leads from "./pages/Leads";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <JobsProvider>
      <div className="min-h-screen bg-white text-gray-900">
        <NavBar />
        <ProgressStrip />
        <Routes>
          <Route path="/" element={<Navigate to="/campaigns" replace />} />
          <Route path="/campaigns" element={<Campaigns />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/campaigns/:campaignId/leads" element={<Leads />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </JobsProvider>
  );
}
