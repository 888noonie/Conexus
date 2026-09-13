from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import timedelta
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.models import Assessment, Evidence, Opportunity, ResearchJob, SourceMonitor
from core.services import audit

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
MAX_RSS_BYTES = 1_048_576
MAX_RSS_ITEMS = 20
MAX_EXCERPT = 2000


def fetch_hackernews(query: str) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    resp = requests.get(
        HN_SEARCH_URL,
        params={"query": query, "hitsPerPage": 20},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    results = []
    for hit in data.get("hits", [])[:20]:
        external_id = hit.get("objectID", "")
        title = hit.get("title") or hit.get("story_title") or "Untitled"
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={external_id}"
        body = hit.get("comment_text") or title
        results.append(
            {
                "external_id": external_id,
                "title": title[:200],
                "url": url,
                "body": body[:MAX_EXCERPT],
                "source": "Hacker News",
                "observed_at": hit.get("created_at_i"),
            }
        )
    return results


def fetch_rss(feed_url: str) -> list[dict[str, Any]]:
    resp = requests.get(
        feed_url,
        timeout=30,
        allow_redirects=False,
        stream=True,
    )
    resp.raise_for_status()
    content = b""
    for chunk in resp.iter_content(chunk_size=8192):
        content += chunk
        if len(content) > MAX_RSS_BYTES:
            raise ValueError("RSS response too large")
    parser = ET.XMLParser()
    root = ET.fromstring(content, parser=parser)
    items = []
    for item in root.iter("item"):
        if len(items) >= MAX_RSS_ITEMS:
            break
        title = _xml_text(item, "title") or "Untitled"
        link = _xml_text(item, "link") or ""
        desc = _xml_text(item, "description") or title
        pub = _xml_text(item, "pubDate") or ""
        external_id = link or title
        items.append(
            {
                "external_id": external_id,
                "title": title[:200],
                "url": link,
                "body": desc[:MAX_EXCERPT],
                "source": feed_url,
                "observed_at": pub,
            }
        )
    return items


def _xml_text(parent, tag: str) -> str:
    el = parent.find(tag)
    if el is not None and el.text:
        return el.text.strip()
    return ""


def import_collection_results(workspace, monitor: SourceMonitor, records: list[dict]) -> int:
    created = 0
    adapter = monitor.adapter
    for rec in records:
        external_id = rec.get("external_id", "")
        url = rec.get("url", "")
        body = rec.get("body", "")
        fingerprint = Evidence.compute_fingerprint(
            url=url, body=body, adapter=adapter, external_id=external_id
        )
        if Evidence.objects.filter(workspace=workspace, fingerprint=fingerprint).exists():
            continue
        observed_at = timezone.now()
        raw_time = rec.get("observed_at")
        if isinstance(raw_time, str) and raw_time:
            parsed = parse_datetime(raw_time)
            if parsed:
                observed_at = parsed
        Evidence.objects.create(
            workspace=workspace,
            title=rec.get("title", "Collected signal")[:200],
            body=body,
            url=url,
            source=rec.get("source", adapter),
            kind=Evidence.KIND_OBSERVED,
            stance=Evidence.STANCE_CONTEXT,
            fingerprint=fingerprint,
            observed_at=observed_at,
        )
        created += 1
    return created


def run_collection(monitor: SourceMonitor) -> dict:
    if monitor.adapter == SourceMonitor.ADAPTER_HN:
        records = fetch_hackernews(monitor.query)
    elif monitor.adapter == SourceMonitor.ADAPTER_RSS:
        records = fetch_rss(monitor.feed_url)
    else:
        raise ValueError(f"Unknown adapter: {monitor.adapter}")
    count = import_collection_results(monitor.workspace, monitor, records)
    return {"imported": count, "fetched": len(records)}


def _extract_citation_ids(text: str) -> list[str]:
    return re.findall(
        r"\[([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]", text, re.I
    )


def run_ai_review(opportunity: Opportunity, mock_response: str | None = None) -> Assessment:
    evidence = list(opportunity.evidence.all()[:20])
    evidence_ids = {str(e.id) for e in evidence}
    if mock_response is not None:
        content = mock_response
    else:
        content = _call_llm(opportunity, evidence)
    cited = _extract_citation_ids(content)
    invalid = [c for c in cited if c not in evidence_ids]
    if invalid:
        raise ValueError(f"Invalid citation IDs: {invalid}")
    report = {
        "draft": content,
        "cited_evidence": cited,
        "label": "AI draft — not validated evidence",
        "generated_at": timezone.now().isoformat(),
    }
    assessment = Assessment.objects.create(
        opportunity=opportunity,
        method=Assessment.METHOD_AI,
        report=report,
        input_snapshot={
            "evidence_ids": list(evidence_ids),
            "opportunity_id": str(opportunity.id),
        },
    )
    audit(opportunity.workspace, "assessment.ai_created", assessment.id)
    return assessment


def _call_llm(opportunity: Opportunity, evidence: list[Evidence]) -> str:
    excerpts = []
    for e in evidence:
        excerpts.append(f"[{e.id}] {e.title}: {e.body[:MAX_EXCERPT]}")
    prompt = (
        f"Review this business opportunity. Cite evidence using [uuid] format only.\n"
        f"Title: {opportunity.title}\n"
        f"Problem: {opportunity.problem}\n"
        f"Buyer: {opportunity.buyer}\n"
        f"Evidence:\n" + "\n".join(excerpts)
    )
    resp = requests.post(
        f"{settings.LLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
        json={
            "model": settings.LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def process_job(job: ResearchJob) -> None:
    if job.kind == ResearchJob.KIND_COLLECTION and job.monitor:
        result = run_collection(job.monitor)
        job.result = result
        monitor = job.monitor
        monitor.next_run_at = timezone.now() + timedelta(hours=monitor.interval_hours)
        monitor.save()
    elif job.kind == ResearchJob.KIND_REVIEW and job.opportunity:
        assessment = run_ai_review(job.opportunity)
        job.result = {"assessment_id": str(assessment.id)}
    else:
        raise ValueError("Invalid job configuration")
