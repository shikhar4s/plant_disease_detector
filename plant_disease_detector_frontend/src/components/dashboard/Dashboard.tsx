import { useLocation, useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import MainContent from './MainContent';

const Dashboard = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = location.pathname.split('/')[2] || 'home';
  const setActiveTab = (tab: string) => navigate('/dashboard/' + (tab === 'home' ? '' : tab));

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100">
      <div className="flex flex-col md:flex-row">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <MainContent activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
    </div>
  );
};

export default Dashboard;
