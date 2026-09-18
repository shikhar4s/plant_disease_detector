import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, messageOf } from '../../lib/api';
import type { RiskData, WeatherData } from '../../lib/types';
import { usePlantData } from '../../contexts/PlantDataContext';

type WeatherState = { code: string; name: string; city_count: number };
type WeatherCity = { id: number; name: string; district: string };
type StateResults = { states: WeatherState[]; source: string; source_url: string; fetched_at: string; coverage: string };
type CityResults = { cities: WeatherCity[] };
const weatherLabel = (code: number | null, hi: boolean) => {
  if (code === null || !Number.isFinite(code)) return hi ? 'उपलब्ध नहीं' : 'Unavailable';
  const labels = hi ? ['साफ़', 'आंशिक बादल', 'कोहरा', 'बारिश', 'बर्फ़', 'बारिश की बौछारें', 'बर्फ़ की बौछारें', 'आंधी-तूफ़ान'] : ['Clear', 'Partly cloudy', 'Fog', 'Rain', 'Snow', 'Rain showers', 'Snow showers', 'Thunderstorm'];
  return labels[code === 0 ? 0 : code <= 3 ? 1 : code <= 48 ? 2 : code <= 67 ? 3 : code <= 77 ? 4 : code <= 82 ? 5 : code <= 86 ? 6 : 7];
};
const measure = (value: number | string | null | undefined, unit: string) => typeof value === 'number' && Number.isFinite(value) ? `${value}${unit}` : '—';

