import type { ReactElement } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { getStoredToken } from '@/lib/api';
import LoginPage from '@/pages/LoginPage';
import HomePage from '@/pages/HomePage';
import HistoryPage from '@/pages/HistoryPage';
import SimulationPage from '@/pages/SimulationPage';
import DebriefPage from '@/pages/DebriefPage';

function RequireAuth({ children }: { children: ReactElement }) {
  return getStoredToken() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <HomePage />
          </RequireAuth>
        }
      />
      <Route
        path="/history"
        element={
          <RequireAuth>
            <HistoryPage />
          </RequireAuth>
        }
      />
      <Route
        path="/simulation/:sessionId"
        element={
          <RequireAuth>
            <SimulationPage />
          </RequireAuth>
        }
      />
      <Route
        path="/debrief/:sessionId"
        element={
          <RequireAuth>
            <DebriefPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
