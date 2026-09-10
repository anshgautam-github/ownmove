import React from 'react';

/** One entry from either `new_claims_supported` (claim + basis) or
 * `claims_still_unsupported` (claim + reason) — same visual treatment,
 * different tone via `supported`. */
export default function ClaimItem({ claim, supported }) {
  const detail = supported ? claim.basis : claim.reason;
  return (
    <li
      className={`rounded-[14px] border p-3 ${
        supported ? 'border-emerald-100 bg-emerald-50/50' : 'border-orange-100 bg-orange-50/50'
      }`}
    >
      <p className={`text-[13.5px] font-black ${supported ? 'text-emerald-800' : 'text-orange-800'}`}>
        {supported ? '✓ ' : '✗ '}
        {claim.claim}
      </p>
      <p className="mt-1 text-[12.5px] font-medium leading-relaxed text-[#7a7a76]">{detail}</p>
    </li>
  );
}
