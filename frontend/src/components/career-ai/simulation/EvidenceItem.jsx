import React from 'react';

/** One entry from `evidence_created` — tangible proof the action would
 * produce IF completed as described, never a vague improvement claim. */
export default function EvidenceItem({ item }) {
  return (
    <li className="rounded-[14px] border border-white/70 bg-white/55 p-3">
      <p className="text-[13.5px] font-black text-[#1a1a1a]">{item.evidence}</p>
      <p className="mt-1 text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">{item.significance}</p>
    </li>
  );
}
