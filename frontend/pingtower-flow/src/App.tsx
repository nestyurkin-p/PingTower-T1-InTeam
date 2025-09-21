import { useState } from "react";

import AppNavigation, { type AppView } from "./components/AppNavigation";
import DashboardPage from "./pages/DashboardPage";
import FlowWorkspace from "./pages/FlowWorkspace";

export default function App() {
  const [activeView, setActiveView] = useState<AppView>("dashboard");

  return (
    <div className="flex h-screen w-screen flex-col bg-slate-100 text-slate-900">
      <AppNavigation activeView={activeView} onChange={setActiveView} />
      <main className="flex flex-1 overflow-hidden">
        {activeView === "dashboard" ? <DashboardPage /> : <FlowWorkspace />}
      </main>
    </div>
  );
}
