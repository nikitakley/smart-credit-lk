import { Navigate, Route, Routes } from 'react-router-dom';
import ClientLayout from './layouts/ClientLayout.jsx';
import AnalystLayout from './layouts/AnalystLayout.jsx';
import Login from './pages/client/Login.jsx';
import Assistant from './pages/client/Assistant.jsx';
import Catalog from './pages/client/Catalog.jsx';
import ApplicationWizard from './pages/client/ApplicationWizard.jsx';
import ApplicationStatus from './pages/client/ApplicationStatus.jsx';
import MyApplications from './pages/client/MyApplications.jsx';
import DecisionExplain from './pages/client/DecisionExplain.jsx';
import Offer from './pages/client/Offer.jsx';
import SignContract from './pages/client/SignContract.jsx';
import Queue from './pages/analyst/Queue.jsx';
import ApplicationCard from './pages/analyst/ApplicationCard.jsx';
import NotFound from './pages/NotFound.jsx';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/assistant" replace />} />
      <Route path="/login" element={<Login />} />

      {/* Клиент */}
      <Route element={<ClientLayout />}>
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/catalog" element={<Catalog />} />
        <Route path="/apply" element={<ApplicationWizard />} />
        <Route path="/applications" element={<MyApplications />} />
        <Route path="/applications/:id" element={<ApplicationStatus />} />
        <Route path="/applications/:id/decision" element={<DecisionExplain />} />
        <Route path="/applications/:id/offer" element={<Offer />} />
        <Route path="/applications/:id/sign" element={<SignContract />} />
      </Route>

      {/* Аналитик */}
      <Route path="/analyst" element={<AnalystLayout />}>
        <Route index element={<Queue />} />
        <Route path="applications/:id" element={<ApplicationCard />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
