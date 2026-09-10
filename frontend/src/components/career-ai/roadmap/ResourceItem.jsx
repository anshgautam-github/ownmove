import React from 'react';
import { Pill } from '../ui';

const TYPE_LABELS = {
  course: 'Course',
  book: 'Book',
  documentation: 'Docs',
  paper: 'Paper',
  tutorial: 'Tutorial',
  video: 'Video',
  repository: 'Repo',
  practice: 'Practice',
};

/**
 * One recommended resource for an objective. Deliberately never renders a
 * link — the backend's `RoadmapResource` schema has no `url` field at all
 * (see backend/app/career_roadmap/schemas/roadmap.py's docstring): a
 * specific URL stated with confidence today can still be wrong, moved, or
 * dead by the time the user clicks it, and this system has no way to keep
 * a generated link accurate after the fact. A resource is identified by
 * title + provider + type only, precisely enough that the user can search
 * for the current version themselves.
 */
export default function ResourceItem({ resource }) {
  return (
    <div className="flex items-start justify-between gap-2.5 rounded-[10px] border border-white/60 bg-white/70 px-2.5 py-2">
      <div className="min-w-0 text-[12.5px] leading-snug">
        <span className="font-black text-[#1a1a1a]">{resource.title}</span>
        {resource.provider && <span className="font-semibold text-[#9a9a97]"> · {resource.provider}</span>}
        {resource.reason && <p className="mt-0.5 font-medium text-[#7a7a76]">{resource.reason}</p>}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <Pill tone="default" className="normal-case">
          {TYPE_LABELS[resource.type] || resource.type}
        </Pill>
        {resource.free === false && (
          <span className="text-[10px] font-black uppercase tracking-wide text-[#b48a3a]">Paid</span>
        )}
      </div>
    </div>
  );
}
