import React from 'react';
import UploadSection from './UploadSection';
import HistorySection from './HistorySection';
import AnalyticsSection from './AnalyticsSection';
import ProfileSection from './ProfileSection';
import ContactSection from './ContactSection';
import SupportedPlants from './SupportedPlants';

interface MainContentProps {
  activeTab: string;
}

const MainContent: React.FC<MainContentProps> = ({ activeTab }) => {
  const renderContent = () => {
    switch (activeTab) {
      case 'upload':
        return <UploadSection />;
      case 'history':
        return <HistorySection />;
      case 'analytics':
        return <AnalyticsSection />;
      case 'profile':
        return <ProfileSection />;
      case 'plants':
        return <SupportedPlants />;
      case 'contact':
        return <ContactSection />;
      default:
        return <UploadSection />;
    }
  };

  return (
    <div className="flex-1 min-w-0 p-4 md:p-8">
      {renderContent()}
    </div>
  );
};

export default MainContent;