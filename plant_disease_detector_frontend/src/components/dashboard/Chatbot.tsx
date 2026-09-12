import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChatBubbleLeftRightIcon, XMarkIcon, PaperAirplaneIcon } from '@heroicons/react/24/outline';
import { Leaf } from 'lucide-react';
import { useAppContext } from '../../contexts/AppContext';
import { usePlantData } from '../../contexts/PlantDataContext';
import { api, messageOf } from '../../lib/api';

interface Message { id: string; text: string; isUser: boolean }

export default function Chatbot({ embedded = false }: { embedded?: boolean }) {
  const { t } = useTranslation();
  const { language } = useAppContext();
  const { selectedImage, weatherContextId, mandiContextId } = usePlantData();
  const [isOpen, setIsOpen] = useState(embedded);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [mode, setMode] = useState('');
  const [error, setError] = useState('');
  const end = useRef<HTMLDivElement>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => { if (isOpen) end.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isOpen]);
  useEffect(() => () => { controller.current?.abort(); }, []);

  async function send() {
    const text = input.trim();
    if (!text || controller.current) return;
    const request = new AbortController();
    controller.current = request;
    const timer = window.setTimeout(() => request.abort(), 45000);
    setIsTyping(true);
    setError('');
    // History excludes the newly submitted message; the server adds it exactly once.
    const history = messages.slice(-20).map(message => ({
      role: message.isUser ? 'user' : 'model', parts: [{ text: message.text }],
    }));
    try {
      const response = await api<{ response: string; mode: string }>('/api/plant_doctor_ai/chat/', {
        method: 'POST', headers: { Language: language }, signal: request.signal,
        body: JSON.stringify({ history, newMessage: text, ...(selectedImage ? { analysisId: selectedImage.id } : {}),
          ...(weatherContextId ? { weatherContextId } : {}), ...(mandiContextId ? { mandiContextId } : {}) }),
      });
      setMessages(previous => [...previous,
        { id: crypto.randomUUID(), text, isUser: true },
        { id: crypto.randomUUID(), text: response.response, isUser: false }]);
      setInput('');
      setMode(response.mode);
    } catch (error) {
      if (!request.signal.aborted) setError(messageOf(error));
      else setError('The assistant took too long to respond. Please try again.');
    } finally {
      window.clearTimeout(timer);
      controller.current = null;
      setIsTyping(false);
    }
  }
  return <div className={embedded ? 'max-w-5xl mx-auto' : 'fixed bottom-4 right-4 z-40'}>
    {isOpen && <section aria-label={t('chatbot.title')} className={'bg-white rounded-2xl shadow-lg border flex flex-col ' + (embedded ? 'w-full h-[70vh]' : 'w-80 max-w-[calc(100vw-2rem)] h-[28rem] max-h-[75vh] mb-3')}>
      <div className="bg-gradient-to-r from-green-500 to-emerald-600 text-white p-4 rounded-t-2xl flex justify-between items-center">
        <div className="flex items-center gap-2"><Leaf className="w-6 h-6" /><div>
          <h2 className="font-semibold">PlantDoc Assistant</h2>
          <p className="text-xs">{mode === 'care-guide' ? t('features.chatGuide') : t('features.chatAI')}</p></div></div>
        {!embedded && <button onClick={() => setIsOpen(false)} aria-label={t('features.close')} className="p-1"><XMarkIcon className="w-5 h-5" /></button>}
      </div>
      {selectedImage && <p className="px-4 py-2 bg-green-50 text-xs text-green-800">{t('features.askAboutResult')}: {selectedImage.disease}</p>}
      <div role="log" aria-live="polite" className="flex-1 overflow-y-auto p-4 space-y-3">
        {!messages.length && <p className="text-sm text-gray-600">{t('chatbot.greeting')}</p>}
        {messages.map(message => <div key={message.id} className={'flex ' + (message.isUser ? 'justify-end' : 'justify-start')}>
          <p className={'max-w-[90%] whitespace-pre-wrap break-words rounded-2xl px-3 py-2 text-sm ' +
            (message.isUser ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-800')}>{message.text}</p>
        </div>)}
        {isTyping && <p role="status" className="text-sm text-green-700">{t('features.loading')}</p>}
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <div ref={end} />
      </div>
      <form onSubmit={event => { event.preventDefault(); void send(); }} className="border-t p-3">
        <div className="flex gap-2"><input aria-label={t('chatbot.placeholder')} placeholder={t('chatbot.placeholder')} value={input}
          onChange={event => setInput(event.target.value)} disabled={isTyping} maxLength={4096} className="min-w-0 flex-1 border rounded-full px-4 py-2 text-sm" />
          <button disabled={isTyping || !input.trim()} aria-label={t('features.send')} className="p-2 bg-green-600 text-white rounded-full disabled:opacity-50">
            <PaperAirplaneIcon className="w-5 h-5" /></button></div>
        <button type="button" disabled={isTyping} onClick={() => { setMessages([]); setError(''); setMode(''); }} className="text-xs text-gray-500 mt-2 underline">{t('features.clearChat')}</button>
      </form>
    </section>}
    {!embedded && <button onClick={() => setIsOpen(value => !value)} aria-expanded={isOpen} aria-label={t('features.openChat')}
      className="bg-gradient-to-r from-green-500 to-emerald-600 text-white p-4 rounded-full shadow-lg">
      <ChatBubbleLeftRightIcon className="w-6 h-6" /></button>}
  </div>;
}
