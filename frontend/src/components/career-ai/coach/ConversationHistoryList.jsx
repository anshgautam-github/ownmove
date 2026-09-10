import React from 'react';
import { Pill } from '../ui';

const TYPE_LABELS = {
  decision: 'Decision',
  prioritization: 'Prioritization',
  evaluation: 'Evaluation',
  problem_solving: 'Problem Solving',
  preparation: 'Preparation',
  general: 'General',
};

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/** Lightweight conversation history — open or delete a past conversation.
 * No folders, tags, or search, per the feature spec's explicit V1 scope. */
export default function ConversationHistoryList({ conversations, onOpen, onDelete }) {
  if (!conversations || conversations.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      {conversations.map((conversation) => (
        <div
          key={conversation.id}
          className="flex items-center justify-between gap-3 rounded-[14px] border border-white/70 bg-white/55 px-3.5 py-2.5 transition hover:bg-white/80"
        >
          <button type="button" onClick={() => onOpen(conversation.id)} className="min-w-0 flex-1 text-left">
            <p className="truncate text-[13.5px] font-black text-[#1a1a1a]">{conversation.title || 'Untitled conversation'}</p>
            <p className="mt-0.5 text-[12px] font-medium text-[#9a9a97]">{formatDate(conversation.updated_at)}</p>
          </button>
          <div className="flex shrink-0 items-center gap-1.5">
            {conversation.conversation_type && (
              <Pill tone="default" className="normal-case">
                {TYPE_LABELS[conversation.conversation_type] || conversation.conversation_type}
              </Pill>
            )}
            <button
              type="button"
              onClick={() => onDelete(conversation.id)}
              title="Delete conversation"
              className="flex h-6 w-6 items-center justify-center rounded-full text-[#9a9a97] transition hover:bg-red-50 hover:text-red-600"
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
