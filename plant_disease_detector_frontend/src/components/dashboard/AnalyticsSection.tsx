import { api, messageOf } from '../../lib/api';
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ChartBarIcon, EyeIcon, CheckCircleIcon, ExclamationTriangleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';

const ANALYTICS_API_ENDPOINT = '/api/plant_doctor_ai/analytics/';

// --- TypeScript Interfaces for API Response ---
interface AnalyticsSummary {
  totalUploads: number;
  analyzed: number;
  successRate: number;
  avgConfidence: number;
}

interface DistributionItem {
  name: string;
  value: number;
}

interface AnalyticsData {
  summary: AnalyticsSummary;
  diseaseDistribution: DistributionItem[];
  statusDistribution: DistributionItem[];
}

const AnalyticsSkeleton = () => (
  <div className="space-y-8 animate-pulse">
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="bg-gray-200/50 rounded-xl h-24"></div>
      ))}
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div className="bg-gray-200/50 rounded-xl h-48"></div>
      <div className="bg-gray-200/50 rounded-xl h-48"></div>
    </div>
  </div>
);


const AnalyticsSection = () => {
  const { t } = useTranslation();
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setIsLoading(true);
        const data: AnalyticsData = await api<AnalyticsData>(ANALYTICS_API_ENDPOINT);
        setAnalyticsData(data);
        setError(null);
      } catch (err: unknown) {
        console.error("Failed to fetch analytics data:", err);
        setError(messageOf(err));
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalytics();
  }, [t]); 
  
  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">{t('dashboard.analytics.title')}</h1>
          <p className="text-gray-600">{t('dashboard.analytics.subtitle')}</p>
        </div>
        <AnalyticsSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto text-center py-12">
        <ExclamationCircleIcon className="w-16 h-16 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-red-600 mb-2">{t('dashboard.analytics.error.title')}</h3>
        <p className="text-gray-500">{error}</p>
      </div>
    );
  }

  if (!analyticsData || analyticsData.summary.totalUploads === 0) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">{t('dashboard.analytics.title')}</h1>
          <p className="text-gray-600">{t('dashboard.analytics.subtitle')}</p>
        </div>
        <div className="bg-white/50 backdrop-blur-sm rounded-xl p-12 border border-white/20 text-center">
          <ChartBarIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-600 mb-2">{t('dashboard.analytics.noData')}</h3>
          <p className="text-gray-500">{t('dashboard.analytics.noDataSubtext')}</p>
        </div>
      </div>
    );
  }
  
  const { summary, diseaseDistribution, statusDistribution } = analyticsData;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">{t('dashboard.analytics.title')}</h1>
        <p className="text-gray-600">{t('dashboard.analytics.subtitle')}</p>
      </div>

      <div className="space-y-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{t('dashboard.analytics.totalUploads')}</p>
                <p className="text-2xl font-bold text-gray-800">{summary.totalUploads}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <EyeIcon className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{t('dashboard.analytics.analyzed')}</p>
                <p className="text-2xl font-bold text-gray-800">{summary.analyzed}</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <CheckCircleIcon className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{t('features.completionRate')}</p>
                <p className="text-2xl font-bold text-gray-800">{summary.successRate}%</p>
              </div>
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                <ChartBarIcon className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{t('dashboard.analytics.avgConfidence')}</p>
                <p className="text-2xl font-bold text-gray-800">{summary.avgConfidence}%</p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                <ExclamationTriangleIcon className="w-6 h-6 text-orange-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Disease Distribution */}
          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">{t('dashboard.analytics.diseaseDistribution')}</h3>
            <div className="space-y-3">
              {diseaseDistribution.map((item) => (
                <div key={item.name} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 truncate pr-4">{item.name}</span>
                  <div className="flex items-center space-x-2 flex-shrink-0">
                    <div className="w-32 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-green-500 h-2 rounded-full" 
                        style={{ width: `${(item.value / Math.max(1, summary.analyzed)) * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium text-gray-800 w-8 text-right">{item.value}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Severity Distribution */}
          <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">{t('features.statusDistribution')}</h3>
            <div className="space-y-3">
              {statusDistribution.map((item) => {
                const color = item.name === 'healthy' ? 'bg-green-500' : 
                              item.name === 'uncertain' ? 'bg-yellow-500' : 'bg-red-500';
                return (
                  <div key={item.name} className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">{t('features.' + item.name)}</span>
                    <div className="flex items-center space-x-2 flex-shrink-0">
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div 
                          className={`${color} h-2 rounded-full`}
                          style={{ width: `${(item.value / Math.max(1, summary.analyzed)) * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-sm font-medium text-gray-800 w-8 text-right">{item.value}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsSection;