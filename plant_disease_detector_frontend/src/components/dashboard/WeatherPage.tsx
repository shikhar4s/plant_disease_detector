import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, messageOf } from '../../lib/api';
import type { RiskData, WeatherData } from '../../lib/types';
import { usePlantData } from '../../contexts/PlantDataContext';

type WeatherLocation = { id: number; name: string; state: string; district: string; country: string };
type LocationResults = { locations: WeatherLocation[] };
const locationLabel = (location: WeatherLocation) => [location.name, location.district, location.state, location.country].filter((part, index, parts) => part && parts.indexOf(part) === index).join(', ');
const weatherLabel = (code: number, hi: boolean) => {
  const labels = hi ? ['साफ़', 'आंशिक बादल', 'कोहरा', 'बारिश', 'बर्फ़', 'बारिश की बौछारें', 'बर्फ़ की बौछारें', 'आंधी-तूफ़ान'] : ['Clear', 'Partly cloudy', 'Fog', 'Rain', 'Snow', 'Rain showers', 'Snow showers', 'Thunderstorm'];
  return labels[code === 0 ? 0 : code <= 3 ? 1 : code <= 48 ? 2 : code <= 67 ? 3 : code <= 77 ? 4 : code <= 82 ? 5 : code <= 86 ? 6 : 7];
};

