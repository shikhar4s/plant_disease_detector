import { useEffect, useRef, useState } from 'react';
import { CameraIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { useTranslation } from 'react-i18next';

type CameraCaptureProps = { disabled: boolean; onCapture: (file: File) => void };

export default function CameraCapture({ disabled, onCapture }: CameraCaptureProps) {
  const { t, i18n } = useTranslation();
  const hi = i18n.language.startsWith('hi');
  const [open, setOpen] = useState(false);
  const [ready, setReady] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [error, setError] = useState('');
  const dialog = useRef<HTMLDialogElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const request = useRef(0);
  const nativeInput = useRef<HTMLInputElement>(null);

  useEffect(() => () => {
    request.current += 1;
    stream.current?.getTracks().forEach(track => track.stop());
  }, []);

  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal();
  }, [open]);

  function stop() {
    request.current += 1;
    stream.current?.getTracks().forEach(track => track.stop());
    stream.current = null;
    if (video.current) video.current.srcObject = null;
    dialog.current?.close();
    setOpen(false);
    setReady(false);
    setCapturing(false);
  }

  async function start() {
    if (disabled || open) return;
    setError('');
    setReady(false);
    setOpen(true);
    const attempt = ++request.current;
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setError(hi ? 'इस ब्राउज़र में लाइव कैमरा उपलब्ध नहीं है। HTTPS पर ऐप खोलें या नीचे कैमरा/फ़ोटो विकल्प चुनें।' : 'Live camera is unavailable in this browser. Open the app over HTTPS or use the camera/photo picker below.');
      return;
    }
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
      if (attempt !== request.current) { media.getTracks().forEach(track => track.stop()); return; }
      stream.current = media;
      if (video.current) {
        video.current.srcObject = media;
        await video.current.play();
      }
    } catch (cause) {
      if (attempt !== request.current) return;
      stream.current?.getTracks().forEach(track => track.stop());
      stream.current = null;
      const name = cause instanceof DOMException ? cause.name : '';
      setError(name === 'NotAllowedError' || name === 'SecurityError'
        ? (hi ? 'कैमरे की अनुमति नहीं मिली। ब्राउज़र की साइट सेटिंग में अनुमति दें, या फ़ोटो चुनें।' : 'Camera permission was denied. Allow camera access in your browser site settings, or choose a photo.')
        : name === 'NotFoundError'
          ? (hi ? 'इस डिवाइस पर कैमरा नहीं मिला। फ़ोटो चुनें।' : 'No camera was found on this device. Choose a photo instead.')
          : (hi ? 'कैमरा शुरू नहीं हो सका। दूसरे ऐप में कैमरा बंद करें और फिर कोशिश करें, या फ़ोटो चुनें।' : 'The camera could not start. Close other apps using it and try again, or choose a photo.'));
    }
  }

  function capture() {
    if (!video.current?.videoWidth || !ready || capturing) return;
    const frame = video.current;
    const canvas = document.createElement('canvas');
    const scale = Math.min(1, 1920 / Math.max(frame.videoWidth, frame.videoHeight));
    canvas.width = Math.round(frame.videoWidth * scale);
    canvas.height = Math.round(frame.videoHeight * scale);
    const context = canvas.getContext('2d');
    if (!context) return;
    context.drawImage(frame, 0, 0, canvas.width, canvas.height);
    const attempt = request.current;
    setCapturing(true);
    canvas.toBlob(blob => {
      if (attempt !== request.current) return;
      setCapturing(false);
      if (!blob) {
        setError(hi ? 'फ़ोटो कैप्चर नहीं हो सकी। फिर कोशिश करें।' : 'Could not capture the photo. Please try again.');
        return;
      }
      onCapture(new File([blob], `plantdoc-leaf-${Date.now()}.jpg`, { type: 'image/jpeg' }));
      stop();
    }, 'image/jpeg', 0.92);
  }

  return <>
    <button type="button" disabled={disabled} onClick={() => void start()}
      className="bg-white border border-green-600 text-green-700 px-4 py-3 rounded-lg inline-flex gap-2 disabled:opacity-50">
      <CameraIcon className="w-5 h-5" />{t('features.camera')}
    </button>
    <input ref={nativeInput} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden"
      onChange={event => {
        const file = event.target.files?.[0];
        if (file) { onCapture(file); stop(); }
        event.target.value = '';
      }} />
    {open && <dialog ref={dialog} onCancel={event => { event.preventDefault(); stop(); }}
      aria-labelledby="camera-title" aria-describedby="camera-instructions"
      className="w-[min(94vw,640px)] rounded-2xl p-5 backdrop:bg-black/60">
      <div className="flex items-center justify-between gap-4 mb-3">
        <h2 id="camera-title" className="text-xl font-semibold">{hi ? 'पत्ते की फ़ोटो लें' : 'Photograph the leaf'}</h2>
        <button type="button" onClick={stop} aria-label={hi ? 'कैमरा बंद करें' : 'Close camera'} className="p-2 rounded-lg border">
          <XMarkIcon className="w-5 h-5" />
        </button>
      </div>
      <p id="camera-instructions" className="text-sm text-gray-600 mb-3">{hi ? 'एक पत्ता अच्छी रोशनी में रखें। फ़ोटो लेने के बाद आप उसे देखकर जाँच शुरू कर सकते हैं।' : 'Place one leaf in good light. You can review the photo before starting a diagnosis.'}</p>
      <video ref={video} autoPlay muted playsInline onLoadedData={() => setReady(true)}
        aria-label={hi ? 'लाइव कैमरा पूर्वावलोकन' : 'Live camera preview'} className="w-full max-h-[55vh] bg-gray-950 rounded-xl" />
      {!ready && !error && <p role="status" className="text-sm mt-3">{hi ? 'कैमरे की अनुमति दें और पूर्वावलोकन का इंतज़ार करें।' : 'Allow camera access and wait for the preview.'}</p>}
      {error && <p role="alert" className="error-panel mt-3">{error}</p>}
      <div className="flex flex-wrap gap-3 mt-4">
        <button type="button" onClick={capture} disabled={!ready || capturing || !!error} className="primary-button disabled:opacity-50">{hi ? 'फ़ोटो लें' : 'Capture photo'}</button>
        <button type="button" onClick={() => nativeInput.current?.click()} className="secondary-button">{hi ? 'कैमरा / फ़ोटो चुनें' : 'Camera / photo picker'}</button>
        <button type="button" onClick={stop} className="secondary-button">{hi ? 'रद्द करें' : 'Cancel'}</button>
      </div>
    </dialog>}
  </>;
}

