import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { SettingsProvider } from "./lib/settings.tsx";
import { Shell } from "./ui/Shell.tsx";
import { Overview } from "./pages/Overview.tsx";
import { Traffic } from "./pages/Traffic.tsx";
import { FunnelPage } from "./pages/FunnelPage.tsx";
import { Clients } from "./pages/Clients.tsx";
import { ClientDetailPage } from "./pages/ClientDetailPage.tsx";
import { Writes } from "./pages/Writes.tsx";
import { Events } from "./pages/Events.tsx";
import { InterventionsPage } from "./pages/InterventionsPage.tsx";
import { System } from "./pages/System.tsx";
import { Glossary } from "./pages/Glossary.tsx";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <SettingsProvider>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<Overview />} />
            <Route path="traffic" element={<Traffic />} />
            <Route path="funnel" element={<FunnelPage />} />
            <Route path="clients" element={<Clients />} />
            <Route path="clients/:id" element={<ClientDetailPage />} />
            <Route path="writes" element={<Writes />} />
            <Route path="events" element={<Events />} />
            <Route path="interventions" element={<InterventionsPage />} />
            <Route path="system" element={<System />} />
            <Route path="glossary" element={<Glossary />} />
            <Route path="*" element={<p className="empty">no such page</p>} />
          </Route>
        </Routes>
      </SettingsProvider>
    </BrowserRouter>
  </StrictMode>,
);
