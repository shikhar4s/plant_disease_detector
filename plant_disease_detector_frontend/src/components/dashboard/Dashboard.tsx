import { useState } from 'react';
import Sidebar from './Sidebar';
import MainContent from './MainContent';
import Chatbot from './Chatbot';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('upload');

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100">
      <div className="flex flex-col md:flex-row">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <MainContent activeTab={activeTab} />
      </div>
      <Chatbot />
    </div>
  );
};

export default Dashboard;