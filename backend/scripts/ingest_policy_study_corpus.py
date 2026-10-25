#!/usr/bin/env python3
"""
Ingest Policy Study passages + chunk tags into PEP (Postgres + Pinecone).

Uses already-extracted passages as vector chunks (no re-chunking). Joins
chunk_tags.jsonl metadata (serves / doc_level_serves) onto each passage.

Usage (from backend/, with production env):
  railway run --service backend python scripts/ingest_policy_study_corpus.py \\
    --passages /path/to/extracted_passages.jsonl \\
    --tags /path/to/chunk_tags.jsonl

  Add --force to delete existing Policy Study docs/vectors and re-ingest.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select

# Ensure backend app is importable when run as scripts/...
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import AsyncSessionLocal
from app.core.vector_db import vector_db
from app.models.document import Document, DocumentType, ProcessingStatus
from app.models.project import Project
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("ingest_policy_study")

PROJECT_NAME = "Policy Study"
FIELD_OF_STUDY = (
    "Pakistan social protection / humanitarian response "
    "(BISP, NSER, emergency cash assistance)"
)
CORE_OBJECTIVE = (
    "Generate grounded personas for a policy study on social protection and "
    "emergency cash assistance in Pakistan, using tagged corpus passages."
)
BATCH_SIZE = 50


def _load_jsonl(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"Invalid JSONL at {path}:{line_no}: {e}") from e
    return rows


def _meta_str(value: Any, max_len: int = 500) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return s[:max_len]


def _meta_str_list(values: Any) -> List[str]:
    if not values:
        return []
    out: List[str] = []
    for v in values:
        s = _meta_str(v, 120)
        if s:
            out.append(s)
    return out


def _passage_embed_text(p: dict) -> str:
    quote = (p.get("quote") or "").strip()
    why = (p.get("why_relevant") or "").strip()
    persona = p.get("persona") or ""
    attribute = p.get("attribute") or ""
    locator = p.get("locator") or ""
    org = p.get("organisation") or ""
    year = p.get("year") or ""
    bibkey = p.get("bibkey") or ""
    measure = p.get("measure_element")
    parts = [
        f"Source: {bibkey} ({org}, {year}) {locator}".strip(),
        f"Persona: {persona} | Attribute: {attribute}"
        + (f" | Measure: {measure}" if measure else ""),
        f'Quote: "{quote}"' if quote else "",
    ]
    if why:
        parts.append(f"Relevance: {why}")
    return "\n".join(x for x in parts if x)


def _doc_content(passages: List[dict]) -> str:
    blocks = []
    for i, p in enumerate(passages, start=1):
        blocks.append(f"### Passage {i}\n{_passage_embed_text(p)}")
    return "\n\n".join(blocks)


async def _get_or_create_project(session, force_reset_docs: bool) -> Project:
    result = await session.execute(select(Project).where(Project.name == PROJECT_NAME))
    project = result.scalar_one_or_none()
    if project:
        logger.info("Found existing project id=%s name=%r", project.id, project.name)
        return project

    admin = (
        await session.execute(select(User).where(User.is_admin.is_(True)).limit(1))
    ).scalar_one_or_none()
    project = Project(
        name=PROJECT_NAME,
        field_of_study=FIELD_OF_STUDY,
        core_objective=CORE_OBJECTIVE,
        includes_context=True,
        includes_interviews=False,
        user_id=admin.id if admin else None,
    )
    session.add(project)
    await session.flush()
    logger.info("Created project id=%s", project.id)
    return project


async def _clear_project_docs(session, project_id: int) -> None:
    result = await session.execute(select(Document).where(Document.project_id == project_id))
    docs = list(result.scalars().all())
    if not docs:
        return
    logger.info("Deleting %d existing documents for project %s", len(docs), project_id)
    for doc in docs:
        try:
            await vector_db.delete_documents(filter_metadata={"document_id": str(doc.id)})
        except Exception as e:
            logger.warning("Vector delete failed for document %s: %s", doc.id, e)
        await session.delete(doc)
    await session.flush()


async def ingest(
    passages_path: Path,
    tags_path: Path,
    force: bool,
    dry_run: bool,
) -> None:
    passages = _load_jsonl(passages_path)
    tags_rows = _load_jsonl(tags_path)
    tags_by_chunk = {t["chunk_id"]: t for t in tags_rows if t.get("chunk_id")}

    by_bibkey: Dict[str, List[dict]] = defaultdict(list)
    for p in passages:
        bib = p.get("bibkey") or "unknown"
        by_bibkey[bib].append(p)

    logger.info(
        "Loaded %d passages across %d sources; %d chunk tags",
        len(passages),
        len(by_bibkey),
        len(tags_by_chunk),
    )
    if dry_run:
        for bib, ps in sorted(by_bibkey.items(), key=lambda x: -len(x[1])):
            logger.info("  %s: %d passages", bib, len(ps))
        return

    async with AsyncSessionLocal() as session:
        project = await _get_or_create_project(session, force)
        await session.commit()

        existing = (
            await session.execute(
                select(Document).where(
                    Document.project_id == project.id,
                    Document.filename.like("policy_study_%"),
                )
            )
        ).scalars().all()
        if existing and not force:
            raise SystemExit(
                f"Project {project.id} already has {len(existing)} policy_study docs. "
                "Re-run with --force to replace."
            )
        if existing and force:
            await _clear_project_docs(session, project.id)
            await session.commit()

        total_vectors = 0
        for bibkey, bib_passages in sorted(by_bibkey.items()):
            filename = f"policy_study_{bibkey}.md"
            content = _doc_content(bib_passages)
            doc = Document(
                filename=filename,
                document_type=DocumentType.CONTEXT,
                content=content,
                processed_content=None,
                project_id=project.id,
                processing_status=ProcessingStatus.COMPLETED,
                processing_error=None,
            )
            session.add(doc)
            await session.flush()

            texts: List[str] = []
            metadatas: List[dict] = []
            ids: List[str] = []
            for idx, p in enumerate(bib_passages):
                chunk_id = p.get("chunk_id") or f"{bibkey}#passage-{idx}"
                tag = tags_by_chunk.get(chunk_id, {})
                serves = _meta_str_list(tag.get("serves"))
                if not serves and p.get("persona"):
                    serves = [_meta_str(p.get("persona"))]
                doc_level = _meta_str_list(tag.get("doc_level_serves"))
                text = _passage_embed_text(p)
                texts.append(text)
                meta = {
                    "document_type": DocumentType.CONTEXT.value,
                    "filename": filename,
                    "document_id": str(doc.id),
                    "project_id": str(project.id),
                    "chunk_index": idx,
                    "chunk_id": _meta_str(chunk_id, 200),
                    "bibkey": _meta_str(bibkey, 120),
                    "organisation": _meta_str(p.get("organisation"), 200),
                    "year": _meta_str(p.get("year"), 16),
                    "locator": _meta_str(p.get("locator"), 64),
                    "persona": _meta_str(p.get("persona"), 120),
                    "attribute": _meta_str(p.get("attribute"), 120),
                    "measure_element": _meta_str(p.get("measure_element"), 120),
                    "corpus": "policy_study",
                    "source_kind": "extracted_passage",
                }
                if serves:
                    meta["serves"] = serves
                if doc_level:
                    meta["doc_level_serves"] = doc_level
                metadatas.append(meta)
                # Stable-ish vector ids for re-runs with --force after delete
                safe = chunk_id.replace("#", "_").replace("/", "_")
                ids.append(f"ps-{doc.id}-{idx}-{safe}"[:64])

            logger.info(
                "Upserting %d passage vectors for %s (document_id=%s)",
                len(texts),
                bibkey,
                doc.id,
            )
            vector_ids: List[str] = []
            for i in range(0, len(texts), BATCH_SIZE):
                batch_texts = texts[i : i + BATCH_SIZE]
                batch_meta = metadatas[i : i + BATCH_SIZE]
                batch_ids = ids[i : i + BATCH_SIZE]
                vids = await vector_db.add_documents(
                    documents=batch_texts,
                    metadatas=batch_meta,
                    ids=batch_ids,
                )
                vector_ids.extend(vids)
                logger.info("  batch %d–%d done", i, i + len(batch_texts) - 1)

            doc.vector_id = vector_ids[0] if vector_ids else None
            total_vectors += len(vector_ids)
            await session.commit()
            logger.info("Document %s stored with %d vectors", doc.id, len(vector_ids))

        logger.info(
            "Done. project_id=%s documents=%d vectors=%d",
            project.id,
            len(by_bibkey),
            total_vectors,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passages", type=Path, required=True)
    parser.add_argument("--tags", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.passages.is_file():
        raise SystemExit(f"Passages file not found: {args.passages}")
    if not args.tags.is_file():
        raise SystemExit(f"Tags file not found: {args.tags}")
    asyncio.run(ingest(args.passages, args.tags, args.force, args.dry_run))


if __name__ == "__main__":
    main()
