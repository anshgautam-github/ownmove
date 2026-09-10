import React, { useEffect, useState } from 'react';
import { startConversation, sendMessage, getConversations, getConversation, deleteConversation } from '../../services/api/aiCoach';
import { getCache, setCache, clearCache } from '../../services/api/localCache';
import { Pill } from './ui';
import { STARTER_CARDS } from './coach/starterConfig';
import ConversationView from './coach/ConversationView';
import ConversationHistoryList from './coach/ConversationHistoryList';
import AnalysisSkeleton from './cards/AnalysisSkeleton';

/**
 * Career AI's "AI Coach" pane. Same state-machine shape as the other
 * Career AI dashboards: never computes a recommendation itself, only
 * renders whatever the backend returns and collects what the user types.
 *
 * `profile` is passed down from AppShell (already loaded once for the
 * whole shell) instead of being fetched again here — see the same note in
 * CareerRoadmapDashboard.jsx.
 *
 * Unlike Career Roadmap (one resource) or Career Simulation (flat
 * append-only history), AI Coach is conversational — a conversation holds
 * many messages — so this container centers on a landing screen (starter
 * cards + recent conversations) and an active conversation view.
 *
 * States: 'loading-initial' -> 'landing' (starter cards + ask box + recent
 * conversations) -> 'conversation' (an active thread) -> 'error'.
 *
 * `onNavigateTab` (passed from AppShell) lets a routing suggestion inside
 * a coaching reply switch the Career AI sidebar to another existing tab
 * (Profile Analysis / Career Roadmap / Career Simulation / Opportunity
 * Matcher) rather than inventing a route.
 */
const CONVERSATIONS_CACHE_KEY = 'ai-coach:conversations';
const conversationCacheKey = (id) => `ai-coach:conversation:${id}`;

export default function CareerCoachDashboard({ profile, onNavigateTab }) {
  // Hydrated synchronously from `localCache` via lazy useState initializers
  // — a revisit (or even a full page reload within the session) renders in
  // its final state on the very first paint with zero network calls. See
  // the identical pattern (and the reasoning behind it) in
  // ProfileAnalysisDashboard.jsx.
  const [status, setStatus] = useState(() => (getCache(CONVERSATIONS_CACHE_KEY) === undefined ? 'loading-initial' : 'landing'));
  const [conversations, setConversations] = useState(() => getCache(CONVERSATIONS_CACHE_KEY) || []);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (getCache(CONVERSATIONS_CACHE_KEY) !== undefined) return; // already hydrated above — nothing to fetch
    let active = true;
    (async () => {
      try {
        const conversationList = await getConversations();
        if (!active) return;
        setConversations(conversationList || []);
        setStatus('landing');
        setCache(CONVERSATIONS_CACHE_KEY, conversationList || []);
      } catch (error) {
        if (!active) return;
        setErrorMessage(error.message || 'Could not load AI Coach.');
        setStatus('error');
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const refreshConversations = async () => {
    try {
      const conversationList = (await getConversations()) || [];
      setConversations(conversationList);
      setCache(CONVERSATIONS_CACHE_KEY, conversationList);
    } catch {
      // Non-fatal — the active conversation is still usable either way.
    }
  };

  const goToLanding = () => {
    setActiveConversation(null);
    setMessages([]);
    setStatus('landing');
  };

  const handleAsk = async (message) => {
    const trimmed = message.trim();
    if (!trimmed) return;
    setSending(true);
    setErrorMessage('');
    setStatus('conversation');
    try {
      const result = await startConversation(trimmed);
      const nextMessages = [result.user_message, result.assistant_message];
      setActiveConversation(result.conversation);
      setMessages(nextMessages);
      setCache(conversationCacheKey(result.conversation.id), { ...result.conversation, messages: nextMessages });
      refreshConversations();
    } catch (error) {
      setErrorMessage(error.message || 'Something went wrong starting that conversation.');
      setStatus('error');
    } finally {
      setSending(false);
    }
  };

  const handleSend = async (message) => {
    if (!activeConversation) return;
    setSending(true);
    setMessages((prev) => [...prev, { id: `pending-${Date.now()}`, role: 'user', content: message }]);
    try {
      const result = await sendMessage(activeConversation.id, message);
      setMessages((prev) => {
        const nextMessages = [...prev.slice(0, -1), result.user_message, result.assistant_message];
        setCache(conversationCacheKey(activeConversation.id), { ...result.conversation, messages: nextMessages });
        return nextMessages;
      });
      setActiveConversation(result.conversation);
    } catch (error) {
      setErrorMessage(error.message || 'Something went wrong sending that message.');
    } finally {
      setSending(false);
    }
  };

  // Reopening a conversation you've already loaded this session is a pure
  // cache read — no database call — since every mutation (start/send) above
  // keeps that conversation's cache entry current as it happens.
  const handleOpenConversation = async (id) => {
    setStatus('conversation');
    setSending(true);
    setErrorMessage('');
    const cached = getCache(conversationCacheKey(id));
    if (cached) {
      setActiveConversation(cached);
      setMessages(cached.messages || []);
      setSending(false);
      return;
    }
    try {
      const detail = await getConversation(id);
      setActiveConversation(detail);
      setMessages(detail.messages || []);
      setCache(conversationCacheKey(id), detail);
    } catch (error) {
      setErrorMessage(error.message || 'Could not open that conversation.');
      setStatus('error');
    } finally {
      setSending(false);
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await deleteConversation(id);
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id);
        setCache(CONVERSATIONS_CACHE_KEY, next);
        return next;
      });
      clearCache(conversationCacheKey(id));
    } catch (error) {
      setErrorMessage(error.message || 'Could not delete that conversation.');
    }
  };

  if (status === 'loading-initial') {
    return <AnalysisSkeleton />;
  }

  if (status === 'error') {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col items-center justify-center gap-3 rounded-[20px] border border-dashed border-white/70 bg-white/40 px-6 py-14 text-center">
        <span className="rounded-full bg-red-50 px-3 py-1 text-[11px] font-black uppercase tracking-wide text-red-600">
          Something went wrong
        </span>
        <p className="max-w-sm text-[14px] font-semibold text-[#7a7a76]">{errorMessage}</p>
        <button
          type="button"
          onClick={goToLanding}
          className="mt-1 rounded-full bg-[#161616] px-4 py-2 text-[13.5px] font-bold text-white transition hover:bg-[#2a2a2a]"
        >
          Back to AI Coach
        </button>
      </div>
    );
  }

  if (status === 'conversation') {
    return (
      <ConversationView
        conversation={activeConversation}
        messages={messages}
        onSend={handleSend}
        sending={sending}
        onNavigateTab={onNavigateTab}
        onBack={goToLanding}
      />
    );
  }

  // status === 'landing'
  return <CoachLanding profile={profile} conversations={conversations} onAsk={handleAsk} onOpen={handleOpenConversation} onDelete={handleDeleteConversation} />;
}

