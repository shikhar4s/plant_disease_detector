import { useTranslation } from 'react-i18next';

export default function AboutPage() {
  const { t } = useTranslation();
  return <div className="max-w-5xl mx-auto space-y-6"><header><p className="eyebrow">PLANTDOC</p><h1 className="page-title">{t('features.about')}</h1>
    <p className="page-subtitle">{t('features.platformTitle')}</p></header>
    <section className="panel"><h2 className="section-title">{t('features.whatPlantdocDoes')}</h2><p>{t('features.aboutCopy')}</p><p className="mt-3">{t('features.advisory')}</p></section>
    <section className="grid md:grid-cols-2 gap-5"><div className="panel"><h2 className="section-title">{t('features.dataSources')}</h2>
      <ul className="list-disc pl-5 mt-3 space-y-2"><li>AGMARKNET / data.gov.in — mandi price records</li><li>Open-Meteo — weather forecasts and geocoding</li><li>PlantVillage-style 38-class model labels — model training provenance and metrics are not available in this repository</li></ul></div>
      <div className="panel"><h2 className="section-title">{t('features.developer')}</h2><p className="text-xl font-bold mt-3">Shikhar Shrivastava</p><p className="text-sm text-gray-600 mt-2">PLANTDOC developer and maintainer</p></div></section>
    <section className="panel"><h2 className="section-title">{t('features.modelLimitations')}</h2><ul className="list-disc pl-5 mt-3 space-y-2">
      <li>{t('features.singleLabelLimit')}</li><li>{t('features.confidenceLimit')}</li><li>{t('features.severityLimit')}</li></ul></section>
  </div>;
}
