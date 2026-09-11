import React from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { 
  CloudArrowUpIcon, 
  DocumentTextIcon, 
  ChartBarIcon,
  UserIcon,
  ArrowRightOnRectangleIcon,
  PhoneIcon
} from '@heroicons/react/24/outline';
import { Leaf } from 'lucide-react';
import LanguageSelector from '../common/LanguageSelector';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();

  const menuItems = [
    { id: 'upload', label: t('dashboard.sidebar.upload'), icon: CloudArrowUpIcon },
    { id: 'plants', label: t('features.supportedPlants'), icon: Leaf },
    { id: 'history', label: t('dashboard.sidebar.history'), icon: DocumentTextIcon },
    { id: 'analytics', label: t('dashboard.sidebar.analytics'), icon: ChartBarIcon },
    { id: 'profile', label: t('dashboard.sidebar.profile'), icon: UserIcon },
    { id: 'contact', label: t('dashboard.sidebar.contact'), icon: PhoneIcon },
  ];

  return (
    <div className="w-full md:w-64 md:shrink-0 bg-white/80 backdrop-blur-lg border-r border-white/20 md:min-h-screen flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-green-500 rounded-lg flex items-center justify-center">
            <Leaf className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-800">{t('app.title')}</h1>
            <p className="text-sm text-gray-600">AI Detection</p>
          </div>
        </div>
      </div>

      {/* User Info */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
            <UserIcon className="w-5 h-5 text-green-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-800">{user?.name}</p>
            <p className="text-xs text-gray-600">{user?.email}</p>
          </div>
        </div>
      </div>

      {/* Menu Items */}
      <nav className="flex-1 p-4">
        <ul className="flex md:block gap-2 overflow-x-auto md:space-y-2">
          {menuItems.map((item) => (
            <li key={item.id} className="shrink-0">
              <button
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                  activeTab === item.id
                    ? 'bg-green-100 text-green-700 border-2 border-green-200'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* Language Selector */}
      <div className="p-4 border-t border-gray-200">
        <LanguageSelector />
      </div>

      {/* Logout */}
      <div className="p-4 border-t border-gray-200">
        <button
          onClick={logout}
          className="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-red-600 hover:bg-red-50 transition-all duration-200"
        >
          <ArrowRightOnRectangleIcon className="w-5 h-5" />
          <span className="font-medium">{t('dashboard.sidebar.logout')}</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;