import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'react-hot-toast';
import { api, messageOf } from '../../lib/api';
import type { CommodityImage as CommodityImageData, CommodityImagesResponse, MandiHistory, MandiRecord, MandiResponse } from '../../lib/types';
import { usePlantData } from '../../contexts/PlantDataContext';

const empty = { q: '', state: '', district: '', market: '', commodity: '', variety: '', date: '', sort: 'newest' };

function CommodityImage({ commodity, image, compact = false }: { commodity: string; image?: CommodityImageData | null; compact?: boolean }) {
  const className = compact ? 'commodity-image commodity-image-compact' : 'commodity-image';
  if (image?.url) return <a href={image.source_url} target="_blank" rel="noreferrer" className={compact ? 'commodity-image-link commodity-image-link-compact' : 'commodity-image-link'} aria-label={`${commodity} image source: ${image.title}`} title={`${image.title} · ${image.license}`}>
    <img src={image.url} alt={`${commodity} from Wikimedia Commons`} className={className} loading="lazy" /><span className="commodity-image-credit">Wikimedia</span>
  </a>;
  return <div className={`${className} commodity-image-fallback`} role="img" aria-label={`${commodity} image unavailable`}>
    {commodity.trim().charAt(0).toLocaleUpperCase('en-IN') || '•'}
  </div>;
}