function CoachLanding({ profile, conversations, onAsk, onOpen, onDelete }) {
  const [draft, setDraft] = useState('');

  const handleStarterClick = (card) => {
    setDraft(card.prompt);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!draft.trim()) return;
    onAsk(draft);
  };

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="relative mb-7 text-center">
        <div className="pointer-events-none absolute left-1/2 top-0 h-32 w-64 -translate-x-1/2 -translate-y-6 rounded-full bg-[radial-gradient(circle,rgba(123,98,232,0.18)_0%,transparent_70%)] blur-xl" />
        <p className="relative mx-auto max-w-sm text-[19px] font-black leading-tight tracking-tight text-[#1a1a1a] sm:text-[21px]">
          Think through your next career move.
        </p>
        <p className="relative mx-auto mt-2 max-w-md text-[13.5px] font-medium text-[#7a7a76]">
          Get context-aware guidance based on your profile, goals, and current situation.
        </p>
        <div className="relative mt-4 flex flex-wrap items-center justify-center gap-1.5">
          <Pill tone="accent" className="normal-case">
            Coaching with your profile
          </Pill>
          {profile?.targetRole && (
            <Pill tone="default" className="normal-case">
              Target: {profile.targetRole}
            </Pill>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {STARTER_CARDS.map((card) => (
          <button
            key={card.key}
            type="button"
            onClick={() => handleStarterClick(card)}
            className="group relative overflow-hidden rounded-[18px] border border-white/70 bg-white/70 p-4 text-left shadow-[0_10px_24px_-18px_rgba(40,50,30,0.3)] transition duration-200 hover:-translate-y-0.5 hover:border-[#ded6fb] hover:bg-white/95 hover:shadow-[0_18px_32px_-16px_rgba(123,98,232,0.28)]"
          >
            <span
              className="absolute inset-y-0 left-0 w-[3px] bg-[linear-gradient(180deg,#7b62e8_0%,#5c63ff_100%)] opacity-0 transition-opacity duration-200 group-hover:opacity-100"
              aria-hidden="true"
            />
            <div className="flex items-start justify-between gap-2">
              <p className="text-[14px] font-black text-[#1a1a1a]">{card.label}</p>
              <span className="flex h-6 w-6 shrink-0 -translate-x-1 items-center justify-center rounded-full bg-[#f3efff] text-[#7b62e8] opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
              </span>
            </div>
            <p className="mt-1.5 text-[13px] font-medium text-[#7a7a76]">&ldquo;{card.example}&rdquo;</p>
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="relative mt-4 flex items-center gap-2">
        <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#b3aef0]">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
            <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" />
          </svg>
        </span>
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask AI Coach..."
          className="w-full flex-1 rounded-full border border-white/70 bg-white/85 py-3 pl-10 pr-4 text-[14px] font-semibold text-[#1a1a1a] shadow-[inset_0_1px_0_rgba(255,255,255,0.9)] outline-none transition placeholder:text-[#b3b3af] placeholder:transition-colors focus:border-[#7b62e8]/50 focus:shadow-[0_0_0_3px_rgba(123,98,232,0.12)] focus:placeholder:text-[#6b6b66]"
        />
        <button
          type="submit"
          disabled={!draft.trim()}
          className="shrink-0 rounded-full bg-[#161616] px-5 py-3 text-[13.5px] font-bold text-white transition hover:bg-[#2a2a2a] disabled:cursor-not-allowed disabled:opacity-40"
        >
          Ask
        </button>
      </form>

      {conversations.length > 0 && (
        <div className="mt-9 border-t border-[#111827]/8 pt-6">
          <p className="mb-2.5 text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">Recent Conversations</p>
          <ConversationHistoryList conversations={conversations} onOpen={onOpen} onDelete={onDelete} />
        </div>
      )}
    </div>
  );
}
