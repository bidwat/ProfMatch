# Publication Fetch Test Report

Generated: 2026-04-29T19:26:18.928591+00:00
Database: `/home/drl/pi-agent/pi-prof-idea/db/professor_match_clean.sqlite`
Professors tested: 3
Papers fetched: 15
Papers with abstracts: 15
SQLite writes enabled: False
Rows inserted: 0
Normalized JSONL: `/home/drl/pi-agent/pi-prof-idea/data/processed/publications/publication_fetch_20260429_142609.jsonl`
Normalized CSV: `/home/drl/pi-agent/pi-prof-idea/data/processed/publications/publication_fetch_20260429_142609.csv`

## Author Resolution

| Professor ID | Professor | OpenAlex Author | Confidence | Institutions | Reasons |
|---:|---|---|---:|---|---|
| 1 | Sara Achour | Sara Achour `https://openalex.org/A5060778165` | 0.98 | Stanford University; Moscow Institute of Thermal Technology; Massachusetts Institute of Technology | name_similarity=1.00; institution_match; works_count=40 |
| 13 | Dan Boneh | Dan Boneh `https://openalex.org/A5027798962` | 0.98 | Stanford University; Association for Computing Machinery; Palo Alto University; Bell (Canada); Princeton University | name_similarity=1.00; institution_match; works_count=505 |
| 28 | Chelsea Finn | Chelsea Finn `https://openalex.org/A5005431772` | 0.98 | Google (United States); Intel (United States); Berkeley College; Harvard University; Google DeepMind (United Kingdom) | name_similarity=1.00; institution_match; works_count=409 |

## Papers

| Professor | Year | Title | Venue | Abstract? | Source |
|---|---:|---|---|---|---|
| Sara Achour | 2025 | HyperCam: Low-Power Onboard Computer Vision for IoT Cameras | Unknown venue | yes | openalex |
| Sara Achour | 2025 | NavHD: Low-Power Learning for Micro-Robotic Controls in the Wild | Unknown venue | yes | openalex |
| Sara Achour | 2025 | A Probabilistic Perspective on Tiling Sparse Tensor Algebra | Unknown venue | yes | openalex+semantic_scholar |
| Sara Achour | 2025 | Oscillator Formulations of Many NP Problems | ArXiv.org | yes | openalex |
| Sara Achour | 2025 | Optimizing Ancilla-Based Quantum Circuits with SPARE | Proceedings of the ACM on Programming Languages | yes | openalex |
| Dan Boneh | 2026 | Securing Elliptic Curve Cryptocurrencies against Quantum Vulnerabilities: Resource Estimates and Mitigations | arXiv (Cornell University) | yes | openalex |
| Dan Boneh | 2026 | Hawkeye: Reproducing GPU-Level Non-Determinism | ArXiv.org | yes | openalex |
| Dan Boneh | 2025 | ZeroOS: A Universal Modular Library OS for zkVMs | ArXiv.org | yes | openalex |
| Dan Boneh | 2025 | Comparing AI Agents to Cybersecurity Professionals in Real-World Penetration Testing | ArXiv.org | yes | openalex |
| Dan Boneh | 2025 | BountyBench: Dollar Impact of AI Agent Attackers and Defenders on Real-World Cybersecurity Systems | ArXiv.org | yes | openalex |
| Chelsea Finn | 2026 | RoboReward: General-Purpose Vision-Language Reward Models for Robotics | ArXiv.org | yes | openalex |
| Chelsea Finn | 2025 | Emergence of Human to Robot Transfer in Vision-Language-Action Models | arXiv (Cornell University) | yes | openalex |
| Chelsea Finn | 2025 | PolaRiS: Scalable Real-to-Sim Evaluations for Generalist Robot Policies | arXiv (Cornell University) | yes | openalex |
| Chelsea Finn | 2025 | Invariance Co-training for Robot Visual Generalization | ArXiv.org | yes | openalex |
| Chelsea Finn | 2025 | $π^{*}_{0.6}$: a VLA That Learns From Experience | ArXiv.org | yes | openalex |
