'use client';

import { Button } from '@heroui/react';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { ProfessorCard } from '@/components/ProfessorCard';
import { LoginModal } from '@/components/LoginModal';
import { FilterSortBar, MultiSelectFilter, SearchBox, SortSelect } from '@/components/Filters';
import { findMatches, getUserState, patchUserState } from '@/lib/api';
import { localStore } from '@/lib/local-store';
import type { MatchResponse, MatchScore } from '@/lib/types';

function scoreToPercent(match: MatchScore) {
  const score = match.llm_rerank_score ?? match.total_score;
  return score <= 1 ? score * 100 : score;
}

export default function MatchPage() {
  const [matches, setMatches] = useState<MatchResponse | null>(null);
  const [saved, setSaved] = useState<number[]>([]);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [sort, setSort] = useState('match-desc');
  const [visibleCount, setVisibleCount] = useState(20);
  const [thresholdPercent, setThresholdPercent] = useState(40);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState('');
  const minimumResults = 10;

  useEffect(() => {
    const cachedMatches = localStore.getMatches();
    const cachedSettings = localStore.getMatchSettings();
    setMatches(cachedMatches);
    setThresholdPercent(cachedSettings.threshold_percent);
    setSaved(localStore.getSaved());
    const user = localStore.getUser();
    setIsLoggedIn(!!user);

    getUserState().then(state => {
      setIsLoggedIn(true);
      if (state.last_match_response) {
        localStore.setMatches(state.last_match_response);
        setMatches(state.last_match_response);
        if (state.last_match_response.metadata?.threshold_percent !== undefined) {
          localStore.setMatchSettings({
            threshold_percent: state.last_match_response.metadata.threshold_percent,
            minimum_results: state.last_match_response.metadata.minimum_results,
          });
          setThresholdPercent(state.last_match_response.metadata.threshold_percent);
        }
      }
      if (state.saved_professor_ids) {
        localStore.setSaved(state.saved_professor_ids);
        setSaved(state.saved_professor_ids);
      }
    }).catch(() => undefined);
  }, []);

  const tags = useMemo(() => {
    const all = new Set<string>();
    matches?.matches.forEach(m => m.evidence?.tags?.forEach(t => all.add(t)));
    return Array.from(all).sort((a, b) => a.localeCompare(b));
  }, [matches]);

  const filteredMatches = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = [...(matches?.matches || [])].filter(match => {
      const haystack = [
        match.professor_name,
        match.title,
        match.university,
        match.department,
        match.explanation,
        match.llm_rerank_reason,
        match.research_summary,
        ...(match.evidence?.matched_terms || []),
      ].filter(Boolean).join(' ').toLowerCase();
      const matchesQuery = !q || haystack.includes(q);
      const matchTags = match.evidence?.tags || [];
      const matchesTags = selectedTags.length === 0 || selectedTags.every(tag => matchTags.includes(tag));
      return matchesQuery && matchesTags;
    });
    rows.sort((a, b) => {
      if (sort === 'name-asc') return a.professor_name.localeCompare(b.professor_name);
      if (sort === 'name-desc') return b.professor_name.localeCompare(a.professor_name);
      const aScore = a.llm_rerank_score ?? a.total_score;
      const bScore = b.llm_rerank_score ?? b.total_score;
      return sort === 'match-asc' ? aScore - bScore : bScore - aScore;
    });
    return rows;
  }, [matches, query, selectedTags, sort]);

  const thresholdStatus = useMemo(() => {
    const metadata = matches?.metadata;
    if (!metadata) {
      return {
        mode: 'ranked' as const,
        label: 'Ranked results',
        explanation: `Showing ${matches?.matches.length || 0} ranked professors. Apply a threshold after the backend branch is deployed to see exact threshold counts.`,
      };
    }
    const threshold = Math.round(metadata.threshold_percent);
    const currentSliderDiffers = thresholdPercent !== metadata.threshold_percent;
    if (currentSliderDiffers) {
      return {
        mode: 'pending' as const,
        label: 'Threshold not applied yet',
        explanation: `Currently showing results for ${threshold}%. Click Update results to apply ${thresholdPercent}%.`,
      };
    }
    if (metadata.fallback_top_results_used) {
      return {
        mode: 'fallback' as const,
        label: `Top ${metadata.minimum_results} fallback`,
        explanation: `Only ${metadata.above_threshold_count} professors met your ${threshold}% threshold, so we’re showing your top ${metadata.minimum_results} matches.`,
      };
    }
    return {
      mode: 'threshold' as const,
      label: `Above ${threshold}% threshold`,
      explanation: `Showing ${metadata.returned_count} professors at or above your ${threshold}% threshold.`,
    };
  }, [matches, thresholdPercent]);

  const refreshMatches = async () => {
    const student = matches?.student || localStore.getProfile();
    if (!student) return;
    setRefreshing(true);
    setRefreshError('');
    try {
      const settings = {
        threshold_percent: thresholdPercent,
        minimum_results: minimumResults,
      };
      localStore.setMatchSettings(settings);
      const result = await findMatches(student, settings);
      setMatches(result);
      localStore.setMatches(result);
      patchUserState({ last_match_response: result }).catch(() => undefined);
      setVisibleCount(20);
    } catch (e: any) {
      setRefreshError(e.message || 'Could not refresh matches.');
    } finally {
      setRefreshing(false);
    }
  };

  const toggleSave = (id: number) => {
    if (!isLoggedIn) {
      setShowLoginModal(true);
      return;
    }
    const next = saved.includes(id) ? saved.filter(x => x !== id) : [...saved, id];
    setSaved(next);
    localStore.setSaved(next);
    patchUserState({ saved_professor_ids: next }).catch(() => undefined);
  };

  if (!matches) return (
    <div className="page narrow">
      <div className="card">
        <h2 style={{ marginBottom: 8 }}>No academic profile yet</h2>
        <p className="muted">Update your profile once to generate evidence-backed professor matches. This page will show your ranked match list after that.</p>
        <Link className="button primary" href="/profile" style={{ marginTop: 16 }}>Update profile →</Link>
      </div>
    </div>
  );

  return (
    <div>
      <div className="topbar filter-bar match-filter-bar">
        <div className="row between">
          <div>
            <h2 style={{ margin: 0 }}>Matches</h2>
            <p className="muted">{filteredMatches.length} of {matches.matches.length} matched professors</p>
          </div>
          <Button type="button" onPress={refreshMatches} isDisabled={refreshing}>
            {refreshing ? 'Refreshing…' : 'Update results'}
          </Button>
        </div>
        <div className="card soft match-threshold-card">
          <div className="row between">
            <label className="label" htmlFor="match-threshold" style={{ margin: 0 }}>
              Match threshold: {thresholdPercent}%
            </label>
            <span className={`match-threshold-mode match-threshold-mode-${thresholdStatus.mode}`}>{thresholdStatus.label}</span>
          </div>
          <input
            id="match-threshold"
            className="match-threshold-slider"
            type="range"
            min={10}
            max={90}
            step={5}
            value={thresholdPercent}
            onChange={(event) => {
              const next = Number(event.target.value);
              setThresholdPercent(next);
              localStore.setMatchSettings({ threshold_percent: next, minimum_results: minimumResults });
            }}
          />
          <p className="muted small-text">
            Show professors at or above this score. If fewer than {minimumResults} professors meet it, we’ll still show your top {minimumResults}.
          </p>
        </div>
        <FilterSortBar
          activeFilters={selectedTags.map(value => ({ group: 'tags', value, onRemove: () => setSelectedTags(selectedTags.filter(v => v !== value)) }))}
          onClearAll={() => setSelectedTags([])}
        >
          <SearchBox value={query} onChange={value => { setQuery(value); setVisibleCount(20); }} placeholder="Search all match properties…" />
          <SortSelect value={sort} onChange={setSort} options={[{ value: 'match-desc', label: 'Match high to low' }, { value: 'match-asc', label: 'Match low to high' }, { value: 'name-asc', label: 'Name A–Z' }, { value: 'name-desc', label: 'Name Z–A' }]} />
          <MultiSelectFilter label="Tags" icon="tag" options={tags} values={selectedTags} onChange={values => { setSelectedTags(values); setVisibleCount(20); }} />
        </FilterSortBar>
      </div>

      <div className="notice" style={{ margin: 24 }}>{thresholdStatus.explanation}</div>
      {refreshError && <div className="error" style={{ margin: 24 }}>{refreshError}</div>}
      {matches.notes.length > 0 && <div className="notice" style={{ margin: 24 }}>{matches.notes.join(' ')}</div>}

      <div className="cards list">
        {filteredMatches.slice(0, visibleCount).map(m => {
          const matchData = {
            score: m.llm_rerank_score ?? m.total_score,
            reason: m.llm_rerank_reason || m.explanation,
            paperCount: m.evidence?.publications?.length || 0,
            researchScore: m.research_text_similarity,
            publicationScore: m.recent_publication_similarity,
            recruitingScore: m.recruiting_signal_score,
            metadataScore: Math.max(m.department_title_relevance, m.location_preference_fit, m.fts_score, m.metadata_boost),
            outreachAngle: m.suggested_outreach_angle,
            risks: m.risks_uncertainties || m.evidence?.risks || [],
          };
          return (
            <ProfessorCard
              key={m.professor_id}
              professor={{
                id: m.professor_id,
                name: m.professor_name,
                title: m.title,
                university: m.university,
                department: m.department,
                photo_url: m.photo_url,
                tags: m.evidence.tags,
              }}
              matchData={matchData}
              saved={saved.includes(m.professor_id)}
              onSave={() => toggleSave(m.professor_id)}
              from="/match"
            />
          );
        })}
        {visibleCount < filteredMatches.length && <Button variant="secondary" onPress={() => setVisibleCount(v => v + 20)}>Load more matches</Button>}
      </div>

      <LoginModal isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} message="Log in to save this professor and track your outreach progress." />
    </div>
  );
}
