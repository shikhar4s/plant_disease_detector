import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'react-hot-toast';
import { api, apiResponse, downloadBlob, messageOf } from '../../lib/api';
import type { Analysis, HistoryPage } from '../../lib/types';
import { usePlantData } from '../../contexts/PlantDataContext';
import { useAuth } from '../../contexts/AuthContext';
import ResultModal from './ResultModal';

export default function HistorySection() {
  const { t } = useTranslation();
  const { selectedImage, setSelectedImage } = usePlantData();
  const { reloadUser } = useAuth();
  const [data, setData] = useState<HistoryPage | null>(null);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('');
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState<Analysis | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [exporting, setExporting] = useState(false);
  const params = new URLSearchParams({ q: query, status: filter, page: String(page) }).toString();

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError('');
    api<HistoryPage>('/api/plant_doctor_ai/history/?' + params, { signal: controller.signal })
      .then(setData).catch(error => { if (!controller.signal.aborted) setError(messageOf(error)); })
      .finally(() => { if (!controller.signal.aborted) setIsLoading(false); });
    return () => controller.abort();
  }, [params, revision]);

  async function remove(item: Analysis) {
    if (!window.confirm(t('features.confirmDelete'))) return;
    setDeleting(item.id);
    try {
      await api('/api/plant_doctor_ai/history/' + item.id + '/', { method: 'DELETE' });
      if (selectedImage?.id === item.id) setSelectedImage(null);
      if (data?.results.length === 1 && page > 1) setPage(page - 1);
      else setRevision(value => value + 1);
      void reloadUser().catch(() => {});
      toast.success(t('features.deleted'));
    } catch (error) { toast.error(messageOf(error)); } finally { setDeleting(null); }
  }
  async function exportHistory() {
    setExporting(true);
    try {
      const response = await apiResponse('/api/plant_doctor_ai/history/export/?' + new URLSearchParams({ q: query, status: filter }));
      downloadBlob(await response.blob(), 'plantdoc-history.csv');
    } catch (error) { toast.error(messageOf(error)); } finally { setExporting(false); }
  }
  function update(item: Analysis) {
    setModal(item);
    setData(previous => previous ? { ...previous, results: previous.results.map(old => old.id === item.id ? item : old) } : previous);
    if (selectedImage?.id === item.id) setSelectedImage(item);
  }

  return <div className="max-w-6xl mx-auto">
    <div className="flex flex-wrap justify-between items-center gap-4 mb-7">
      <div><h1 className="text-3xl font-bold text-gray-800 mb-2">{t('dashboard.history.title')}</h1>
        <p className="text-gray-600">{t('dashboard.history.subtitle')}</p></div>
      <button onClick={() => void exportHistory()} disabled={exporting || !data?.count}
        className="border border-green-600 text-green-700 bg-white rounded-lg px-4 py-2 disabled:opacity-50">{t('features.exportCSV')}</button>
    </div>
    <form onSubmit={event => { event.preventDefault(); setQuery(search.trim()); setPage(1); }} className="flex flex-wrap gap-3 mb-6">
      <input aria-label={t('features.searchHistory')} value={search} onChange={event => setSearch(event.target.value)}
        placeholder={t('features.searchHistory')} className="flex-1 min-w-48 rounded-lg border p-3" maxLength={200} />
      <select aria-label={t('features.filterStatus')} value={filter} onChange={event => { setFilter(event.target.value); setPage(1); }}
        className="rounded-lg border p-3">
        <option value="">{t('features.allResults')}</option>
        {['healthy', 'possible_disease', 'uncertain'].map(status => <option key={status} value={status}>{t('features.' + status)}</option>)}
      </select>
      <button className="bg-green-600 text-white px-5 rounded-lg py-3">{t('features.search')}</button>
    </form>
    {isLoading ? <p role="status" className="p-8 text-center">{t('features.loading')}</p> :
      error ? <div role="alert" className="bg-red-50 p-6 rounded-xl"><p>{error}</p><button onClick={() => setRevision(value => value + 1)} className="mt-3 underline">{t('features.retry')}</button></div> :
      !data?.results.length ? <div className="bg-white/60 p-12 text-center rounded-xl"><h2 className="font-semibold text-lg">{t('features.noResults')}</h2>
        <p className="text-gray-600 mt-2">Upload a leaf photo or try a different search.</p></div> :
      <>
        <p className="text-sm text-gray-600 mb-4">{data.count} {t('features.savedResults')}</p>
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-5">
          {data.results.map(item => <article key={item.id} className="bg-white/80 rounded-xl overflow-hidden border">
            {item.image_url ? <img src={item.image_url} alt="Saved leaf analysis" loading="lazy" className="w-full h-40 object-contain bg-gray-50" /> :
              <div className="h-40 flex items-center justify-center bg-gray-100 text-gray-500">Preview unavailable</div>}
            <div className="p-5 space-y-3">
              <p className="text-xs text-gray-500">{new Date(item.created_at).toLocaleString()}</p>
              <h2 className="font-semibold text-gray-800">{item.disease}</h2>
              <p className="text-sm text-green-700">{t('features.' + item.prediction_status)} · {(item.confidence * 100).toFixed(1)}%</p>
              <div className="flex justify-between gap-3">
                <button onClick={() => { setModal(item); setSelectedImage(item); }} className="text-green-700 font-medium">{t('features.viewResult')}</button>
                <button onClick={() => void remove(item)} disabled={deleting !== null} className="text-red-600 disabled:opacity-50">{t('features.delete')}</button>
              </div>
            </div>
          </article>)}
        </div>
        <div className="flex justify-center items-center gap-5 my-7">
          <button disabled={!data.previous} onClick={() => setPage(value => value - 1)} className="border rounded-lg px-4 py-2 disabled:opacity-40">{t('features.previous')}</button>
          <span>{page} / {Math.max(1, Math.ceil(data.count / 12))}</span>
          <button disabled={!data.next} onClick={() => setPage(value => value + 1)} className="border rounded-lg px-4 py-2 disabled:opacity-40">{t('features.next')}</button>
        </div>
      </>}
    {modal && <ResultModal image={modal} isOpen onClose={() => setModal(null)} onUpdate={update} />}
  </div>;
}
