# Publication Fetch Test Report

Generated: 2026-04-29T20:08:22.634360+00:00
Source database: `db/professor_match_publications.sqlite`
Output database: `db/professor_match_publications.sqlite`
OpenRouter model configured: `tencent/hy3-preview:free`
OpenAlex API key configured: `True`
AI usage: not needed for this publication metadata workflow; OpenRouter is only guarded for future optional AI enrichment.
Professors tested: 3
Papers fetched: 13
Papers with abstracts: 13
SQLite writes enabled: True
Rows inserted: 13
Normalized JSONL: `/home/drl/pi-agent/pi-prof-idea/data/processed/publications/publication_fetch_20260429_150819.jsonl`
Normalized CSV: `/home/drl/pi-agent/pi-prof-idea/data/processed/publications/publication_fetch_20260429_150819.csv`

## Author Resolution

| Professor ID | Professor | OpenAlex Author | Confidence | Institutions | Reasons |
|---:|---|---|---:|---|---|
| 893 | Bruce Tidor | Bruce Tidor `https://openalex.org/A5028186526` | 0.98 | Massachusetts Institute of Technology; Rush University Medical Center; National Institutes of Health; Biotechnology Institute; Université Libre de Bruxelles | name_similarity=1.00; institution_match; works_count=214 |
| 894 | Ernest Fraenkel | Ernest Fraenkel `https://openalex.org/A5043876367` | 0.98 | Massachusetts Institute of Technology; Broad Institute; Ben-Gurion University of the Negev; Vassar College; Cedars-Sinai Medical Center | name_similarity=1.00; institution_match; works_count=295 |
| 895 | Richard Young | Richard A. Young `https://openalex.org/A5112460504` | 0.94 | Whitehead Institute for Biomedical Research; Massachusetts Institute of Technology; University College Dublin; Broad Institute; Boston University | name_similarity=0.93; institution_match; works_count=549 |

## Papers

| Professor | Year | Title | Venue | Abstract? | Source |
|---|---:|---|---|---|---|
| Bruce Tidor | 2024 | Substrate Turnover Dynamics Guide Ketol-Acid Reductoisomerase Redesign for Increased Specific Activity | ACS Catalysis | yes | openalex |
| Bruce Tidor | 2021 | Entropy of Two-Molecule Correlated Translational-Rotational Motions Using the <i>k</i>th Nearest Neighbor Method | Journal of Chemical Theory and Computation | yes | openalex |
| Bruce Tidor | 2019 | Machine Learning Identifies Chemical Characteristics That Promote Enzyme Catalysis | Journal of the American Chemical Society | yes | openalex |
| Ernest Fraenkel | 2026 | Systematic evaluation of single-cell multimodal data integration enhances cell type resolution and discovery of clinical | Genome biology | yes | openalex |
| Ernest Fraenkel | 2026 | Integration of multiomic and multi-phenotypic data identifies biological pathways associated with physical fitness | Communications Biology | yes | openalex |
| Ernest Fraenkel | 2026 | IGF1 peptide targets Rett Syndrome astrocytes to degrade IGF binding protein, rescue synaptogenesis and restore mitochon | bioRxiv (Cold Spring Harbor Laboratory) | yes | openalex |
| Ernest Fraenkel | 2025 | CHAMMI-75: Pre-training multi-channel models with heterogeneous microscopy images | ArXiv.org | yes | openalex |
| Ernest Fraenkel | 2025 | TDP-43 loss induces cryptic polyadenylation in ALS/FTD | Nature Neuroscience | yes | openalex |
| Richard Young | 2025 | High‐throughput CRISPR screen of GWAS risk loci in human microglia reveals novel risk genes for Alzheimer's disease and  | Alzheimer s & Dementia | yes | openalex |
| Richard Young | 2025 | Social Factors and Chronic Disease Burden of Adults with Autism Spectrum Disorder in Multi-system Family Medicine Clinic | Big Data | yes | openalex |
| Richard Young | 2025 | Functional genomic dissection of MS risk loci reveals convergence of cis and trans gene regulatory mechanisms in microgl | medRxiv | yes | openalex |
| Richard Young | 2025 | CRISPR-Cas13d functional transcriptomics reveals widespread isoform-selective cancer dependencies on lncRNAs | Blood | yes | openalex |
| Richard Young | 2024 | Epigenomics and single cell CRISPR screening to investigate the risk‐modifying role of microglia in Alzheimer’s disease  | Alzheimer s & Dementia | yes | openalex |
