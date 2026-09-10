import React from 'react';

/** One before/after signal change — either brand-new (`new_signals`) or
 * deepened (`strengthened_signals`); both shapes share before/after/reason-
 * like fields, so this renders either. */
export default function SignalItem({ signal, isNew }) {
  return (
    <div className="rounded-[14px] border border-white/70 bg-white/55 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[13.5px] font-black text-[#1a1a1a]">{signal.signal}</p>
        {isNew && (
          <span className="shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-black uppercase tracking-wide text-emerald-700">
            New
          </span>
        )}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2 text-[12.5px] font-semibold">
        <div>
          <p className="text-[10px] font-black uppercase tracking-wide text-[#9a9a97]">Before</p>
          <p className="text-[#7a7a76]">{signal.before}</p>
        </div>
        <div>
          <p className="text-[10px] font-black uppercase tracking-wide text-[#9a9a97]">After</p>
          <p className="text-[#1a1a1a]">{signal.after}</p>
        </div>
      </div>
      {(signal.why_it_matters || signal.reason) && (
        <p className="mt-2 text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">
          {signal.why_it_matters || signal.reason}
        </p>
      )}
      {signal.relevance_to_target && (
        <p className="mt-1 text-[12px] font-medium italic leading-relaxed text-[#9a9a97]">{signal.relevance_to_target}</p>
      )}
    </div>
  );
}
