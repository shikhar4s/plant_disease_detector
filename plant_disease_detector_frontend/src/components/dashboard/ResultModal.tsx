import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { toast } from 'react-hot-toast';
import { api, downloadBlob, messageOf } from '../../lib/api';
import type { Analysis } from '../../lib/types';

interface Props { image: Analysis; isOpen: boolean; onClose: () => void; onUpdate?: (image: Analysis) => void }

export default function ResultModal({ image, isOpen, onClose, onUpdate }: Props) {
  const { t } = useTranslation();
  const dialog = useRef<HTMLDialogElement>(null);
  const [notes, setNotes] = useState(image.notes);
  const [isSaving, setIsSaving] = useState(false);
  useEffect(() => { setNotes(image.notes); }, [image.id, image.notes]);
  useEffect(() => {
    const element = dialog.current;
    if (isOpen && !element?.open) element?.showModal();
    if (!isOpen && element?.open) element.close();
    return () => { element?.close(); };
  }, [isOpen]);

  async function saveNotes() {
    setIsSaving(true);
    try {
      const result = await api<Analysis>('/api/plant_doctor_ai/history/' + image.id + '/', {
        method: 'PATCH', body: JSON.stringify({ notes }),
      });
      onUpdate?.(result);
      toast.success(t('features.notesSaved'));
    } catch (error) { toast.error(messageOf(error)); } finally { setIsSaving(false); }
  }
  function downloadReport() {
    const text = ['PlantDoc analysis report', 'Date: ' + new Date(image.created_at).toLocaleString(),
      'Possible match: ' + image.disease, 'Model confidence: ' + (image.confidence * 100).toFixed(1) + '%',
      'Confidence is not disease severity. This is not a confirmed diagnosis.',
      '', 'Care guide', image.recommended_treatment, '', 'Prevention',
      ...image.prevention_tips.map(tip => '- ' + tip), '', 'Saved notes', image.notes].join('\n');
    downloadBlob(new Blob([text], { type: 'text/plain;charset=utf-8' }), 'plantdoc-analysis-' + image.id + '.txt');
  }

  return <dialog ref={dialog} onCancel={onClose} onClose={onClose} aria-labelledby="result-heading"
    className="rounded-2xl shadow-2xl w-[calc(100%-2rem)] max-w-2xl max-h-[90vh] p-0 backdrop:bg-black/50">
    <div className="flex items-center justify-between p-5 border-b sticky top-0 bg-white z-10">
      <h2 id="result-heading" className="text-xl font-bold text-gray-800">{t('result.title')}</h2>
      <button onClick={onClose} aria-label={t('features.close')} className="p-2 rounded-lg hover:bg-gray-100">
        <XMarkIcon className="w-6 h-6" /></button>
    </div>
    <div className="p-6 space-y-5">
      {image.image_url && <img src={image.image_url} alt="Analyzed leaf" className="max-h-56 mx-auto rounded-xl" />}
      <p className="text-center text-green-700 font-semibold">{t('features.' + image.prediction_status)}</p>
      {image.prediction_status === 'uncertain' ? <h3 className="text-xl font-bold text-center text-amber-800">{t('features.uncertainMessage')}</h3> : <>
        <p className="text-center text-gray-600">{t('features.crop')}: <strong>{image.crop_name}</strong></p>
        <h3 className="text-2xl font-bold text-center text-gray-800">{t('features.disease')}: {image.condition_name}</h3></>}
      <p className="text-center">{t('features.modelConfidence')}: <strong>{(image.confidence * 100).toFixed(1)}%</strong></p>
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-900">
        {t('features.confidenceWarning')}
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <section className="bg-white border rounded-xl p-4"><h4 className="font-bold mb-2">{t('features.symptoms')}</h4>
          <ul className="list-disc pl-5 space-y-1 text-sm">{image.information.symptoms.map(item => <li key={item}>{item}</li>)}</ul></section>
        <section className="bg-white border rounded-xl p-4"><h4 className="font-bold mb-2">{t('features.possibleCauses')}</h4>
          <ul className="list-disc pl-5 space-y-1 text-sm">{image.information.causes.map(item => <li key={item}>{item}</li>)}</ul></section>
        <section className="bg-white border rounded-xl p-4"><h4 className="font-bold mb-2">{t('features.recommendedActions')}</h4>
          <ul className="list-disc pl-5 space-y-1 text-sm">{image.information.actions.map(item => <li key={item}>{item}</li>)}</ul></section>
        <section className="bg-white border rounded-xl p-4"><h4 className="font-bold mb-2">{t('result.prevention')}</h4>
          <ul className="list-disc pl-5 space-y-1 text-sm">{image.information.prevention.map(item => <li key={item}>{item}</li>)}</ul></section>
      </div>
      {image.top_predictions.length > 0 && <section>
        <h4 className="font-semibold mb-3">{t('features.topMatches')}</h4>
        {image.top_predictions.map(match => <div key={match.label} className="mb-3">
          <div className="flex justify-between gap-4 text-sm mb-1"><span>{match.disease}</span><span>{(match.confidence * 100).toFixed(1)}%</span></div>
          <div className="bg-gray-100 h-2 rounded-full"><div className="bg-green-500 h-2 rounded-full" style={{ width: match.confidence * 100 + '%' }} /></div>
        </div>)}
      </section>}
      <section className="bg-green-50 rounded-xl p-5"><h4 className="font-bold text-green-900 mb-2">{image.guidance_source === 'gemini' ? t('result.treatment') : t('features.careGuide')}</h4>
        <p className="text-green-800">{image.recommended_treatment}</p></section>
      <section className="bg-blue-50 rounded-xl p-5"><h4 className="font-bold text-blue-900 mb-2">{t('result.prevention')}</h4>
        <ul className="list-disc pl-5 space-y-2 text-blue-800">{image.prevention_tips.map(tip => <li key={tip}>{tip}</li>)}</ul></section>
      <section>
        <label htmlFor="analysis-notes" className="block font-semibold mb-2">{t('features.notes')}</label>
        <textarea id="analysis-notes" value={notes} onChange={event => setNotes(event.target.value)} maxLength={2000}
          rows={3} placeholder={t('features.notesPlaceholder')}
          className="w-full border rounded-lg p-3 focus:ring-2 focus:ring-green-500" />
        <button onClick={() => void saveNotes()} disabled={isSaving || notes === image.notes}
          className="mt-2 bg-green-600 text-white rounded-lg px-4 py-2 disabled:opacity-50">{t('features.saveNotes')}</button>
      </section>
      <button onClick={downloadReport} className="border border-green-600 text-green-700 rounded-lg px-5 py-2">{t('features.downloadReport')}</button>
      <p className="text-xs text-gray-600">{image.information.disclaimer} Model: {image.model_version}</p>
    </div>
  </dialog>;
}
