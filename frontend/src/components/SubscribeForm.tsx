import { useState } from 'react';
import { subscribe } from '../lib/api';

export default function SubscribeForm() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;

    setStatus('loading');
    try {
      const res = await subscribe(email);
      setStatus('success');
      setMessage(res.message);
      setEmail('');
    } catch {
      setStatus('error');
      setMessage('error: try again');
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input
        type="email"
        value={email}
        onChange={(e) => {
          setEmail(e.target.value);
          if (status !== 'idle') setStatus('idle');
        }}
        placeholder="email@addr"
        required
        className="bg-[#0d120d] border border-[#1a2a1a] px-2 py-1.5 text-[11px] text-[#6a7a6a] placeholder-[#2a3a2a] focus:outline-none focus:border-[#4ade80]/40 w-40"
      />
      <button
        type="submit"
        disabled={status === 'loading'}
        className="border border-[#4ade80]/40 text-[#4ade80] text-[11px] px-3 py-1.5 hover:bg-[#4ade80]/10 disabled:border-[#1a2a1a] disabled:text-[#3a4a3a] transition-colors whitespace-nowrap"
      >
        {status === 'loading' ? 'wait...' : '> subscribe'}
      </button>
      {status === 'success' && (
        <span className="text-[#4ade80] text-[10px]">{message}</span>
      )}
      {status === 'error' && (
        <span className="text-[#f87171] text-[10px]">{message}</span>
      )}
    </form>
  );
}
