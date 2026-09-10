import React from 'react';

function Bar({ width = '100%', height = 'h-2.5' }) {
  return <div className={`${height} animate-pulse rounded-full bg-[#111827]/8`} style={{ width }} />;
}

function SkeletonSection({ lines = 3 }) {
  return (
    <div className="flex flex-col gap-3 border-b border-[#111827]/8 py-7 first:pt-0 last:border-b-0">
      <Bar width="140px" height="h-3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Bar key={i} width={`${88 - i * 12}%`} />
      ))}
    </div>
  );
}

/** Mirrors the real report's single-column shape (masthead, then stacked
 * sections) so the layout doesn't jump when data arrives. */
export default function AnalysisSkeleton() {
  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="flex items-center gap-6 border-b border-[#111827]/8 pb-7">
        <div className="h-28 w-28 shrink-0 animate-pulse rounded-full bg-[#111827]/8" />
        <div className="flex-1 space-y-2.5">
          <Bar width="50%" height="h-3" />
          <Bar width="30%" height="h-2" />
          <Bar width="65%" height="h-2" />
        </div>
      </div>
      {Array.from({ length: 9 }).map((_, i) => (
        <SkeletonSection key={i} lines={3} />
      ))}
    </div>
  );
}
