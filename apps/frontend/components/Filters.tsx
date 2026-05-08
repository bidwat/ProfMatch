'use client';

import type React from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Icon } from '@/components/Icon';

type IconName = Parameters<typeof Icon>[0]['name'];

type ActiveFilter = { group: string; value: string; onRemove?: () => void };

export function Chip({ label, onRemove, tone = 'default' }: { label: string; onRemove?: () => void; tone?: 'default' | 'gold' | 'olive' | 'peach' }) {
  return <span className={`tag chip chip-${tone}`}>{label}{onRemove && <button type="button" aria-label={`Remove ${label}`} onClick={onRemove}><Icon name="x" size={10} /></button>}</span>;
}

export function ChipList({ values, onRemove }: { values: string[]; onRemove?: (value: string) => void }) {
  if (!values.length) return null;
  return <div className="tags chip-list">{values.map(value => <Chip key={value} label={value} onRemove={onRemove ? () => onRemove(value) : undefined} />)}</div>;
}

export function SearchBox({ value, onChange, placeholder = 'Search…' }: { value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="search-box compact-search">
      <Icon name="search" size={13} />
      <input value={value} placeholder={placeholder} onChange={e => onChange(e.target.value)} />
    </label>
  );
}

interface MultiSelectFilterProps {
  label: string;
  options: string[];
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  icon?: IconName;
}

export function MultiSelectFilter({ label, options, values, onChange, placeholder = 'Search options…', icon = 'filter' }: MultiSelectFilterProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [open]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return options.filter(option => !q || option.toLowerCase().includes(q)).slice(0, 120);
  }, [options, query]);

  function toggle(value: string) {
    onChange(values.includes(value) ? values.filter(v => v !== value) : [...values, value]);
  }

  return (
    <div className="multi-filter compact-filter" ref={rootRef}>
      <button type="button" className={`filter-chip-button ${values.length ? 'active' : ''}`} onClick={() => setOpen(v => !v)} aria-expanded={open}>
        <Icon name={icon} size={13} />
        <span>{label}</span>
        {values.length > 0 && <strong>{values.length}</strong>}
        <Icon name="chevronDown" size={11} />
      </button>
      {open && (
        <div className="multi-filter-menu">
          <input className="input" value={query} placeholder={placeholder} onChange={e => setQuery(e.target.value)} autoFocus />
          <div className="multi-filter-options">
            {filtered.map(option => (
              <label className="multi-filter-option" key={option} title={option}>
                <input type="checkbox" checked={values.includes(option)} onChange={() => toggle(option)} />
                <span>{option}</span>
              </label>
            ))}
            {filtered.length === 0 && <p className="muted small-text">No options found.</p>}
          </div>
          {values.length > 0 && <button type="button" className="ghost small" onClick={() => onChange([])}>Clear {label.toLowerCase()}</button>}
        </div>
      )}
    </div>
  );
}

export function SingleSelectFilter({ label, value, onChange, options, icon = 'filter', emptyLabel = 'All', className = '' }: { label: string; value: string; onChange: (value: string) => void; options: Array<{ value: string; label: string }>; icon?: IconName; emptyLabel?: string; className?: string }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = options.find(option => option.value === value);

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [open]);

  function choose(nextValue: string) {
    onChange(nextValue);
    setOpen(false);
  }

  return (
    <div className={`multi-filter compact-filter single-filter ${className}`} ref={rootRef}>
      <button type="button" className={`filter-chip-button ${value ? 'active' : ''}`} onClick={() => setOpen(v => !v)} aria-expanded={open}>
        <Icon name={icon} size={13} />
        <span className="filter-button-label">{label}</span>
        <span className="filter-button-value">{selected?.label || emptyLabel}</span>
        <Icon name="chevronDown" size={11} />
      </button>
      {open && (
        <div className="multi-filter-menu single-filter-menu">
          <button type="button" className={`single-filter-option ${!value ? 'selected' : ''}`} onClick={() => choose('')}>{emptyLabel}</button>
          {options.map(option => (
            <button type="button" className={`single-filter-option ${option.value === value ? 'selected' : ''}`} key={option.value} onClick={() => choose(option.value)}>
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function SortSelect({ value, onChange, options }: { value: string; onChange: (value: string) => void; options: Array<{ value: string; label: string }> }) {
  return <SingleSelectFilter label="Sort by" value={value} onChange={onChange} options={options} icon="sort" emptyLabel="Default" className="sort-filter" />;
}

function formatFilterGroup(group: string) {
  return group.split(/[\s_-]+/).filter(Boolean).map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
}

export function ActiveFilterSummary({ filters, onClearAll }: { filters: ActiveFilter[]; onClearAll?: () => void }) {
  if (!filters.length) return null;
  return (
    <div className="active-filter-row" aria-label="Active filters">
      {filters.map((filter, index) => (
        <span className="active-filter-group" key={`${filter.group}-${filter.value}-${index}`}>
          <span className="active-filter-label">{formatFilterGroup(filter.group)}:</span>
          <Chip label={filter.value} onRemove={filter.onRemove} tone={index % 3 === 0 ? 'gold' : index % 3 === 1 ? 'olive' : 'peach'} />
        </span>
      ))}
      {onClearAll && <button type="button" className="button secondary clear-filter-button" onClick={onClearAll}><Icon name="x" size={10} />Clear all</button>}
    </div>
  );
}

export function ChipInput({ label, values, onChange, placeholder }: { label: string; values: string[]; onChange: (values: string[]) => void; placeholder?: string }) {
  const [draft, setDraft] = useState('');
  function add(value: string) {
    const cleanedValues = value.split(',').map(item => item.trim()).filter(Boolean);
    if (!cleanedValues.length) return;
    const next = [...values];
    cleanedValues.forEach(cleaned => {
      if (!next.some(v => v.toLowerCase() === cleaned.toLowerCase())) next.push(cleaned);
    });
    onChange(next);
    setDraft('');
  }
  return (
    <label className="label chip-input">
      {label}
      <div className="chip-input-box">
        <ChipList values={values} onRemove={value => onChange(values.filter(v => v !== value))} />
        <input
          value={draft}
          placeholder={placeholder}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' || e.key === ',') {
              e.preventDefault();
              add(draft.replace(',', ''));
            }
            if (e.key === 'Backspace' && !draft && values.length) onChange(values.slice(0, -1));
          }}
          onBlur={() => add(draft)}
        />
      </div>
    </label>
  );
}

export function FilterSortBar({ children, activeFilters, onClearAll }: { children: React.ReactNode; activeFilters?: ActiveFilter[]; onClearAll?: () => void }) {
  return (
    <div className="filter-sort-shell">
      <div className="filter-controls">{children}</div>
      <ActiveFilterSummary filters={activeFilters || []} onClearAll={onClearAll} />
    </div>
  );
}