export default function WeatherPage() {
  const { t, i18n } = useTranslation();
  const hi = i18n.language.startsWith('hi');
  const { selectedImage, setWeatherContextId } = usePlantData();
  const [data, setData] = useState<WeatherData | null>(null);
  const [risk, setRisk] = useState<RiskData | null>(null); const [loading, setLoading] = useState(false); const [error, setError] = useState('');
  const [states, setStates] = useState<WeatherState[]>([]);
  const [cities, setCities] = useState<WeatherCity[]>([]);
  const [catalog, setCatalog] = useState<StateResults | null>(null);
  const [statesLoading, setStatesLoading] = useState(true);
  const [citiesLoading, setCitiesLoading] = useState(false);
  const [catalogError, setCatalogError] = useState('');
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedLocation, setSelectedLocation] = useState('');
  const [riskLoading, setRiskLoading] = useState(false);
  const weatherRequest = useRef<AbortController | null>(null);
  const riskRequest = useRef<AbortController | null>(null);
  const locationRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    riskRequest.current?.abort();
    setRisk(null);
    setRiskLoading(false);
  }, [i18n.language, selectedImage?.id]);

  useEffect(() => {
    const controller = new AbortController();
    void api<StateResults>('/api/plant_doctor_ai/weather/catalog/', { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) { setStates(result.states); setCatalog(result); } })
      .catch(cause => { if (!controller.signal.aborted) setCatalogError(messageOf(cause)); })
      .finally(() => { if (!controller.signal.aborted) setStatesLoading(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    locationRequest.current?.abort();
    if (!selectedRegion) return;
    const controller = new AbortController();
    locationRequest.current = controller;
    setCitiesLoading(true);
    setCatalogError('');
    void api<CityResults>('/api/plant_doctor_ai/weather/catalog/?state=' + encodeURIComponent(selectedRegion), { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) setCities(result.cities); })
      .catch(cause => { if (!controller.signal.aborted) setCatalogError(messageOf(cause)); })
      .finally(() => { if (!controller.signal.aborted) setCitiesLoading(false); });
    return () => controller.abort();
  }, [selectedRegion]);

  useEffect(() => () => {
    weatherRequest.current?.abort();
    riskRequest.current?.abort();
    locationRequest.current?.abort();
  }, []);

  function clearWeather() {
    weatherRequest.current?.abort();
    riskRequest.current?.abort();
    setLoading(false); setRiskLoading(false); setError('');
    setData(null); setRisk(null); setWeatherContextId('');
  }

  async function load(path: string) {
    weatherRequest.current?.abort();
    riskRequest.current?.abort();
    const controller = new AbortController();
    weatherRequest.current = controller;
    setLoading(true); setError(''); setRisk(null); setRiskLoading(false); setData(null); setWeatherContextId('');
    try {
      const result = await api<WeatherData>(path, { signal: controller.signal, headers: { Language: i18n.language } });
      if (!controller.signal.aborted) { setData(result); setWeatherContextId(result.context_id); }
    } catch (cause) { if (!controller.signal.aborted) setError(messageOf(cause)); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }
  async function calculateRisk() {
    if (!data) return;
    riskRequest.current?.abort();
    const controller = new AbortController();
    riskRequest.current = controller;
    setRiskLoading(true); setError('');
    try {
      const result = await api<RiskData>('/api/plant_doctor_ai/risk/', { signal: controller.signal, method: 'POST', headers: { Language: i18n.language }, body: JSON.stringify({
        weatherContextId: data.context_id,
        crop: selectedImage?.prediction_status !== 'uncertain' ? selectedImage?.crop_name || '' : '',
        disease: selectedImage?.prediction_status !== 'uncertain' ? selectedImage?.condition_name || '' : '',
      }) });
      if (!controller.signal.aborted) setRisk(result);
    } catch (cause) { if (!controller.signal.aborted) setError(messageOf(cause)); }
    finally { if (!controller.signal.aborted) setRiskLoading(false); }
  }
  return <div className="max-w-6xl mx-auto space-y-6"><header><p className="eyebrow">{t('features.farmWeather')}</p><h1 className="page-title">{t('features.weather')}</h1>
    <p className="page-subtitle">{t('features.weatherSubtitle')} {hi ? 'केवल भारत के स्थान उपलब्ध हैं।' : 'Indian locations only.'}</p></header>
    <form onSubmit={event => {
      event.preventDefault();
      if (selectedLocation) void load('/api/plant_doctor_ai/weather/?location_id=' + encodeURIComponent(selectedLocation));
    }} className="panel space-y-4">
      <div className="grid md:grid-cols-2 gap-4">
        <label className="field-label">{hi ? 'राज्य / क्षेत्र' : 'State / region'}
          <select className="field" value={selectedRegion} disabled={statesLoading || !states.length} onChange={event => {
            locationRequest.current?.abort(); setSelectedRegion(event.target.value); setSelectedLocation(''); setCities([]); clearWeather();
          }}>
            <option value="">{hi ? 'राज्य या केंद्र शासित प्रदेश चुनें' : 'Choose a state or union territory'}</option>
            {states.map(state => <option key={state.code} value={state.code}>{state.name} ({state.city_count})</option>)}
          </select>
        </label>
        <label className="field-label">{hi ? 'शहर / स्थान' : 'City / location'}
          <select className="field" value={selectedLocation} disabled={!selectedRegion || citiesLoading || !cities.length} onChange={event => { setSelectedLocation(event.target.value); clearWeather(); }}>
            <option value="">{hi ? 'शहर चुनें' : 'Choose a city'}</option>
            {cities.map(city => <option key={city.id} value={String(city.id)}>{city.name}{city.district ? `, ${city.district}` : ''}</option>)}
          </select>
        </label>
      </div>
      <div role="status" aria-live="polite" className="text-sm text-gray-600">
        {statesLoading ? (hi ? 'राज्य लोड हो रहे हैं…' : 'Loading states…') : citiesLoading ? (hi ? 'शहर लोड हो रहे हैं…' : 'Loading cities…') : selectedRegion ? (hi ? `${cities.length} उपलब्ध शहर और कस्बे।` : `${cities.length} available cities and towns.`) : (hi ? 'पहले राज्य चुनें, फिर शहर चुनें।' : 'Choose a state, then a city.')}
      </div>
      {catalogError && <p className="error-panel" role="alert">{catalogError}</p>}
      {catalog && <p className="text-xs text-gray-600">{hi ? 'छोटे गाँव सूची में नहीं हो सकते। स्रोत:' : 'Smaller settlements may be absent. Source:'} <a className="underline" href={catalog.source_url} target="_blank" rel="noreferrer">{catalog.source}</a> (CC BY 4.0) · {catalog.fetched_at}</p>}
      <div className="flex flex-wrap gap-3">
        <button disabled={!selectedLocation || loading || citiesLoading} className="primary-button disabled:opacity-50">{hi ? 'मौसम देखें' : 'Show weather'}</button>
      </div>
    </form>
    {loading && <div className="panel" role="status">{t('features.loading')}</div>}{error && <div className="error-panel" role="alert">{error}</div>}
    {data && <><section className="panel"><div className="flex flex-wrap justify-between gap-4"><div><p className="eyebrow">{data.location.name}, {data.location.state} {data.location.country}</p>
      <h2 className="text-5xl font-bold">{measure(data.current.temperature_2m, '°')}</h2><p>{weatherLabel(typeof data.current.weather_code === 'number' ? data.current.weather_code : null, hi)}</p></div>
      <dl className="grid grid-cols-2 md:grid-cols-3 gap-5 text-sm"><div><dt>{t('features.feelsLike')}</dt><dd>{measure(data.current.apparent_temperature, '°C')}</dd></div>
        <div><dt>{t('features.humidity')}</dt><dd>{measure(data.current.relative_humidity_2m, '%')}</dd></div><div><dt>{data.source.name.startsWith('MET Norway') ? (hi ? 'अगले घंटे का वर्षा पूर्वानुमान' : 'Next-hour precipitation forecast') : t('features.precipitation')}</dt><dd>{measure(data.current.precipitation, ' mm')}</dd></div>
        <div><dt>{t('features.wind')}</dt><dd>{measure(data.current.wind_speed_10m, ' km/h')}</dd></div><div><dt>{t('features.timezone')}</dt><dd>{data.location.timezone}</dd></div></dl></div></section>
      <section><h2 className="section-title mb-3">{t('features.sevenDayForecast')}</h2><div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
        {data.forecast.map(day => <article key={String(day.date)} className="panel p-4"><h3 className="font-semibold">{new Date(String(day.date) + 'T12:00').toLocaleDateString(i18n.language, { weekday: 'short' })}</h3>
          <p className="text-sm">{weatherLabel(typeof day.weather_code === 'number' ? day.weather_code : null, hi)}</p><p className="mt-2 font-semibold">{measure(day.temperature_2m_max, '°')} / {measure(day.temperature_2m_min, '°')}</p>
          <p className="text-sm text-blue-700">{day.precipitation_probability_max != null ? `${t('features.rain')}: ${measure(day.precipitation_probability_max, '%')}` : day.precipitation_sum != null ? `${hi ? 'अनुमानित वर्षा' : 'Forecast precipitation'}: ${measure(day.precipitation_sum, ' mm')}` : (hi ? 'वर्षा की संभावना उपलब्ध नहीं' : 'Rain probability unavailable')}</p></article>)}</div></section>
      <section className="panel"><div className="flex flex-wrap justify-between gap-3"><div><h2 className="section-title">{t('features.diseaseRisk')}</h2><p className="text-sm text-gray-600">{t('features.riskSeparate')}</p></div>
        <button disabled={riskLoading} onClick={() => void calculateRisk()} className="primary-button disabled:opacity-50">{riskLoading ? t('features.loading') : t('features.calculateRisk')}</button></div>
        {risk && <div className="mt-4"><p className={`risk-badge risk-${risk.level.toLowerCase()}`}>{risk.level_label || t('features.' + risk.level.toLowerCase())}</p>
          <ul className="list-disc pl-5 mt-3">{risk.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul><p className="text-xs text-gray-500 mt-3">{risk.method}</p>
          {!!risk.references?.length && <p className="text-xs mt-2">{risk.references.map((reference, index) => <span key={reference.url}>{index > 0 && ' · '}<a className="underline" href={reference.url} target="_blank" rel="noreferrer">{reference.title}</a></span>)}</p>}</div>}</section>
      <section className="panel"><h2 className="section-title">{t('features.farmGuidance')}</h2><ul className="list-disc pl-5 mt-3 space-y-2">
        <li>{t('features.rainGuidance')}</li><li>{t('features.humidityGuidance')}</li><li>{t('features.heatGuidance')}</li><li>{t('features.soilGuidance')}</li></ul></section>
      <p className="text-sm text-gray-600"><a className="underline" href={data.source.url} target="_blank" rel="noreferrer">{data.source.name}</a> · {new Date(data.fetched_at).toLocaleString()} · {data.location.timezone}{data.source.license && <> · <a className="underline" href={data.source.license} target="_blank" rel="noreferrer">CC BY 4.0</a></>}{data.source.name.startsWith('MET Norway') && <> · {hi ? 'पूर्वानुमान अवधि के अनुसार वर्षा का योग; संभावना उपलब्ध नहीं' : 'Precipitation summed by forecast period; probability unavailable'}</>}</p></>}
  </div>;
}
