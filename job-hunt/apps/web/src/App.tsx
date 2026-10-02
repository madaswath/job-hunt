import { Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "./layout/Shell";
import { DashboardPage } from "./pages/DashboardPage";
import { DiscoverPage } from "./pages/DiscoverPage";
import { InboxPage } from "./pages/InboxPage";
import { ApplicationsPage } from "./pages/ApplicationsPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { AgentsPage } from "./pages/AgentsPage";
import { SourcesPage } from "./pages/SourcesPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SignInPage } from "./pages/SignInPage";
import { RequireAuth } from "./layout/RequireAuth";

export default function App() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignInPage />} />
      <Route
        element={
          <RequireAuth>
            <Shell />
          </RequireAuth>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/discover" element={<DiscoverPage />} />
        <Route path="/inbox" element={<InboxPage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/sources" element={<SourcesPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<ProfilePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
