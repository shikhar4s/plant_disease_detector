import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../lib/api';
import type { HistoryPage } from '../../lib/types';
import { CloudArrowUpIcon, CloudIcon, CurrencyRupeeIcon, ClockIcon, StarIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';

interface WatchItem { id: number; commodity: string; state: string; latest: null | { modal_price: number; unit: string; market: string; price_date: string } }

export default function HomePage({ navigate }: { navigate: (tab: string) => void }) {
  const { t } = useTranslation();
  const [history, setHistory] = useState<HistoryPage | null>(null); const [watchlist, setWatchlist] = useState<WatchItem[]>([]);
  useEffect(() => { const controller = new AbortController(); Promise.all([
    api<HistoryPage>('/api/plant_doctor_ai/history/?page_size=5', { signal: controller.signal }),
    api<WatchItem[]>('/api/plant_doctor_ai/watchlist/', { signal: controller.signal }),
  ]).then(([h, w]) => { setHistory(h); setWatchlist(w); }).catch(() => {}); return () => controller.abort(); }, []);
  const cards = [
    ['diagnose', t('features.diagnosePlant'), t('features.diagnoseCard'), CloudArrowUpIcon],
    ['weather', t('features.weather'), t('features.weatherCard'), CloudIcon],
    ['weather', t('features.diseaseRisk'), t('features.riskCard'), ClockIcon],
    ['mandi', t('features.mandiUpdates'), t('features.mandiCard'), CurrencyRupeeIcon],
    ['history', t('features.recentDiagnoses'), `${history?.count || 0} ${t('features.savedResults')}`, ClockIcon],
    ['mandi', t('features.commodityWatchlist'), `${watchlist.length} ${t('features.watched')}`, StarIcon],
    ['assistant', t('features.askPlantdoc'), t('features.assistantCard'), ChatBubbleLeftRightIcon],
  ] as const;
  return <div className="max-w-7xl mx-auto space-y-8"><header className="hero-panel"><p className="eyebrow text-green-200">PLANTDOC</p>
    <h1 className="text-3xl md:text-5xl font-bold max-w-3xl">{t('features.platformTitle')}</h1><p className="mt-3 text-green-100 max-w-2xl">{t('features.platformSubtitle')}</p>
    <button onClick={() => navigate('diagnose')} className="mt-6 bg-amber-400 text-green-950 px-5 py-3 rounded-lg font-bold">{t('features.diagnosePlant')}</button></header>
    <section><h2 className="section-title mb-4">{t('features.farmOverview')}</h2><div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map(([tab,title,description,Icon]) => <button key={title} onClick={() => navigate(tab)} className="panel text-left hover:border-green-400 focus-visible:ring-2 focus-visible:ring-green-600">
        <Icon className="w-8 h-8 text-green-700" /><h3 className="font-bold text-lg mt-4">{title}</h3><p className="text-sm text-gray-600 mt-1">{description}</p></button>)}</div></section>
    <div className="grid lg:grid-cols-2 gap-6"><section className="panel"><h2 className="section-title">{t('features.recentDiagnoses')}</h2>
      {!history?.results.length ? <p className="empty-state">{t('features.noResults')}</p> : <ul className="divide-y mt-3">{history.results.map(item => <li key={item.id} className="py-3 flex justify-between gap-3"><span><strong>{item.crop_name}</strong><br/><span className="text-sm text-gray-600">{item.condition_name}</span></span><span className="text-sm">{(item.confidence * 100).toFixed(1)}%</span></li>)}</ul>}</section>
      <section className="panel"><h2 className="section-title">{t('features.commodityWatchlist')}</h2>{!watchlist.length ? <p className="empty-state">{t('features.watchlistEmpty')}</p> : <ul className="divide-y mt-3">{watchlist.map(item => <li key={item.id} className="py-3 flex justify-between gap-3"><span><strong>{item.commodity}</strong><br/><span className="text-sm text-gray-600">{item.state || t('features.allStates')}</span></span><span className="text-right text-sm">{item.latest ? `₹${item.latest.modal_price} / quintal` : t('features.collectingHistory')}</span></li>)}</ul>}</section></div>
  </div>;
}
