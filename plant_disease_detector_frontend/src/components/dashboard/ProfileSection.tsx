import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { UserIcon, CameraIcon } from '@heroicons/react/24/outline';
import { toast } from 'react-hot-toast';
import { useAuth } from '../../contexts/AuthContext';
import { messageOf } from '../../lib/api';

export default function ProfileSection() {
  const { t } = useTranslation();
  const { user, logout, updateProfile, reloadUser } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [saving, setSaving] = useState(false);
  const photoInput = useRef<HTMLInputElement>(null);
  useEffect(() => { void reloadUser().catch(error => toast.error(messageOf(error))); }, [reloadUser]);
  useEffect(() => { setName(user?.name || ''); }, [user?.name]);

  async function save() {
    if (!name.trim()) { toast.error('Enter your full name.'); return; }
    setSaving(true);
    try { await updateProfile({ full_name: name.trim() }); toast.success(t('features.profileSaved')); }
    catch (error) { toast.error(messageOf(error)); } finally { setSaving(false); }
  }
  async function changePhoto(file: File | undefined) {
    if (!file) return;
    if (file.size > 3 * 1024 * 1024) { toast.error('Profile photos must be smaller than 3 MB.'); return; }
    setSaving(true);
    const form = new FormData();
    form.append('photo', file);
    try { await updateProfile(form); toast.success(t('features.profileSaved')); }
    catch (error) { toast.error(messageOf(error)); } finally { setSaving(false); }
  }
  return <div className="max-w-4xl mx-auto">
    <h1 className="text-3xl font-bold text-gray-800 mb-2">{t('dashboard.profile.title')}</h1>
    <p className="text-gray-600 mb-8">{t('dashboard.profile.subtitle')}</p>
    <div className="grid lg:grid-cols-3 gap-6">
      <form className="lg:col-span-2 bg-white/80 rounded-xl p-6 space-y-6" onSubmit={event => { event.preventDefault(); void save(); }}>
        <div className="flex items-center gap-4">
          {user?.photo_url ? <img src={user.photo_url} alt="Your profile" className="w-20 h-20 rounded-full object-cover" /> :
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center"><UserIcon className="w-10 h-10 text-green-600" /></div>}
          <div><h2 className="font-semibold text-lg">{user?.name}</h2>
            <input ref={photoInput} className="hidden" type="file" accept="image/jpeg,image/png,image/webp"
              onChange={event => { void changePhoto(event.target.files?.[0]); event.target.value = ''; }} />
            <button type="button" disabled={saving} onClick={() => photoInput.current?.click()} className="text-green-700 mt-2 inline-flex gap-2">
              <CameraIcon className="w-5 h-5" />{t('dashboard.profile.changePhoto')}</button>
          </div>
        </div>
        <div><label htmlFor="profile-name" className="block text-sm font-medium mb-2">{t('dashboard.profile.fullName')}</label>
          <input id="profile-name" value={name} maxLength={255} required onChange={event => setName(event.target.value)} className="w-full rounded-lg border p-3" /></div>
        <div><label htmlFor="profile-email" className="block text-sm font-medium mb-2">{t('dashboard.profile.emailAddress')}</label>
          <input id="profile-email" value={user?.email || ''} readOnly className="w-full rounded-lg border p-3 bg-gray-50 text-gray-600" />
          <p className="text-xs text-gray-500 mt-2">Your sign-in email is fixed for this account.</p></div>
        <div className="flex flex-wrap gap-3">
          <button disabled={saving || name === user?.name} className="bg-green-600 text-white px-5 py-3 rounded-lg disabled:opacity-50">{t('dashboard.profile.save')}</button>
          <button type="button" onClick={logout} className="border border-red-300 text-red-600 px-5 py-3 rounded-lg">{t('dashboard.profile.signOut')}</button>
        </div>
      </form>
      <div className="bg-white/80 rounded-xl p-6 h-fit">
        <h2 className="font-semibold text-lg mb-5">{t('dashboard.profile.accountStats')}</h2>
        <dl className="space-y-5">
          <div><dt className="text-gray-600 text-sm">{t('dashboard.analytics.totalUploads')}</dt><dd className="font-bold text-xl">{user?.total_uploads || 0}</dd></div>
          <div><dt className="text-gray-600 text-sm">{t('features.savedResults')}</dt><dd className="font-bold text-xl">{user?.saved_analyses || 0}</dd></div>
          <div><dt className="text-gray-600 text-sm">{t('dashboard.profile.memberSince')}</dt>
            <dd className="font-semibold">{user?.date_joined ? new Date(user.date_joined).toLocaleDateString() : '—'}</dd></div>
        </dl>
      </div>
    </div>
  </div>;
}
