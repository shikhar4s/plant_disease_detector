import { useTranslation } from 'react-i18next';
import { PhoneIcon, EnvelopeIcon } from '@heroicons/react/24/outline';

const ContactSection = () => {
  const { t } = useTranslation();

  const teamMembers = [
    {
      name: 'Shikhar Shrivastava',
      contact: '9340143366',
      role: 'B.Tech AIML',
      avatar: 'SS'
    },

  ];

  const getRandomColor = (index: number) => {
    const colors = [
      'bg-blue-500',
      'bg-green-500',
      'bg-purple-500',
      'bg-pink-500',
      'bg-indigo-500',
      'bg-yellow-500'
    ];
    return colors[index % colors.length];
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">{t('dashboard.contact.title')}</h1>
        <p className="text-gray-600">{t('dashboard.contact.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Team Members */}
        <div className="lg:col-span-2">
          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <h2 className="text-xl font-semibold text-gray-800 mb-6">{t('features.developer')}</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {teamMembers.map((member, index) => (
                <div key={member.name} className="bg-gradient-to-br from-white to-gray-50 rounded-lg p-6 border border-gray-200 hover:shadow-lg transition-all duration-200">
                  <div className="flex items-center space-x-4 mb-4">
                    <div className={`w-12 h-12 ${getRandomColor(index)} rounded-full flex items-center justify-center text-white font-bold text-lg`}>
                      {member.avatar}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-800">{member.name}</h3>
                      <p className="text-sm text-gray-600">{member.role}</p>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center space-x-3 text-gray-700">
                      <PhoneIcon className="w-4 h-4 text-green-600" />
                      <span className="text-sm">{t('dashboard.contact.contact')}: {member.contact}</span>
                    </div>
                  </div>
                  
                  <div className="mt-4 flex space-x-2">
                    <a
                      href={`tel:+91${member.contact}`}
                      className="flex-1 bg-green-500 text-white px-3 py-2 rounded-lg text-sm hover:bg-green-600 transition-colors duration-200 flex items-center justify-center space-x-1"
                    >
                      <PhoneIcon className="w-4 h-4" />
                      <span>{t('common.call')}</span>
                    </a>
                    <a
                      href={`sms:+91${member.contact}`}
                      className="flex-1 bg-blue-500 text-white px-3 py-2 rounded-lg text-sm hover:bg-blue-600 transition-colors duration-200 flex items-center justify-center space-x-1"
                    >
                      <EnvelopeIcon className="w-4 h-4" />
                      <span>{t('common.sms')}</span>
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Contact Info */}
        <div className="space-y-6">
          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">{t('dashboard.contact.getInTouch')}</h3>
            <p className="text-gray-600 mb-6">{t('dashboard.contact.getInTouchSubtext')}</p>
            
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                  <EnvelopeIcon className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Email</p>
                  <p className="text-sm font-medium text-gray-800">shikharshrivastava1980@gmail.com</p>
                </div>
              </div>
              
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <PhoneIcon className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Support</p>
                  <p className="text-sm font-medium text-gray-800">+91 9340143366</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-green-50 to-emerald-100 rounded-xl p-6 border border-green-200">
            <h3 className="text-lg font-semibold text-green-800 mb-3">About PlantDoc</h3>
            <p className="text-green-700 text-sm leading-relaxed">
              PlantDoc is an AI-powered plant disease detection system maintained by Shikhar Shrivastava. 
              The aim is to help farmers and gardeners identify plant diseases early and provide effective treatment solutions.
            </p>
          </div>

          <div className="bg-gradient-to-br from-blue-50 to-indigo-100 rounded-xl p-6 border border-blue-200">
            <h3 className="text-lg font-semibold text-blue-800 mb-3">Project Info</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-blue-600">Version:</span>
                <span className="text-blue-800 font-medium">1.0.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-blue-600">Technology:</span>
                <span className="text-blue-800 font-medium">React + AI + Django</span>
              </div>
              <div className="flex justify-between">
                <span className="text-blue-600">Status:</span>
                <span className="text-blue-800 font-medium">Active</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContactSection;
