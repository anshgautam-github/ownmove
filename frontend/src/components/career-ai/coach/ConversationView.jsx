import React, { useEffect, useRef, useState } from 'react';
import AssistantMessage from './AssistantMessage';

function UserMessage({ message }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-[16px] rounded-tr-[4px] bg-[#161616] p-3.5 text-white">
        <p className="text-[14px] font-semibold leading-relaxed">{message.content}</p>
      </div>
    </div>
  );
}

/**
 * The active conversation thread — user messages get conventional
 * conversation bubbles; assistant messages render structured content via
 * AssistantMessage. Deliberately not styled identically to a generic chat
 * clone (asymmetric bubble treatment, no avatars-everywhere, structured
 * cards instead of a wall of prose).
 */
export default function ConversationView({ conversation, messages, onSend, sending, onNavigateTab, onBack }) {
  const [draft, setDraft] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages.length, sending]);

  const handleSubmit = (event) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || sending) return;
    setDraft('');
    onSend(trimmed);
  };

  return (
    <div className="mx-auto flex h-full w-full max-w-3xl flex-col">
      <div className="mb-3 flex shrink-0 items-center justify-between gap-2">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 rounded-full border border-white/70 bg-white/75 px-3 py-1.5 text-[12.5px] font-bold text-[#4a4a48] transition hover:bg-white/90"
        >
          ← Back
        </button>
        <p className="truncate text-[13.5px] font-bold text-[#7a7a76]">{conversation?.title || 'New conversation'}</p>
        <span />
      </div>

      <div ref={scrollRef} className="custom-scroll min-h-0 flex-1 overflow-y-auto overflow-x-hidden pr-1">
        <div className="flex flex-col gap-4 pb-3">
          {messages.map((message) =>
            message.role === 'user' ? (
              <UserMessage key={message.id} message={message} />
            ) : (
              <AssistantMessage key={message.id} message={message} onNavigateTab={onNavigateTab} />
            )
          )}
          {sending && (
            <div className="flex items-center gap-2 text-[13px] font-bold text-[#9a9a97]">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#7b62e8]" />
              Thinking...
            </div>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-3 flex shrink-0 items-center gap-2">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask a follow-up..."
          disabled={sending}
          className="w-full flex-1 rounded-full border border-white/70 bg-white/85 px-4 py-2.5 text-[14px] font-semibold text-[#1a1a1a] outline-none transition placeholder:text-[#b3b3af] placeholder:transition-colors focus:border-[#7b62e8]/50 focus:placeholder:text-[#6b6b66] disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={sending || !draft.trim()}
          className="shrink-0 rounded-full bg-[#161616] px-4 py-2.5 text-[13.5px] font-bold text-white transition hover:bg-[#2a2a2a] disabled:cursor-not-allowed disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  );
}
