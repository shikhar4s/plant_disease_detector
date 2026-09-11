import { useTranslation } from 'react-i18next';
import type { Analysis } from '../../lib/types';

export default function ResultCard({ image, onDetails }: { image: Analysis; onDetails: () => void }) {
  const { t } = useTranslation();
  return <article className="bg-white/80 rounded-xl shadow-lg border border-white/20 overflow-hidden">
    {image.image_url && <img src={image.image_url} alt="Analyzed leaf" className="h-48 w-full object-contain bg-gray-50" />}
    <div className="p-6 space-y-4">
      <p className="text-sm font-medium text-green-700">{t('features.' + image.prediction_status)}</p>
      <h2 className="text-xl font-bold text-gray-800">{image.disease}</h2>
      <p className="text-gray-700">{t('features.modelConfidence')}: <strong>{(image.confidence * 100).toFixed(1)}%</strong></p>
      <p className="text-sm text-gray-500">Model confidence is not disease severity or a guarantee of correctness.</p>
      <div className="bg-green-50 rounded-lg p-4 text-sm text-green-900">{image.recommended_treatment}</div>
      <button onClick={onDetails} className="bg-green-600 text-white rounded-lg px-5 py-2">{t('features.viewResult')}</button>
    </div>
  </article>;
}
