import React, { lazy, Suspense } from 'react';
import UploadSection from './UploadSection';
import HistorySection from './HistorySection';
import ProfileSection from './ProfileSection';
import HomePage from './HomePage';
import AboutPage from './AboutPage';
import Chatbot from './Chatbot';
const MandiRates = lazy(() => import('./MandiRates'));
const WeatherPage = lazy(() => import('./WeatherPage'));

interface MainContentProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const MainContent: React.FC<MainContentProps> = ({ activeTab, setActiveTab }) => {
  const renderContent = () => {
    switch (activeTab) {
      case 'home':
        return <HomePage navigate={setActiveTab} />;
      case 'diagnose':
        return <UploadSection />;
      case 'mandi':
        return <MandiRates />;
      case 'weather':
        return <WeatherPage />;
      case 'history':
        return <HistorySection />;
      case 'assistant':
        return null;
      case 'profile':
        return <ProfileSection />;
      case 'about':
        return <AboutPage />;
      default:
        return <HomePage navigate={setActiveTab} />;
    }
  };

  return (
    <div className="flex-1 min-w-0 p-4 pb-24 md:p-8 md:pb-24">
      <Suspense fallback={<p role="status" className="panel">Loading…</p>}>{renderContent()}</Suspense>
      <Chatbot embedded={activeTab === 'assistant'} />
    </div>
  );
};

export default MainContent;

