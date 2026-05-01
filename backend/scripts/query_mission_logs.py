"""Query mission logs from ChromaDB.

This script is intended for quick verification that progress-step events are being
indexed into the `mission_logs` collection and can be semantically searched.

Prereqs:
- `CHROMA_ENABLED=true`
- Chroma connection settings configured in `.env`
- `GEMINI_API_KEY` set (used for embeddings)

Examples:
- python backend/scripts/query_mission_logs.py --run-id <RUN_ID> --query "failed to find a paper" --top-k 10
- python backend/scripts/query_mission_logs.py --run-id <RUN_ID> --query "503 high demand" --include-internal
"""

from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser(description="Semantic search over ARS mission logs")
    parser.add_argument("--run-id", dest="run_id", default=None, help="Filter logs to a specific run_id")
    parser.add_argument("--query", required=True, help="Semantic query")
    parser.add_argument("--top-k", dest="top_k", type=int, default=10, help="Number of results")
    parser.add_argument(
        "--include-internal",
        action="store_true",
        help="Include internal/system logs (retries, stack traces, etc.)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results",
    )
    args = parser.parse_args()

    from app.pipeline.rag import query_mission_logs

    results = query_mission_logs(
        query=args.query,
        run_id=args.run_id,
        top_k=args.top_k,
        include_internal=args.include_internal,
    )

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    if not results:
        print("No results.")
        return 0

    for i, item in enumerate(results, start=1):
        metadata = item.get("metadata") or {}
        distance = item.get("distance")
        text = (item.get("text") or "").strip()

        header = {
            "rank": i,
            "distance": distance,
            "run_id": metadata.get("run_id"),
            "step": metadata.get("step"),
            "status": metadata.get("status"),
            "is_internal": metadata.get("is_internal"),
            "title": metadata.get("title"),
            "timestamp": metadata.get("timestamp"),
        }
        print(json.dumps(header, ensure_ascii=False))
        print(text[:800])
        if len(text) > 800:
            print("…")
        print("-" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