export default function WeatherPage() {
  const { t, i18n } = useTranslation();
  const hi = i18n.language.startsWith('hi');
  const { selectedImage, setWeatherContextId } = usePlantData();
  const [city, setCity] = useState(''); const [data, setData] = useState<WeatherData | null>(null);
  const [risk, setRisk] = useState<RiskData | null>(null); const [loading, setLoading] = useState(false); const [error, setError] = useState('');
  const [locations, setLocations] = useState<WeatherLocation[]>([]);
  const [selectedLocation, setSelectedLocation] = useState('');
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState('');
  const [searched, setSearched] = useState(false);
  const [riskLoading, setRiskLoading] = useState(false);
  const [locating, setLocating] = useState(false);
  const weatherRequest = useRef<AbortController | null>(null);
  const riskRequest = useRef<AbortController | null>(null);
  const operation = useRef(0);
  const query = city.trim();

  useEffect(() => {
    riskRequest.current?.abort();
    setRisk(null);
    setRiskLoading(false);
  }, [i18n.language, selectedImage?.id]);

  useEffect(() => () => {
    operation.current += 1;
    weatherRequest.current?.abort();
    riskRequest.current?.abort();
  }, []);

  useEffect(() => {
    if (query.length < 2) return;
    const controller = new AbortController();
    setLocationLoading(true);
    setLocationError('');
    const timer = window.setTimeout(() => {
      void api<LocationResults>('/api/plant_doctor_ai/weather/locations/?q=' + encodeURIComponent(query), {
        signal: controller.signal, headers: { Language: i18n.language },
      }).then(result => {
        if (controller.signal.aborted) return;
        setLocations(result.locations);
        setSearched(true);
      }).catch(cause => {
        if (!controller.signal.aborted) setLocationError(messageOf(cause));
      }).finally(() => {
        if (!controller.signal.aborted) setLocationLoading(false);
      });
    }, 350);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [query, i18n.language]);

  async function load(path: string) {
    operation.current += 1;
    weatherRequest.current?.abort();
    riskRequest.current?.abort();
    const controller = new AbortController();
    weatherRequest.current = controller;
    setLoading(true); setLocating(false); setError(''); setRisk(null); setRiskLoading(false); setData(null); setWeatherContextId('');
    try {
      const result = await api<WeatherData>(path, { signal: controller.signal, headers: { Language: i18n.language } });
      if (!controller.signal.aborted) { setData(result); setWeatherContextId(result.context_id); }
    } catch (cause) { if (!controller.signal.aborted) setError(messageOf(cause)); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }
  function geolocate() {
    if (!navigator.geolocation) { setError(t('features.geolocationUnavailable')); return; }
    const attempt = ++operation.current;
    setLocating(true); setError('');
    navigator.geolocation.getCurrentPosition(position => {
      if (operation.current !== attempt) return;
      void load('/api/plant_doctor_ai/weather/?' + new URLSearchParams({
        latitude: String(position.coords.latitude), longitude: String(position.coords.longitude),
      }));
    }, cause => {
      if (operation.current !== attempt) return;
      setLocating(false);
      setError(cause.code === 1 ? t('features.locationDenied') : (hi ? 'स्थान नहीं मिल सका। शहर खोजकर चुनें और फिर कोशिश करें।' : 'Could not find your location. Search and select a city instead.'));
    }, { timeout: 10000, maximumAge: 300000 });
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
    <p className="page-subtitle">{t('features.weatherSubtitle')}</p></header>
    <form onSubmit={event => {
      event.preventDefault();
      if (selectedLocation) void load('/api/plant_doctor_ai/weather/?location_id=' + encodeURIComponent(selectedLocation));
    }} className="panel space-y-4">
      <div className="grid md:grid-cols-2 gap-4">
        <label className="field-label">{t('features.city')}<input className="field" value={city} maxLength={120} autoComplete="off"
          placeholder={hi ? 'जैसे इंदौर, भोपाल या दिल्ली' : 'e.g. Indore, Bhopal or Delhi'} aria-describedby="location-search-help"
          onChange={event => { setCity(event.target.value); setSelectedLocation(''); setLocations([]); setSearched(false); setLocationLoading(false); setLocationError(''); }} /></label>
        <label className="field-label">{hi ? 'सही शहर और क्षेत्र चुनें' : 'Select city and region'}
          <select className="field" value={selectedLocation} disabled={!locations.length || locationLoading} onChange={event => setSelectedLocation(event.target.value)} required>
            <option value="">{hi ? 'स्थान चुनें' : 'Choose a location'}</option>
            {locations.map(location => <option key={location.id} value={String(location.id)}>{locationLabel(location)}</option>)}
          </select>
        </label>
      </div>
      <p id="location-search-help" className="text-sm text-gray-600">{hi ? 'कम से कम 2 अक्षर लिखें, फिर राज्य और देश सहित सही स्थान चुनें।' : 'Type at least 2 characters, then choose the correct location with its state and country.'}</p>
      <div role="status" aria-live="polite" className="text-sm text-gray-600">
        {locationLoading ? (hi ? 'स्थान खोज रहे हैं…' : 'Finding locations…') : searched && !locations.length ? (hi ? 'कोई स्थान नहीं मिला। पास के शहर का नाम आज़माएँ।' : 'No matching locations. Try a nearby city.') : locations.length > 0 ? (hi ? `${locations.length} स्थान मिले। नीचे मौसम देखने से पहले एक चुनें।` : `${locations.length} locations found. Choose one before viewing weather.`) : ''}
      </div>
      {locationError && <p className="error-panel" role="alert">{locationError}</p>}
      <div className="flex flex-wrap gap-3">
        <button disabled={!selectedLocation || loading || locationLoading} className="primary-button disabled:opacity-50">{hi ? 'मौसम देखें' : 'Show weather'}</button>
        <button type="button" disabled={locating || loading} onClick={geolocate} className="secondary-button disabled:opacity-50">{t('features.useLocation')}</button>
      </div>
    </form>
    {(loading || locating) && <div className="panel" role="status">{locating ? (hi ? 'आपका स्थान ढूँढ रहे हैं…' : 'Finding your location…') : t('features.loading')}</div>}{error && <div className="error-panel" role="alert">{error}</div>}
    {data && <><section className="panel"><div className="flex flex-wrap justify-between gap-4"><div><p className="eyebrow">{data.location.name}, {data.location.state} {data.location.country}</p>
      <h2 className="text-5xl font-bold">{data.current.temperature_2m}°</h2><p>{weatherLabel(data.current.weather_code, hi)}</p></div>
      <dl className="grid grid-cols-2 md:grid-cols-3 gap-5 text-sm"><div><dt>{t('features.feelsLike')}</dt><dd>{data.current.apparent_temperature}°C</dd></div>
        <div><dt>{t('features.humidity')}</dt><dd>{data.current.relative_humidity_2m}%</dd></div><div><dt>{t('features.precipitation')}</dt><dd>{data.current.precipitation} mm</dd></div>
        <div><dt>{t('features.wind')}</dt><dd>{data.current.wind_speed_10m} km/h</dd></div><div><dt>{t('features.timezone')}</dt><dd>{data.location.timezone}</dd></div></dl></div></section>
      <section><h2 className="section-title mb-3">{t('features.sevenDayForecast')}</h2><div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
        {data.forecast.map(day => <article key={String(day.date)} className="panel p-4"><h3 className="font-semibold">{new Date(String(day.date) + 'T12:00').toLocaleDateString(i18n.language, { weekday: 'short' })}</h3>
          <p className="text-sm">{weatherLabel(Number(day.weather_code), hi)}</p><p className="mt-2 font-semibold">{day.temperature_2m_max}° / {day.temperature_2m_min}°</p>
          <p className="text-sm text-blue-700">{t('features.rain')}: {day.precipitation_probability_max}%</p></article>)}</div></section>
      <section className="panel"><div className="flex flex-wrap justify-between gap-3"><div><h2 className="section-title">{t('features.diseaseRisk')}</h2><p className="text-sm text-gray-600">{t('features.riskSeparate')}</p></div>
        <button disabled={riskLoading} onClick={() => void calculateRisk()} className="primary-button disabled:opacity-50">{riskLoading ? t('features.loading') : t('features.calculateRisk')}</button></div>
        {risk && <div className="mt-4"><p className={`risk-badge risk-${risk.level.toLowerCase()}`}>{risk.level_label || t('features.' + risk.level.toLowerCase())}</p>
          <ul className="list-disc pl-5 mt-3">{risk.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul><p className="text-xs text-gray-500 mt-3">{risk.method}</p>
          {!!risk.references?.length && <p className="text-xs mt-2">{risk.references.map((reference, index) => <span key={reference.url}>{index > 0 && ' · '}<a className="underline" href={reference.url} target="_blank" rel="noreferrer">{reference.title}</a></span>)}</p>}</div>}</section>
      <section className="panel"><h2 className="section-title">{t('features.farmGuidance')}</h2><ul className="list-disc pl-5 mt-3 space-y-2">
        <li>{t('features.rainGuidance')}</li><li>{t('features.humidityGuidance')}</li><li>{t('features.heatGuidance')}</li><li>{t('features.soilGuidance')}</li></ul></section>
      <p className="text-sm text-gray-600">{data.source.name} · {new Date(data.fetched_at).toLocaleString()} · {data.location.timezone}</p></>}
  </div>;
}

