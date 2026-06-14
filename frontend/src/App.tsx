import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Nav from "./components/Nav";
import { api } from "./api/client";
import Setup from "./screens/Setup";
import Reception from "./screens/Reception";
import PerformanceReviews from "./screens/PerformanceReviews";
import Knowledge from "./screens/Knowledge";

export default function App() {
  const [demo, setDemo] = useState(false);
  const [seeded, setSeeded] = useState<boolean | null>(null);
  const location = useLocation();

  const refresh = () => {
    api.status().then((s) => {
      setDemo(s.demo_mode);
      setSeeded(s.db_seeded);
    });
  };

  useEffect(refresh, []);

  // While we don't yet know seed state, render nothing (avoids a redirect flicker).
  if (seeded === null) {
    return (
      <div className="app">
        <Nav demo={demo} />
        <div className="container">Loading the office…</div>
      </div>
    );
  }

  const needsSetup = !seeded && location.pathname !== "/setup";

  return (
    <div className="app">
      <Nav demo={demo} />
      {needsSetup && <Navigate to="/setup" replace />}
      <Routes>
        <Route path="/setup" element={<Setup onSeeded={refresh} />} />
        <Route path="/" element={<Reception />} />
        <Route path="/reviews" element={<PerformanceReviews />} />
        <Route path="/knowledge" element={<Knowledge />} />
      </Routes>
    </div>
  );
}
