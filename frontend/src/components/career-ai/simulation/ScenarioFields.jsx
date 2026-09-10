import React from 'react';
import { TYPE_FIELDS } from './typeConfig';

const inputCls =
  'w-full rounded-[14px] border border-white/70 bg-white/80 px-4 py-2.5 text-[14.5px] font-bold text-[#1a1a1a] outline-none transition placeholder:text-[#b3b3af] placeholder:transition-colors focus:border-[#7b62e8]/50 focus:placeholder:text-[#6b6b66]';

/**
 * Renders whatever fields a given simulation type collects (see
 * typeConfig.js's `TYPE_FIELDS`, matching the backend's
 * `scenario_input` shape per type). `value` is the scenario_input object
 * so far; `onChange(key, value)` patches one field at a time.
 */
export default function ScenarioFields({ simulationType, value, onChange }) {
  const fields = TYPE_FIELDS[simulationType] || [];

  return (
    <div className="flex flex-col gap-3">
      {fields.map((field) => {
        const raw = value[field.key];
        if (field.type === 'textarea') {
          return (
            <div key={field.key}>
              <label className="mb-1.5 block text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">
                {field.label}
              </label>
              <textarea
                rows={2}
                value={raw || ''}
                placeholder={field.placeholder}
                onChange={(e) => onChange(field.key, e.target.value)}
                className={`${inputCls} resize-none`}
              />
            </div>
          );
        }
        if (field.type === 'select') {
          return (
            <div key={field.key}>
              <label className="mb-1.5 block text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">
                {field.label}
              </label>
              <select
                value={raw || ''}
                onChange={(e) => onChange(field.key, e.target.value)}
                className={inputCls}
              >
                <option value="">Select...</option>
                {field.options.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          );
        }
        if (field.type === 'tags') {
          const text = Array.isArray(raw) ? raw.join(', ') : raw || '';
          return (
            <div key={field.key}>
              <label className="mb-1.5 block text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">
                {field.label}
              </label>
              <input
                type="text"
                value={text}
                placeholder={field.placeholder}
                onChange={(e) =>
                  onChange(
                    field.key,
                    e.target.value
                      .split(',')
                      .map((v) => v.trim())
                      .filter(Boolean)
                  )
                }
                className={inputCls}
              />
            </div>
          );
        }
        return (
          <div key={field.key}>
            <label className="mb-1.5 block text-[12px] font-black uppercase tracking-wide text-[#9a9a97]">
              {field.label}
              {field.required && <span className="ml-1 text-[#7b62e8]">*</span>}
            </label>
            <input
              type={field.type === 'number' ? 'number' : 'text'}
              value={raw ?? ''}
              placeholder={field.placeholder}
              onChange={(e) => onChange(field.key, field.type === 'number' ? Number(e.target.value) || null : e.target.value)}
              className={inputCls}
            />
          </div>
        );
      })}
    </div>
  );
}
