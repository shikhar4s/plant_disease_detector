import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, messageOf } from '../../lib/api';
import type { RiskData, WeatherData } from '../../lib/types';
import { usePlantData } from '../../contexts/PlantDataContext';

const weatherLabel = (code: number) => code === 0 ? 'Clear' : code <= 3 ? 'Partly cloudy' : code <= 48 ? 'Fog' : code <= 67 ? 'Rain' : code <= 77 ? 'Snow' : code <= 82 ? 'Rain showers' : code <= 86 ? 'Snow showers' : 'Thunderstorm';

export default function WeatherPage() {
  const { t, i18n } = useTranslation();
  const { selectedImage, setWeatherContextId } = usePlantData();
  const [city, setCity] = useState(''); const [data, setData] = useState<WeatherData | null>(null);
  const [risk, setRisk] = useState<RiskData | null>(null); const [loading, setLoading] = useState(false); const [error, setError] = useState('');
  async function load(path: string) {
    setLoading(true); setError(''); setRisk(null);
    try { const result = await api<WeatherData>(path, { headers: { Language: i18n.language } }); setData(result); setWeatherContextId(result.context_id); }
    catch (error) { setError(messageOf(error)); } finally { setLoading(false); }
  }
  function geolocate() {
    if (!navigator.geolocation) { setError(t('features.geolocationUnavailable')); return; }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(position => void load('/api/plant_doctor_ai/weather/?' + new URLSearchParams({
      latitude: String(position.coords.latitude), longitude: String(position.coords.longitude),
    })), () => { setLoading(false); setError(t('features.locationDenied')); }, { timeout: 10000, maximumAge: 300000 });
  }
  async function calculateRisk() {
    if (!data) return;
    try { setRisk(await api<RiskData>('/api/plant_doctor_ai/risk/', { method: 'POST', headers: { Language: i18n.language }, body: JSON.stringify({
      weatherContextId: data.context_id, crop: selectedImage?.crop_name || '', disease: selectedImage?.condition_name || '',
    }) })); } catch (error) { setError(messageOf(error)); }
  }
  return <div className="max-w-6xl mx-auto space-y-6"><header><p className="eyebrow">{t('features.farmWeather')}</p><h1 className="page-title">{t('features.weather')}</h1>
    <p className="page-subtitle">{t('features.weatherSubtitle')}</p></header>
    <form onSubmit={event => { event.preventDefault(); void load('/api/plant_doctor_ai/weather/?city=' + encodeURIComponent(city)); }} className="panel flex flex-wrap gap-3">
      <label className="field-label flex-1 min-w-56">{t('features.city')}<input className="field" value={city} onChange={event => setCity(event.target.value)} required /></label>
      <button className="primary-button self-end">{t('features.search')}</button><button type="button" onClick={geolocate} className="secondary-button self-end">{t('features.useLocation')}</button></form>
    {loading && <div className="panel" role="status">{t('features.loading')}</div>}{error && <div className="error-panel" role="alert">{error}</div>}
    {data && <><section className="panel"><div className="flex flex-wrap justify-between gap-4"><div><p className="eyebrow">{data.location.name}, {data.location.state} {data.location.country}</p>
      <h2 className="text-5xl font-bold">{data.current.temperature_2m}°</h2><p>{weatherLabel(data.current.weather_code)}</p></div>
      <dl className="grid grid-cols-2 md:grid-cols-3 gap-5 text-sm"><div><dt>{t('features.feelsLike')}</dt><dd>{data.current.apparent_temperature}°C</dd></div>
        <div><dt>{t('features.humidity')}</dt><dd>{data.current.relative_humidity_2m}%</dd></div><div><dt>{t('features.precipitation')}</dt><dd>{data.current.precipitation} mm</dd></div>
        <div><dt>{t('features.wind')}</dt><dd>{data.current.wind_speed_10m} km/h</dd></div><div><dt>{t('features.timezone')}</dt><dd>{data.location.timezone}</dd></div></dl></div></section>
      <section><h2 className="section-title mb-3">{t('features.sevenDayForecast')}</h2><div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
        {data.forecast.map(day => <article key={String(day.date)} className="panel p-4"><h3 className="font-semibold">{new Date(String(day.date) + 'T12:00').toLocaleDateString(undefined, { weekday: 'short' })}</h3>
          <p className="text-sm">{weatherLabel(Number(day.weather_code))}</p><p className="mt-2 font-semibold">{day.temperature_2m_max}° / {day.temperature_2m_min}°</p>
          <p className="text-sm text-blue-700">{t('features.rain')}: {day.precipitation_probability_max}%</p></article>)}</div></section>
      <section className="panel"><div className="flex flex-wrap justify-between gap-3"><div><h2 className="section-title">{t('features.diseaseRisk')}</h2><p className="text-sm text-gray-600">{t('features.riskSeparate')}</p></div>
        <button onClick={() => void calculateRisk()} className="primary-button">{t('features.calculateRisk')}</button></div>
        {risk && <div className="mt-4"><p className={`risk-badge risk-${risk.level.toLowerCase()}`}>{risk.level_label || t('features.' + risk.level.toLowerCase())}</p>
          <ul className="list-disc pl-5 mt-3">{risk.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul><p className="text-xs text-gray-500 mt-3">{risk.method}</p>
          {!!risk.references?.length && <p className="text-xs mt-2">{risk.references.map((reference, index) => <span key={reference.url}>{index > 0 && ' · '}<a className="underline" href={reference.url} target="_blank" rel="noreferrer">{reference.title}</a></span>)}</p>}</div>}</section>
      <section className="panel"><h2 className="section-title">{t('features.farmGuidance')}</h2><ul className="list-disc pl-5 mt-3 space-y-2">
        <li>{t('features.rainGuidance')}</li><li>{t('features.humidityGuidance')}</li><li>{t('features.heatGuidance')}</li><li>{t('features.soilGuidance')}</li></ul></section>
      <p className="text-sm text-gray-600">{data.source.name} · {new Date(data.fetched_at).toLocaleString()} · {data.location.timezone}</p></>}
  </div>;
}
