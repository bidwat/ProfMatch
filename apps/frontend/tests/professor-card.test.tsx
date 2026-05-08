import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ProfessorCard } from '../components/ProfessorCard'
import type { MatchScore, ProfessorSummary } from '../lib/types'

const professor: ProfessorSummary = {
  id: 1,
  name: 'Ada Lovelace',
  title: 'Assistant Professor',
  university: 'Example University',
  department: 'Computer Science',
  research_summary: 'Works on machine learning for robotics.',
  recruiting_signal: 'unknown',
  source_confidence: 0.8,
  publication_count: 12,
  tags: ['Robotics', 'Machine Learning'],
  photo_url: 'https://example.edu/ada.jpg',
  photo_source_url: 'https://example.edu/ada',
  photo_confidence: 0.75,
}

function matchWithPublications(count: number): MatchScore {
  return {
    professor_id: 1,
    professor_name: 'Ada Lovelace',
    title: 'Assistant Professor',
    university: 'Example University',
    department: 'Computer Science',
    research_summary: 'Works on machine learning for robotics.',
    professor_url: 'https://example.edu/ada',
    photo_url: 'https://example.edu/ada.jpg',
    photo_source_url: 'https://example.edu/ada',
    photo_confidence: 0.75,
    total_score: 0.91,
    research_text_similarity: 0.8,
    recent_publication_similarity: 0.7,
    recruiting_signal_score: 0.35,
    department_title_relevance: 0.9,
    location_preference_fit: 0.5,
    fts_score: 0.8,
    metadata_boost: 0.02,
    explanation: 'Research overlap includes robotics.',
    evidence: {
      matched_terms: ['robotics'],
      tags: ['Robotics'],
      publications: Array.from({ length: count }, (_, i) => ({
        id: i + 1,
        title: `Relevant Robotics Paper ${i + 1}`,
        year: 2024 - i,
        venue: 'Robotics Conf',
        url: `https://example.edu/papers/${i + 1}`,
        source: 'test',
        match_confidence: 0.9,
        similarity_score: 0.8,
        matched_terms: ['robotics', 'learning'],
        abstract: 'This paper studies robotics and learning.',
        abstract_snippet: 'This paper studies robotics and learning.',
      })),
      recruiting_status: 'unknown',
      risks: [],
    },
    risks_uncertainties: [],
    rerank_applied: false,
  }
}

describe('ProfessorCard and MatchCard', () => {
  it('renders a source-backed professor photo when available', () => {
    render(<ProfessorCard professor={professor} />)
    const image = screen.getByAltText('Ada Lovelace profile photo') as HTMLImageElement
    expect(image).toBeInTheDocument()
    expect(image.src).toBe('https://example.edu/ada.jpg')
  })

  it('falls back to initials when no photo is available', () => {
    render(<ProfessorCard professor={{ ...professor, photo_url: null, name: 'Grace Hopper' }} />)
    expect(screen.getByText('GH')).toBeInTheDocument()
    expect(screen.queryByAltText('Grace Hopper profile photo')).not.toBeInTheDocument()
  })

  it('renders relevant publication matched summary', () => {
    const match = matchWithPublications(12);
    render(
      <ProfessorCard 
        professor={{
          id: match.professor_id,
          name: match.professor_name,
          university: match.university,
          department: match.department,
        }}
        matchData={{
          score: match.total_score,
          reason: match.explanation,
          paperCount: match.evidence.publications.length,
          researchScore: match.research_text_similarity,
          publicationScore: match.recent_publication_similarity,
          recruitingScore: match.recruiting_signal_score,
          metadataScore: match.department_title_relevance,
          outreachAngle: 'Ask about robotics lab rotations.',
          risks: ['Recruiting status is unknown'],
        }}
      />
    )
    expect(screen.getByText('12 relevant papers matched')).toBeInTheDocument()
    expect(screen.getByText(/Why matched/)).toBeInTheDocument()
    expect(screen.queryByText('Research')).not.toBeInTheDocument()
    expect(screen.queryByText('Papers')).not.toBeInTheDocument()
    expect(screen.queryByText(/Ask about robotics lab rotations/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Recruiting status is unknown/)).not.toBeInTheDocument()
  })
})