export default function MandiRates() {
  const { t } = useTranslation();
  const { setMandiContextId } = usePlantData();
  const [form, setForm] = useState(empty);
  const [filters, setFilters] = useState(empty);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<MandiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [trendFor, setTrendFor] = useState<MandiRecord | null>(null);
  const [trendDays, setTrendDays] = useState(30);
  const [trend, setTrend] = useState<MandiHistory | null>(null);
  const [commodityImages, setCommodityImages] = useState<Record<string, CommodityImageData | null>>({});
  const query = new URLSearchParams({ ...filters, page: String(page), page_size: '20' }).toString();

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    api<MandiResponse>('/api/plant_doctor_ai/mandi/?' + query, { signal: controller.signal })
      .then(result => { setData(result); setMandiContextId(result.context_id); })
      .catch(error => { if (!controller.signal.aborted) setError(messageOf(error)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query, setMandiContextId]);

  useEffect(() => {
    if (!data?.results.length) return;
    const commodities = Array.from(new Set(data.results.map(row => row.commodity)));
    const controller = new AbortController();
    api<CommodityImagesResponse>('/api/plant_doctor_ai/commodity-images/?commodities=' + encodeURIComponent(commodities.join(',')), { signal: controller.signal })
      .then(result => setCommodityImages(previous => ({ ...previous, ...result.images })))
      .catch(() => undefined);
    return () => controller.abort();
  }, [data?.results]);

  useEffect(() => {
    if (!trendFor) return;
    const controller = new AbortController();
    const params = new URLSearchParams({ commodity: trendFor.commodity, variety: trendFor.variety,
      market: trendFor.market, district: trendFor.district, state: trendFor.state, days: String(trendDays) });
    api<MandiHistory>('/api/plant_doctor_ai/mandi/history/?' + params, { signal: controller.signal })
      .then(setTrend).catch(error => { if (!controller.signal.aborted) setError(messageOf(error)); });
    return () => controller.abort();
  }, [trendFor, trendDays]);

  async function watch() {
    if (!filters.commodity) { toast.error(t('features.chooseCommodity')); return; }
    try {
      await api('/api/plant_doctor_ai/watchlist/', { method: 'POST', body: JSON.stringify({
        commodity: filters.commodity, state: filters.state, district: filters.district, market: filters.market,
      }) });
      toast.success(t('features.watchlistSaved'));
    } catch (error) { toast.error(messageOf(error)); }
  }

  const money = (value: number | null) => value == null ? '—' : new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(value);
  const perKg = (value: number | null, unit: string) => value == null || !unit.toLowerCase().includes('quintal') ? '—' : money(value / 100);
  return <div className="max-w-7xl mx-auto space-y-6">
    <header><p className="eyebrow">{t('features.marketIntelligence')}</p><h1 className="page-title">{t('features.mandiRates')}</h1>
      <p className="page-subtitle">{t('features.mandiSubtitle')}</p></header>
    <form onSubmit={event => { event.preventDefault(); setFilters(form); setPage(1); }} className="panel grid sm:grid-cols-2 xl:grid-cols-4 gap-3">
      {(['q','state','district','market','commodity','variety'] as const).map(key => <label key={key} className="field-label">
        {t('features.' + key)}<input value={form[key]} onChange={event => setForm({ ...form, [key]: event.target.value })}
          placeholder={t('features.' + key)} className="field" maxLength={160} /></label>)}
      <label className="field-label">{t('features.date')}<input type="date" value={form.date} onChange={event => setForm({ ...form, date: event.target.value })} className="field" /></label>
      <label className="field-label">{t('features.sort')}<select value={form.sort} onChange={event => setForm({ ...form, sort: event.target.value })} className="field">
        {['newest','highest','lowest','alphabetical'].map(value => <option key={value} value={value}>{t('features.' + value)}</option>)}</select></label>
      <div className="sm:col-span-2 xl:col-span-4 flex flex-wrap gap-3"><button className="primary-button">{t('features.applyFilters')}</button>
        <button type="button" onClick={() => { setForm(empty); setFilters(empty); setPage(1); }} className="secondary-button">{t('features.clear')}</button>
        <button type="button" onClick={() => void watch()} className="secondary-button">{t('features.addWatchlist')}</button></div>
    </form>
    {data?.comparison && <section className="panel border-l-4 border-l-amber-500">
      <p className="eyebrow">{t('features.highestComparable')}</p>
      <div className="flex flex-wrap items-end justify-between gap-4"><div className="flex items-center gap-4"><CommodityImage commodity={data.comparison.highest.commodity} image={commodityImages[data.comparison.highest.commodity]} compact /><div>
        <h2 className="text-2xl font-bold">₹{money(data.comparison.highest.modal_price)} / {t('features.quintal')}</h2>
        <p className="font-semibold text-green-800">₹{perKg(data.comparison.highest.modal_price, data.comparison.highest.unit)} / {t('features.kg')}</p>
        <p>{data.comparison.highest.market}, {data.comparison.highest.district}, {data.comparison.highest.state}</p>
        <p className="text-sm text-gray-600">{data.comparison.highest.commodity} · {data.comparison.highest.variety} · {data.comparison.highest.price_date}</p></div></div>
        <p className="max-w-xl text-sm text-gray-600">{data.comparison.scope} ({data.comparison.record_count} records compared.)</p></div>
    </section>}
    {loading ? <div className="panel" role="status">{t('features.loading')}</div> : error ? <div className="error-panel" role="alert"><strong>{t('features.providerError')}</strong><p>{error}</p></div> :
      !data?.results.length ? <div className="panel empty-state">{t('features.noMarketRecords')}</div> : <section aria-label={t('features.mandiRates')}>
        <div className="mandi-card-grid">{data.results.map((row, index) => <article className="mandi-price-card" key={`${row.market}-${row.commodity}-${row.variety}-${row.price_date}-${index}`}>
          <div className="flex gap-4"><CommodityImage commodity={row.commodity} image={commodityImages[row.commodity]} /><div className="min-w-0 flex-1">
            <p className="eyebrow">{row.variety}</p><h2 className="section-title break-words">{row.commodity}</h2>
            <p className="mt-1 text-sm font-semibold text-green-800">{row.market}</p>
            <p className="text-sm text-gray-600">{row.district}, {row.state}</p><p className="mt-1 text-xs text-gray-500">{row.price_date}</p>
          </div></div>
          <div className="mandi-price-grid">
            {([['min', row.min_price], ['modal', row.modal_price], ['max', row.max_price]] as const).map(([label, value]) => <div className={label === 'modal' ? 'mandi-price-box mandi-price-box-modal' : 'mandi-price-box'} key={label}>
              <p className="text-xs font-bold uppercase tracking-wide text-gray-500">{t('features.' + label)}</p>
              <p className="mt-1 text-lg font-bold">₹{money(value)} <span className="text-xs font-medium">/ {t('features.quintal')}</span></p>
              <p className="text-sm text-green-800">₹{perKg(value, row.unit)} / {t('features.kg')}</p>
            </div>)}
          </div>
          <div className="flex items-center justify-between gap-3 border-t border-green-950/10 pt-3"><p className="text-xs text-gray-500">{t('features.regionPrice')}</p>
            <button type="button" onClick={() => setTrendFor(row)} className="text-sm font-semibold text-green-700 underline">{t('features.viewTrend')}</button></div>
        </article>)}</div>
        <p className="mt-3 text-xs text-gray-600">{t('features.kgConversionNote')}</p>
      </section>}
    {data && <footer className="flex flex-wrap justify-between gap-4 text-sm text-gray-600">
      <div><p>{data.source.name} · fetched {new Date(data.fetched_at).toLocaleString()} {data.cached ? '· cached' : ''}</p>
        {!data.coverage.complete && <p className="text-amber-700">{t('features.partialCoverage')} {data.coverage.fetched_limit} / {data.coverage.provider_total}</p>}</div>
      <div className="flex items-center gap-3"><button disabled={!data.previous} onClick={() => setPage(value => value - 1)} className="secondary-button">{t('features.previous')}</button>
        <span>{page}</span><button disabled={!data.next} onClick={() => setPage(value => value + 1)} className="secondary-button">{t('features.next')}</button></div></footer>}
    <section className="panel"><div className="flex flex-wrap justify-between gap-3"><div><h2 className="section-title">{t('features.priceTrends')}</h2>
      {trendFor && <p className="text-sm text-gray-600">{trendFor.commodity} · {trendFor.variety} · {trendFor.market}</p>}</div>
      <div className="flex gap-2">{[7,30,90].map(days => <button type="button" key={days} onClick={() => setTrendDays(days)} className={days === trendDays ? 'primary-button' : 'secondary-button'}>{days}d</button>)}</div></div>
      {!trendFor ? <p className="mt-4">{t('features.historyUnavailable')}</p> : trend?.status === 'available' && trend.points.length >= 2 ? <div className="mt-4">
        <svg role="img" aria-label={t('features.priceTrends')} viewBox="0 0 600 180" className="w-full h-44 border rounded-lg bg-green-50">
          <polyline fill="none" stroke="currentColor" strokeWidth="4" className="text-green-700" points={trend.points.map((point, index) => {
            const values = trend.points.map(item => item.modal_price); const min = Math.min(...values); const max = Math.max(...values);
            const x = trend.points.length === 1 ? 300 : index * 580 / (trend.points.length - 1) + 10;
            const y = max === min ? 90 : 160 - (point.modal_price - min) * 140 / (max - min); return `${x},${y}`;
          }).join(' ')} /></svg>
        <p className="mt-2 font-semibold">{t('features.priceChange')}: {trend.percentage_change == null ? '—' : `${trend.percentage_change}%`}</p><p className="text-xs text-gray-600">{trend.scope}</p></div> :
        <p className="mt-4">{trend?.message || t('features.collectingHistory')}</p>}
      <p className="text-sm text-gray-600 mt-2">{t('features.historyHonesty')}</p></section>
  </div>;
}

