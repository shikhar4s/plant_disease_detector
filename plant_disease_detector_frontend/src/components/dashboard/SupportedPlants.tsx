import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, messageOf } from '../../lib/api';

interface Catalogue { classCount: number; plants: { name: string; conditions: string[] }[] }

export default function SupportedPlants() {
  const { t } = useTranslation();
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    api<Catalogue>('/api/plant_doctor_ai/plants/', { signal: controller.signal }).then(setCatalogue)
      .catch(error => { if (!controller.signal.aborted) setError(messageOf(error)); });
    return () => controller.abort();
  }, [retry]);
  const plants = catalogue?.plants.filter(plant => (plant.name + ' ' + plant.conditions.join(' ')).toLowerCase().includes(query.toLowerCase())) || [];
  return <div className="max-w-5xl mx-auto">
    <h1 className="text-3xl font-bold text-gray-800 mb-3">{t('features.supportedPlants')}</h1>
    <p className="text-gray-600 mb-6">{catalogue ? catalogue.plants.length + ' plants · ' + catalogue.classCount + ' trained classes' : t('features.loading')}</p>
    <p className="bg-amber-50 border border-amber-200 rounded-xl p-5 mb-6 text-amber-900">
      Upload leaves from the plants below. The model can only choose among these classes; its score does not validate the image or rule out other diseases.
    </p>
    <input aria-label={t('features.searchPlants')} placeholder={t('features.searchPlants')} value={query}
      onChange={event => setQuery(event.target.value)} className="w-full border rounded-lg p-3 mb-6" />
    {error ? <div role="alert"><p>{error}</p><button onClick={() => setRetry(value => value + 1)} className="underline mt-2">{t('features.retry')}</button></div> :
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {plants.map(plant => <article key={plant.name} className="bg-white/80 border rounded-xl p-5">
          <h2 className="font-semibold text-green-800 text-lg mb-3">{plant.name}</h2>
          <ul className="space-y-2 text-sm text-gray-600">{plant.conditions.map(condition => <li key={condition}>{condition}</li>)}</ul>
        </article>)}
        {catalogue && !plants.length && <p>{t('features.noResults')}</p>}
      </div>}
  </div>;
}
