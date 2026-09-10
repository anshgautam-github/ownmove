import React, { useState } from 'react';
import { Pill, EmptyRow } from '../ui';

const STRENGTH_TONE = {
  strong: 'positive',
  moderate: 'accent',
  emerging: 'medium',
  'not observed': 'low',
};

/** One observable career signal, collapsed to its interpretation by default;
 * expands to show the evidence behind it. Deliberately no progress bar and
 * no personality label anywhere here — `strength` is a named verdict
 * (strong/moderate/emerging/not observed), not a percentage meter, and a
 * "not observed" signal is shown with the same weight as the others: an
 * honest absence is still a finding. */
function SignalPanel({ signal, isOpen, onToggle }) {
  return (
    <div className="overflow-hidden rounded-[16px] border border-white/70 bg-white/55">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex w-full items-center justify-between gap-3 p-4 text-left"
      >
        <div className="min-w-0 flex-1">
          <span className="text-[14.5px] font-black text-[#1a1a1a]">{signal.signal}</span>
          <p className="mt-1 text-[13.5px] font-medium leading-relaxed text-[#4a4a48]">{signal.interpretation}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Pill tone={STRENGTH_TONE[signal.strength] || 'default'}>{signal.strength}</Pill>
          <span
            className={`text-[11px] text-[#9a9a97] transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
            aria-hidden="true"
          >
            ▾
          </span>
        </div>
      </button>
      {isOpen && (
        <div className="border-t border-white/60 bg-white/40 p-4">
          <div className="flex items-center justify-between">
            <p className="text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Evidence</p>
            <span className="text-[12px] font-bold text-[#9a9a97]">{signal.confidence}% confidence</span>
          </div>
          {(signal.evidence || []).length > 0 ? (
            <ul className="mt-1.5 flex flex-col gap-1">
              {signal.evidence.map((line) => (
                <li key={line} className="flex items-start gap-1.5 text-[13px] font-semibold text-[#4a4a48]">
                  <span className="mt-0.5 shrink-0 text-[#7b62e8]">•</span>
                  {line}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1.5 text-[13px] font-medium text-[#9a9a97]">No supporting evidence on file.</p>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Replaces "Career DNA". No archetype, no personality read — a fixed set of
 * 6 observable career signals (Technical Leadership, Product Building,
 * Research Exposure, Community Involvement, Learning Consistency, Software
 * Engineering Foundation), each an expandable panel: the interpretation is
 * visible immediately, and opening a signal reveals the evidence and
 * confidence behind it. A signal reported "not observed" is still shown,
 * not hidden — the absence is itself the finding.
 */
export default function CareerSignalsCard({ signals }) {
  const list = signals || [];
  const [openSignal, setOpenSignal] = useState(list[0]?.signal ?? null);

  if (list.length === 0) {
    return <EmptyRow>No career signals detected yet.</EmptyRow>;
  }

  return (
    <div className="flex flex-col gap-3">
      {list.map((signal) => (
        <SignalPanel
          key={signal.signal}
          signal={signal}
          isOpen={openSignal === signal.signal}
          onToggle={() => setOpenSignal((current) => (current === signal.signal ? null : signal.signal))}
        />
      ))}
    </div>
  );
}
