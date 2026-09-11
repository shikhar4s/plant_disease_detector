import { useEffect, useRef, useState, type DragEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { CloudArrowUpIcon, CameraIcon, PhotoIcon } from '@heroicons/react/24/outline';
import { toast } from 'react-hot-toast';
import { usePlantData } from '../../contexts/PlantDataContext';
import { useAuth } from '../../contexts/AuthContext';
import { useAppContext } from '../../contexts/AppContext';
import { api, messageOf } from '../../lib/api';
import type { Analysis } from '../../lib/types';
import ResultCard from './ResultCard';
import ResultModal from './ResultModal';

export default function UploadSection() {
  const { t } = useTranslation();
  const { language } = useAppContext();
  const { reloadUser } = useAuth();
  const { selectedImage, setSelectedImage } = usePlantData();
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [preview, setPreview] = useState('');
  const fileInput = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);
  const inFlight = useRef<AbortController | null>(null);

  useEffect(() => () => { inFlight.current?.abort(); }, []);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  async function handleFiles(files: File[]) {
    if (inFlight.current) return;
    if (files.length !== 1) { toast.error('Choose one leaf photo at a time.'); return; }
    const file = files[0];
    if (!/\.(jpe?g|png|webp)$/i.test(file.name) && !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      toast.error('Choose a JPEG, PNG or WebP image.'); return;
    }
    if (file.size > 10 * 1024 * 1024) { toast.error('The image must be smaller than 10 MB.'); return; }
    const controller = new AbortController();
    inFlight.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 90000);
    setIsAnalyzing(true);
    setPreview(URL.createObjectURL(file));
    setSelectedImage(null);
    const form = new FormData();
    form.append('image', file);
    try {
      const result = await api<Analysis>('/api/plant_doctor_ai/analyze/', {
        method: 'POST', headers: { Language: language }, body: form, signal: controller.signal,
      });
      setSelectedImage(result);
      setShowResult(true);
      setPreview('');
      toast.success(t('features.analysisSaved'));
      void reloadUser().catch(() => {});
    } catch (error) {
      if (!controller.signal.aborted) toast.error(messageOf(error));
      else if (inFlight.current === controller) toast.error('Analysis timed out. Please try again.');
    } finally {
      window.clearTimeout(timeout);
      inFlight.current = null;
      setIsAnalyzing(false);
    }
  }
  function drop(event: DragEvent) {
    event.preventDefault();
    setIsDragging(false);
    void handleFiles(Array.from(event.dataTransfer.files));
  }

  return <div className="max-w-4xl mx-auto">
    <div className="mb-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-2">{t('dashboard.upload.title')}</h1>
      <p className="text-gray-600">{t('dashboard.upload.subtitle')}</p>
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div className="space-y-5">
        <div onDragOver={event => { event.preventDefault(); if (!isAnalyzing) setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)} onDrop={drop}
          className={'border-2 border-dashed rounded-xl p-8 text-center transition-colors ' +
            (isDragging ? 'border-green-500 bg-green-50' : 'border-gray-300 bg-white/50')}>
          <CloudArrowUpIcon className="w-14 h-14 text-green-600 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-800 mb-2">{t('dashboard.upload.dropZone')}</h2>
          <p className="text-sm text-gray-600 mb-5">JPEG, PNG, WebP · 10 MB · 12 MP</p>
          <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
            onChange={event => { void handleFiles(Array.from(event.target.files || [])); event.target.value = ''; }} />
          <input ref={cameraInput} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden"
            onChange={event => { void handleFiles(Array.from(event.target.files || [])); event.target.value = ''; }} />
          <div className="flex flex-wrap justify-center gap-3">
            <button disabled={isAnalyzing} onClick={() => fileInput.current?.click()}
              className="bg-green-600 text-white px-5 py-3 rounded-lg disabled:opacity-50">{t('dashboard.upload.chooseFile')}</button>
            <button disabled={isAnalyzing} onClick={() => cameraInput.current?.click()}
              className="bg-white border border-green-600 text-green-700 px-4 py-3 rounded-lg inline-flex gap-2 disabled:opacity-50">
              <CameraIcon className="w-5 h-5" />{t('features.camera')}
            </button>
          </div>
        </div>
        {isAnalyzing && <div role="status" className="bg-white rounded-xl p-5 flex items-center gap-4">
          <span className="animate-spin rounded-full h-7 w-7 border-2 border-green-600 border-t-transparent" />
          <div><p className="font-semibold">{t('dashboard.upload.analyzing')}</p>
            <p className="text-sm text-gray-600">The first scan can take longer while the server wakes up.</p></div>
        </div>}
        <div className="bg-green-50 border border-green-200 rounded-xl p-5 text-sm text-green-900 space-y-2">
          <h2 className="font-semibold">{t('features.photoTips')}</h2>
          <p>Use one leaf, natural daylight and a plain background. Include the affected area and avoid blur.</p>
          <p>Check Supported plants before scanning. The model always chooses from its trained classes and cannot reliably reject unrelated photos.</p>
        </div>
      </div>
      <div>
        {selectedImage ? <ResultCard image={selectedImage} onDetails={() => setShowResult(true)} /> :
          <div className="bg-white/60 rounded-xl p-8 text-center">
            {preview ? <img src={preview} alt="Selected leaf" className="max-h-72 mx-auto rounded-lg mb-4" /> :
              <PhotoIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />}
            <h2 className="text-lg font-semibold text-gray-600">{t('dashboard.upload.noAnalysis')}</h2>
            <p className="text-gray-500">{t('dashboard.upload.noAnalysisSubtext')}</p>
          </div>}
      </div>
    </div>
    {selectedImage && <ResultModal image={selectedImage} isOpen={showResult} onClose={() => setShowResult(false)}
      onUpdate={setSelectedImage} />}
  </div>;
}
