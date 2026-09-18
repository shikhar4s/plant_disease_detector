import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, messageOf } from '../../lib/api';
import type { RiskData, WeatherData } from '../../lib/types';
import { usePlantData } from '../../contexts/PlantDataContext';

type WeatherLocation = { id: number; name: string; state: string; district: string; country: string; country_code: string };
type LocationResults = { locations: WeatherLocation[] };
const locationLabel = (location: WeatherLocation) => [location.name, location.district, location.state, location.country].filter((part, index, parts) => part && parts.indexOf(part) === index).join(', ');
const regionKey = (location: WeatherLocation) => JSON.stringify([location.country_code || location.country, location.state]);
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
  const [city, setCity] = useState(''); const [data, setData] = useState<WeatherData | null>(null);
  const [risk, setRisk] = useState<RiskData | null>(null); const [loading, setLoading] = useState(false); const [error, setError] = useState('');
  const [locations, setLocations] = useState<WeatherLocation[]>([]);
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedLocation, setSelectedLocation] = useState('');
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState('');
  const [searched, setSearched] = useState(false);
  const [riskLoading, setRiskLoading] = useState(false);
  const [locating, setLocating] = useState(false);
  const weatherRequest = useRef<AbortController | null>(null);
  const riskRequest = useRef<AbortController | null>(null);
  const locationRequest = useRef<AbortController | null>(null);
  const operation = useRef(0);
  const query = city.trim();
  const regions = Array.from(new Map(locations.map(location => [regionKey(location), location])).entries());
  const matchingLocations = locations.filter(location => regionKey(location) === selectedRegion);

  useEffect(() => {
    riskRequest.current?.abort();
    setRisk(null);
    setRiskLoading(false);
  }, [i18n.language, selectedImage?.id]);

  useEffect(() => () => {
    operation.current += 1;
    weatherRequest.current?.abort();
    riskRequest.current?.abort();
    locationRequest.current?.abort();
  }, []);

  async function findLocations() {
    locationRequest.current?.abort();
    setSelectedRegion(''); setSelectedLocation(''); setLocations([]); setSearched(false);
    if (query.length < 2) {
      setLocationError(hi ? 'शहर का नाम कम से कम 2 अक्षरों में लिखें।' : 'Enter at least 2 characters for the city.');
      return;
    }
    const controller = new AbortController();
    locationRequest.current = controller;
    setLocationLoading(true);
    setLocationError('');
    try {
      const result = await api<LocationResults>('/api/plant_doctor_ai/weather/locations/?q=' + encodeURIComponent(query), {
        signal: controller.signal, headers: { Language: i18n.language },
      });
      if (!controller.signal.aborted) {
        setLocations(result.locations);
        setSearched(true);
      }
    } catch (cause) {
      if (!controller.signal.aborted) setLocationError(messageOf(cause));
    } finally {
      if (!controller.signal.aborted) setLocationLoading(false);
    }
  }

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
      else void findLocations();
    }} className="panel space-y-4">
      <div className="grid md:grid-cols-3 gap-4">
        <label className="field-label">{t('features.city')}<input className="field" value={city} maxLength={120} autoComplete="off"
          placeholder={hi ? 'जैसे Indore, Bhopal या Delhi' : 'e.g. Indore, Bhopal or Delhi'} aria-describedby="location-search-help"
          onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); void findLocations(); } }}
          onChange={event => { locationRequest.current?.abort(); weatherRequest.current?.abort(); riskRequest.current?.abort(); setCity(event.target.value); setSelectedRegion(''); setSelectedLocation(''); setLocations([]); setSearched(false); setLocationLoading(false); setLoading(false); setRiskLoading(false); setLocationError(''); setError(''); setData(null); setRisk(null); setWeatherContextId(''); }} /></label>
        <label className="field-label">{hi ? 'राज्य / क्षेत्र और देश' : 'State / region and country'}
          <select className="field" value={selectedRegion} disabled={!regions.length || locationLoading} onChange={event => { setSelectedRegion(event.target.value); setSelectedLocation(''); }}>
            <option value="">{hi ? 'क्षेत्र चुनें' : 'Choose a region'}</option>
            {regions.map(([key, location]) => <option key={key} value={key}>{[location.state || (hi ? 'क्षेत्र उपलब्ध नहीं' : 'Region unavailable'), location.country].filter(Boolean).join(', ')}</option>)}
          </select>
        </label>
        <label className="field-label">{hi ? 'शहर / स्थान' : 'City / location'}
          <select className="field" value={selectedLocation} disabled={!selectedRegion || locationLoading} onChange={event => setSelectedLocation(event.target.value)}>
            <option value="">{hi ? 'स्थान चुनें' : 'Choose a location'}</option>
            {matchingLocations.map(location => <option key={location.id} value={String(location.id)}>{locationLabel(location)}</option>)}
          </select>
        </label>
      </div>
      <p id="location-search-help" className="text-sm text-gray-600">{hi ? 'शहर का अंग्रेज़ी नाम लिखकर खोजें, फिर सही क्षेत्र और स्थान चुनें। Open-Meteo सभी हिन्दी वर्तनियों को नहीं पहचानता।' : 'Search by city name, then choose the correct region and location. For best results, use an English spelling.'}</p>
      <div role="status" aria-live="polite" className="text-sm text-gray-600">
        {locationLoading ? (hi ? 'स्थान खोज रहे हैं…' : 'Finding locations…') : searched && !locations.length ? (hi ? 'कोई स्थान नहीं मिला। अंग्रेज़ी वर्तनी या पास के शहर का नाम आज़माएँ।' : 'No matching locations. Try an English spelling or a nearby city.') : locations.length > 0 ? (hi ? `${locations.length} स्थान मिले। सही क्षेत्र और स्थान चुनें।` : `${locations.length} locations found. Choose the correct region and location.`) : ''}
      </div>
      {locationError && <p className="error-panel" role="alert">{locationError}</p>}
      <div className="flex flex-wrap gap-3">
        <button type="button" disabled={locationLoading || loading} onClick={() => void findLocations()} className="secondary-button disabled:opacity-50">{hi ? 'शहर खोजें' : 'Find cities'}</button>
        <button disabled={!selectedLocation || loading || locationLoading} className="primary-button disabled:opacity-50">{hi ? 'मौसम देखें' : 'Show weather'}</button>
        <button type="button" disabled={locating || loading} onClick={geolocate} className="secondary-button disabled:opacity-50">{t('features.useLocation')}</button>
      </div>
    </form>
    {(loading || locating) && <div className="panel" role="status">{locating ? (hi ? 'आपका स्थान ढूँढ रहे हैं…' : 'Finding your location…') : t('features.loading')}</div>}{error && <div className="error-panel" role="alert">{error}</div>}
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

