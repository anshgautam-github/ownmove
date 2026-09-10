import React from 'react';
import { Pill } from '../ui';
import { TYPE_LABELS } from './typeConfig';

const VERDICT_TONE = { high_value: 'positive', useful: 'accent', limited_value: 'warning', low_value: 'high' };
const VERDICT_LABEL = { high_value: 'High Value', useful: 'Useful', limited_value: 'Limited Value', low_value: 'Low Value' };

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/** A lightweight "Recent Simulations" list — scenario, target role,
 * verdict, date, and nothing more (no analytics over history, per the
 * feature spec). Clicking a row opens that past simulation. */
export default function RecentSimulations({ items, onOpen, onDelete }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      {items.map((item) => (
        <div
          key={item.id}
          role="button"
          tabIndex={0}
          className="group relative flex items-center justify-between gap-3 rounded-[14px] border border-white/70 bg-white/55 px-3.5 py-2.5 text-left transition hover:bg-white/80 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7b62e8]"
          onClick={() => onOpen(item.id)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              onOpen(item.id);
            }
          }}
        >
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13.5px] font-black text-[#1a1a1a]">{item.scenario_title}</p>
            <p className="mt-0.5 text-[12px] font-medium text-[#9a9a97]">
              {TYPE_LABELS[item.simulation_type] || item.simulation_type} · {item.target_role} · {formatDate(item.created_at)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {item.status === 'failed' ? (
              <Pill tone="high">Failed</Pill>
            ) : item.verdict ? (
              <Pill tone={VERDICT_TONE[item.verdict] || 'default'}>{VERDICT_LABEL[item.verdict] || item.verdict}</Pill>
            ) : (
              <Pill tone="default">Comparison</Pill>
            )}
            
            {onDelete && (
              <button
                type="button"
                className="flex h-6 w-6 items-center justify-center rounded-full bg-black/5 text-black/40 opacity-0 transition-opacity hover:bg-black/10 hover:text-black group-hover:opacity-100"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(item.id);
                }}
                title="Remove simulation"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
