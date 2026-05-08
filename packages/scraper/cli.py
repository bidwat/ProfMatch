from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

ADAPTERS = {
    "stanford": "packages.scraper.adapters.stanford:StanfordAdapter",
    "cmu": "packages.scraper.adapters.cmu:CMUAdapter",
    "berkeley": "packages.scraper.adapters.berkeley:BerkeleyAdapter",
    "cornell": "packages.scraper.adapters.cornell:CornellAdapter",
    "georgia-tech": "packages.scraper.adapters.georgia_tech:GeorgiaTechAdapter",
    "michigan": "packages.scraper.adapters.michigan:MichiganAdapter",
    "mit": "packages.scraper.adapters.mit:MITAdapter",
    "uiuc": "packages.scraper.adapters.uiuc:UIUCAdapter",
    "ut-austin": "packages.scraper.adapters.ut_austin:UTAustinAdapter",
    "washington": "packages.scraper.adapters.washington:WashingtonAdapter",
}


def load_adapter(adapter_name: str):
    module_name, class_name = ADAPTERS[adapter_name].split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a Professor Match faculty scraper adapter.")
    parser.add_argument("--adapter", choices=sorted(ADAPTERS), required=True)
    parser.add_argument("--fixture", type=Path, help="Offline HTML fixture to parse instead of fetching the live roster.")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--output-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    adapter_cls = load_adapter(args.adapter)
    adapter = adapter_cls()
    outputs = adapter.scrape(run_id=args.run_id, output_root=args.output_root, fixture_path=args.fixture)
    print(
        json.dumps(
            {
                "run_record": outputs.run_record.to_dict(),
                "raw_path": str(outputs.raw_path),
                "processed_paths": {k: str(v) for k, v in outputs.processed_paths.items()},
                "professor_count": len(outputs.professor_records),
                "publication_count": len(outputs.publication_records),
                "duplicate_count": len(outputs.duplicates),
                "validation_issue_count": len(outputs.validation_issues),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
