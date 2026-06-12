#!/usr/bin/env python3

import json
import os
from pathlib import Path
from sqlmodel import Session, create_engine
from apps.backend.app.models.professor import Professor, Publication, RecruitingSignal
from apps.backend.app.db import engine
from apps.backend.app.main import create_db_and_tables

def load_professors_from_jsonl(file_path: Path):
    professors = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                # Convert to model
                prof = Professor(
                    name=data['name'],
                    normalized_name=data.get('normalized_name', data['name'].lower()),
                    title=data.get('title'),
                    university=data['university'],
                    department=data['department'],
                    email=data.get('email'),
                    faculty_profile_url=data.get('faculty_profile_url'),
                    homepage_url=data.get('homepage_url'),
                    google_scholar_url=data.get('google_scholar_url'),
                    openalex_id=data.get('openalex_id'),
                    dblp_url=data.get('dblp_url'),
                    semantic_scholar_id=data.get('semantic_scholar_id'),
                    research_text=data.get('research_text'),
                    research_summary=data.get('research_summary'),
                    recruiting_signal=RecruitingSignal(data.get('recruiting_signal', 'unknown')),
                    recruiting_evidence_url=data.get('recruiting_evidence_url'),
                    recruiting_evidence_text=data.get('recruiting_evidence_text'),
                    source_confidence=data.get('source_confidence', 0.0),
                    extra=data.get('extra') or {},
                )
                professors.append(prof)
    return professors

def load_publications_from_jsonl(file_path: Path):
    publications = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                # Find professor by some id, but since no prof id yet, perhaps later
                # For now, assume publications are linked by prof id after insert
                pass
    return publications

def main():
    processed_dir = Path('data/processed')
    if not processed_dir.exists():
        print("Processed data directory not found")
        return

    create_db_and_tables()

    with Session(engine) as session:
        # Collect all professors
        all_professors = []
        for uni_dir in processed_dir.iterdir():
            if uni_dir.is_dir():
                for dept_dir in uni_dir.iterdir():
                    if dept_dir.is_dir():
                        for source_dir in dept_dir.iterdir():
                            if source_dir.is_dir():
                                # Find the latest scrape run
                                runs = [d for d in source_dir.iterdir() if d.is_dir()]
                                if runs:
                                    latest_run = max(runs, key=lambda x: x.name)
                                    prof_file = latest_run / 'professors.jsonl'
                                    if prof_file.exists():
                                        print(f"Loading professors from {prof_file}")
                                        profs = load_professors_from_jsonl(prof_file)
                                        all_professors.extend(profs)

        # Insert professors
        for prof in all_professors:
            session.add(prof)
        session.commit()
        print(f"Loaded {len(all_professors)} professors")

        # TODO: Load publications if needed, but for now skip

if __name__ == '__main__':
    main()