import { useTranslation } from 'react-i18next';
import type { Analysis } from '../../lib/types';

export default function ResultCard({ image, onDetails }: { image: Analysis; onDetails: () => void }) {
  const { t } = useTranslation();
  return <article className="bg-white/80 rounded-xl shadow-lg border border-white/20 overflow-hidden">
    {image.image_url && <img src={image.image_url} alt="Analyzed leaf" className="h-48 w-full object-contain bg-gray-50" />}
    <div className="p-6 space-y-4">
      <p className="text-sm font-medium text-green-700">{t('features.' + image.prediction_status)}</p>
      {image.prediction_status === 'uncertain' ? <h2 className="text-xl font-bold text-amber-800">{t('features.uncertainMessage')}</h2> :
        <div><p className="text-sm text-gray-500">{t('features.crop')}: {image.crop_name}</p>
          <h2 className="text-xl font-bold text-gray-800">{t('features.disease')}: {image.condition_name}</h2></div>}
      <p className="text-gray-700">{t('features.modelConfidence')}: <strong>{(image.confidence * 100).toFixed(1)}%</strong></p>
      <div className="h-3 rounded-full bg-gray-200" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(image.confidence * 100)}>
        <div className="h-3 rounded-full bg-green-600" style={{ width: `${Math.max(2, image.confidence * 100)}%` }} /></div>
      <p className="text-sm text-gray-500">{t('features.confidenceShort')}</p>
      <div className="bg-green-50 rounded-lg p-4 text-sm text-green-900">{image.recommended_treatment}</div>
      <button onClick={onDetails} className="bg-green-600 text-white rounded-lg px-5 py-2">{t('features.viewResult')}</button>
    </div>
  </article>;
}
