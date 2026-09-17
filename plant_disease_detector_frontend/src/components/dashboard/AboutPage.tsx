import { useTranslation } from 'react-i18next';
import developerPhoto from '../../assets/shikhar-shrivastava.jpg';

export default function AboutPage() {
  const { t } = useTranslation();
  return <div className="max-w-5xl mx-auto space-y-6"><header><p className="eyebrow">PLANTDOC</p><h1 className="page-title">{t('features.about')}</h1>
    <p className="page-subtitle">{t('features.platformTitle')}</p></header>
    <section className="panel"><h2 className="section-title">{t('features.whatPlantdocDoes')}</h2><p>{t('features.aboutCopy')}</p><p className="mt-3">{t('features.advisory')}</p></section>
    <section className="grid md:grid-cols-2 gap-5"><div className="panel"><h2 className="section-title">{t('features.dataSources')}</h2>
      <ul className="list-disc pl-5 mt-3 space-y-2"><li>AGMARKNET / data.gov.in — mandi price records</li><li>Wikimedia Commons — dynamically resolved commodity images with source links and license metadata</li><li>Open-Meteo — weather forecasts and geocoding</li><li>PlantVillage and PlantDoc — EfficientNet-B0, 38 single-label classes. Field-test accuracy: 65.3%; laboratory-style test accuracy: 97.8%. Field photos remain substantially harder.</li></ul></div>
      <div className="panel"><h2 className="section-title">{t('features.developer')}</h2>
        <img src={developerPhoto} alt="Shikhar Shrivastava" width={120} height={160} className="mt-4 w-30 h-40 object-cover object-top rounded-xl" loading="lazy" />
        <p className="text-xl font-bold mt-3">Shikhar Shrivastava</p><p className="text-sm text-gray-600 mt-2">PLANTDOC developer and maintainer</p>
        <a className="inline-block mt-3 text-green-800 underline" href="https://github.com/shikhar4s" target="_blank" rel="noreferrer">GitHub · shikhar4s</a>
      </div></section>
    <section className="panel"><h2 className="section-title">{t('features.modelLimitations')}</h2><ul className="list-disc pl-5 mt-3 space-y-2">
      <li>{t('features.singleLabelLimit')}</li><li>{t('features.confidenceLimit')}</li><li>{t('features.severityLimit')}</li></ul></section>
  </div>;
}

