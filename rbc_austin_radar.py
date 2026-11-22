#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RBC + Austin, TX Senior Finance AI Radar
========================================
Standalone multi-portal job radar and local web dashboard designed for a
20-year financial services veteran targeting AI-related roles connected to
RBC (Royal Bank of Canada, RBC Wealth Management US, RBC Capital Markets,
City National Bank, City National Rochdale, and RBC's strategic AI & SOW
consulting ecosystem) while living in Austin, Texas.

Usage:
  python rbc_austin_radar.py            # Full live scrape + open HTML board
  python rbc_austin_radar.py --quick    # Fast API scrape (~15s, skips JobSpy)
  python rbc_austin_radar.py --serve    # Launch interactive local web app (port 8787)
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import html
import json
import re
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

import requests

try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except Exception:
    JOBSPY_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

AI_REGEX = re.compile(
    r"\b(artificial intelligence|generative ai|gen\s*ai|ai/ml|ai\s*&\s*ml|"
    r"machine learning|large language model|llms|agentic|copilot|ai-driven|"
    r"ai-powered|ai\s+tools|ai\s+solutions|ai\s+strategy|ai\s+governance|"
    r"ai\s+adoption|ai\s+transformation|ai\s+readiness|ai\s+business\s+enablement|"
    r"ai\s+capabilities|ai\s+models|data science|predictive modeling|intelligent automation)\b",
    re.I,
)
EXACT_AI_TOKEN = re.compile(r"\bAI\b")

CANADA_CITIES = [
    "toronto", "mississauga", "montreal", "vancouver", "calgary", "halifax",
    "winnipeg", "ottawa", "edmonton", "waterloo", "guelph", "london, ontario",
    "quebec", "saskatoon", "regina", "moncton", "charlottetown", "brampton",
    "markham", "vaughan", "oakville",
]

US_STATE_MARKERS = [
    "united states", "austin", "texas", "dallas", "houston", "new york",
    "jersey city", "minneapolis", "california", "los angeles", "san francisco",
    "san diego", "chicago", "boston", "florida", "atlanta", "charlotte",
    "wilmington", "newark", "phoenix", "seattle", "denver", "stamford",
    "connecticut", "maryland", "virginia", "ohio", "wisconsin", "nevada",
    "washington, dc", "central region", "cnb", "1251 aoa", "brookfield place",
    "nicollet", "goldman sachs tower",
]

BUCKET_LABELS = {
    "1_direct_rbc_austin_remote_ai": "1. Direct RBC / CNB: Austin, TX or US-Remote + AI",
    "2_rbc_strategic_ai_partners": "2. RBC Strategic AI Partners (Austin / US-Remote, No Bank RTO)",
    "3_banking_ai_consulting_sow": "3. Austin & US-Remote Finance AI Executive & SOW Advisory Leads",
    "4_rbc_us_senior_finance_ai": "4. RBC US Senior Finance + AI (Spoke-Office / Hybrid Pitch)",
    "5_rbc_tx_remote_precedents": "5. RBC / CNB Texas & US-Remote Precedents",
    "6_rbc_ai_enablement_blueprints": "6. RBC 'AI Business Enablement' Executive Blueprints",
}

SCRAPE_STATUS: Dict[str, Any] = {
    "running": False,
    "step": "Idle",
    "last_updated": "",
    "error": "",
}


def sanitize_dashes(text: str) -> str:
    if not text:
        return ""
    cleaned = str(text).replace("\u2014", " - ").replace("\u2013", " - ")
    return re.sub(r"\s+", " ", cleaned).strip()


def sanitize_dashes_multiline(text: str) -> str:
    return str(text).replace("\u2014", " - ").replace("\u2013", " - ")


def strip_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    no_tags = re.sub(r"<[^>]+>", " ", str(raw_html))
    return sanitize_dashes(html.unescape(no_tags))


def extract_ai_signals(title: str, desc: str) -> List[str]:
    signals = set()
    combined = f"{title} {desc}"
    for m in AI_REGEX.findall(combined):
        signals.add(m.lower())
    if EXACT_AI_TOKEN.search(combined):
        signals.add("AI")
    return sorted(signals)


def extract_ai_snippet(desc: str) -> str:
    for m in re.finditer(
        r"[^.]{0,90}\b(?:AI|Artificial Intelligence|Machine Learning|GenAI|Generative AI|Data Science|AI/ML|North)\b[^.]{0,130}",
        desc,
    ):
        return sanitize_dashes(m.group(0))
    return ""


def extract_pay_band(desc: str) -> str:
    matches = re.findall(r"\$[0-9]{2,3},[0-9]{3}(?:\s*-\s*\$[0-9]{2,3},[0-9]{3})?", desc)
    for m in matches:
        if "-" in m:
            return sanitize_dashes(m)
    return sanitize_dashes(matches[0]) if matches else ""


# ---------------------------------------------------------------------------
# Live Scrapers
# ---------------------------------------------------------------------------

def scrape_rbc_workday() -> tuple[List[Dict[str, Any]], int]:
    SCRAPE_STATUS["step"] = "Scraping RBC Global Workday (RBCGLOBAL1)..."
    print("[1/5] Scraping RBC Global Workday (RBCGLOBAL1)...")
    list_url = "https://rbc.wd3.myworkdayjobs.com/wday/cxs/rbc/RBCGLOBAL1/jobs"
    r0 = requests.post(
        list_url,
        headers=HEADERS,
        json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
        timeout=25,
    ).json()
    total = r0.get("total", 0)
    postings = list(r0.get("jobPostings", []))

    for offset in range(20, total, 20):
        try:
            resp = requests.post(
                list_url,
                headers=HEADERS,
                json={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""},
                timeout=25,
            )
            if resp.status_code == 200:
                postings.extend(resp.json().get("jobPostings", []))
            time.sleep(0.15)
        except Exception:
            continue

    to_enrich = []
    for p in postings:
        loc = (p.get("locationsText") or "").lower()
        title = p.get("title") or ""
        is_multi = "locations" in loc
        is_us = any(k in loc for k in US_STATE_MARKERS)
        is_ai_title = bool(re.search(
            r"\b(AI|Artificial Intelligence|Machine Learning|GenAI|Borealis|Agentic|Quant|Data Management)\b",
            title,
            re.I,
        ))
        is_senior_ai_bench = is_ai_title and any(
            s in title.lower() for s in ["director", "vp", "vice president", "principal", "lead", "head", "senior manager"]
        )
        if is_multi or is_us or is_senior_ai_bench or (is_ai_title and not any(c in loc for c in CANADA_CITIES)):
            to_enrich.append(p)

    SCRAPE_STATUS["step"] = f"Enriching {len(to_enrich)} RBC US & AI postings..."
    print(f"      Pulled {len(postings)} RBC postings; enriching {len(to_enrich)} candidates...")

    get_headers = {"Accept": "application/json", "Accept-Encoding": "gzip, deflate", "User-Agent": HEADERS["User-Agent"]}

    def fetch_detail(p: Dict[str, Any]) -> Dict[str, Any] | None:
        ext = p.get("externalPath", "")
        if not ext:
            return None
        try:
            r = requests.get(f"https://rbc.wd3.myworkdayjobs.com/wday/cxs/rbc/RBCGLOBAL1{ext}", headers=get_headers, timeout=15)
            if r.status_code != 200:
                return None
            info = r.json().get("jobPostingInfo", {})
            desc = strip_html(info.get("jobDescription", ""))
            primary_loc = sanitize_dashes(info.get("location", p.get("locationsText", "")))
            add_locs = [sanitize_dashes(x) for x in (info.get("additionalLocations") or [])]
            all_locs = " | ".join([primary_loc] + add_locs)
            country = info.get("country", {})
            country_name = country.get("descriptor", "") if isinstance(country, dict) else str(country)
            return {
                "kind": "direct_rbc",
                "source": "RBC Workday",
                "company": "RBC",
                "req_id": sanitize_dashes(info.get("jobReqId", "")),
                "title": sanitize_dashes(info.get("title", p.get("title", ""))),
                "location": all_locs,
                "country": sanitize_dashes(country_name),
                "remote_type": sanitize_dashes(info.get("remoteType", "")),
                "posted_on": sanitize_dashes(info.get("startDate", p.get("postedOn", ""))),
                "url": f"https://rbc.wd3.myworkdayjobs.com/en-US/RBCGLOBAL1{ext}",
                "description": desc,
                "partner_note": "",
            }
        except Exception:
            return None

    enriched = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for item in ex.map(fetch_detail, to_enrich):
            if item:
                enriched.append(item)
    return enriched, len(postings)


def scrape_cnb() -> tuple[List[Dict[str, Any]], int]:
    SCRAPE_STATUS["step"] = "Scraping City National Bank & Rochdale (RBC)..."
    print("[2/5] Scraping City National Bank & Rochdale (an RBC Company)...")
    cnb_raw = []
    get_headers = {"Accept": "application/json", "Accept-Encoding": "gzip, deflate", "User-Agent": HEADERS["User-Agent"]}
    for page in [1, 2, 3]:
        try:
            r = requests.get(f"https://careers.cnb.com/api/jobs?page={page}&limit=100", headers=get_headers, timeout=20)
            if r.status_code == 200:
                batch = [j.get("data", j) for j in r.json().get("jobs", [])]
                if not batch:
                    break
                cnb_raw.extend(batch)
        except Exception:
            break

    results = []
    for d in cnb_raw:
        title = sanitize_dashes(d.get("title", ""))
        desc = strip_html((d.get("description") or "") + " " + (d.get("qualifications") or ""))
        desc_no_boiler = re.sub(r"Unless otherwise indicated as fully remote[^.]+\.", "", desc, flags=re.I)
        desc_no_boiler = re.sub(r"remote deposit capture|remote colleagues", "", desc_no_boiler, flags=re.I)
        full_loc = sanitize_dashes(d.get("full_location") or f"{d.get('city', '')}, {d.get('state', '')}")
        req_id = sanitize_dashes(str(d.get("req_id", "")))
        is_rem = bool(re.search(r"\b(remote|virtual)\b", f"{title} {full_loc} {desc_no_boiler}", re.I))
        results.append({
            "kind": "direct_rbc",
            "source": "City National Bank (RBC)",
            "company": "City National Bank (an RBC Company)",
            "req_id": f"CNB-{req_id}",
            "title": title,
            "location": full_loc,
            "country": "United States of America",
            "remote_type": "Remote / Virtual" if is_rem else "",
            "posted_on": sanitize_dashes(str(d.get("posted_date", ""))[:10]),
            "url": f"https://careers.cnb.com/jobs/{req_id}",
            "description": desc,
            "partner_note": "",
        })
    print(f"      Pulled {len(results)} City National Bank postings.")
    return results, len(results)


def scrape_ashby_partners() -> List[Dict[str, Any]]:
    SCRAPE_STATUS["step"] = "Scraping RBC Strategic AI Partners (Cohere & Factory)..."
    print("[3/5] Scraping RBC Strategic AI Partners on Ashby (Cohere 'North for Banking' & Factory)...")
    partners = [
        (
            "cohere",
            "Cohere (RBC 'North for Banking' AI Partner)",
            "Co-developed 'North for Banking' generative AI workspace directly with RBC across Wealth Management and Capital Markets.",
        ),
        (
            "factory",
            "Factory (RBC Enterprise AI Partner)",
            "Autonomous enterprise AI platform naming Royal Bank of Canada (RBC) and Blackstone among flagship enterprise customers.",
        ),
    ]
    get_headers = {"Accept": "application/json", "Accept-Encoding": "gzip, deflate", "User-Agent": HEADERS["User-Agent"]}
    found: List[Dict[str, Any]] = []

    for slug, display_name, p_note in partners:
        try:
            r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", headers=get_headers, timeout=20)
            if r.status_code != 200:
                continue
            for j in r.json().get("jobs", []):
                title = sanitize_dashes(j.get("title", ""))
                sec = [s.get("locationName", "") for s in (j.get("secondaryLocations") or [])]
                loc = sanitize_dashes(" | ".join(filter(None, [j.get("location", "")] + sec)))
                is_rem = bool(j.get("isRemote"))
                desc = strip_html(j.get("descriptionHtml") or j.get("descriptionPlain") or "")
                loc_low = loc.lower()
                # Focus on US Remote, Texas, Central Region, or Finance/Enterprise/Corporate Leadership
                is_us_rem_or_tx = (
                    (is_rem and any(u in loc_low for u in ["united states", "austin", "texas", "houston", "dallas", "central region", "new york", "washington, dc", "san francisco"]))
                    or any(t in loc_low for t in ["austin", "texas", "houston", "dallas", "central region"])
                )
                if not is_us_rem_or_tx:
                    continue
                found.append({
                    "kind": "rbc_partner",
                    "source": f"Ashby ({slug})",
                    "company": display_name,
                    "req_id": f"{slug.upper()}-{str(j.get('id', ''))[:6]}",
                    "title": title,
                    "location": loc,
                    "country": "United States of America",
                    "remote_type": "Remote (US / Central)" if is_rem else "Texas / Regional",
                    "posted_on": sanitize_dashes(str(j.get("publishedAt", ""))[:10]),
                    "url": j.get("jobUrl", ""),
                    "description": desc or p_note,
                    "partner_note": p_note,
                })
        except Exception as e:
            print(f"      Ashby {slug} warning: {e}")

    print(f"      Pulled {len(found)} US-Remote / Texas postings at Cohere & Factory.")
    return found


def scrape_jobspy_ecosystem_and_sow() -> List[Dict[str, Any]]:
    if not JOBSPY_AVAILABLE:
        print("[4/5] JobSpy not installed; skipping external Indeed/LinkedIn sweep.")
        return []

    SCRAPE_STATUS["step"] = "Scraping Indeed USA & LinkedIn for RBC Vendors & Banking AI SOWs..."
    print("[4/5] Scraping Indeed USA & LinkedIn for RBC Ecosystem Vendors & Austin/Remote Banking AI Consulting SOWs...")

    queries = [
        # RBC-named portfolio & infrastructure vendors (Conquest Planning, Solace, etc.)
        {
            "kind": "rbc_partner",
            "site_name": ["indeed"],
            "search_term": '("Royal Bank of Canada" OR "RBC Capital Markets" OR "RBC Wealth Management") ("AI" OR "Artificial Intelligence" OR "Wealth")',
            "location": "United States",
            "is_remote": True,
            "results_wanted": 20,
        },
        # Banking / Wealth Management AI Transformation & Governance Consulting SOW roles in Austin, TX
        {
            "kind": "sow_consulting",
            "site_name": ["indeed", "linkedin"],
            "search_term": '("Director" OR "Principal" OR "VP" OR "Lead") ("Financial Services" OR "Banking" OR "Wealth Management" OR "Capital Markets") ("AI" OR "Generative AI" OR "AI Governance" OR "Model Risk")',
            "location": "Austin, TX",
            "is_remote": False,
            "results_wanted": 25,
        },
        # US-Remote Banking / Wealth Management AI Strategy & SOW Consulting roles
        {
            "kind": "sow_consulting",
            "site_name": ["indeed"],
            "search_term": '("Director" OR "Principal" OR "VP" OR "Practice Lead") ("Banking" OR "Wealth Management" OR "Capital Markets") ("AI Strategy" OR "Generative AI" OR "AI Governance" OR "AI Transformation")',
            "location": "United States",
            "is_remote": True,
            "results_wanted": 25,
        },
    ]

    found: List[Dict[str, Any]] = []
    seen_urls = set()

    for q in queries:
        try:
            df = scrape_jobs(
                site_name=q["site_name"],
                search_term=q["search_term"],
                location=q["location"],
                distance=50,
                is_remote=q["is_remote"],
                results_wanted=q["results_wanted"],
                country_indeed="usa",
                linkedin_fetch_description=True,
                verbose=0,
            )
            if df is None or df.empty:
                continue
            for _, row in df.iterrows():
                url = str(row.get("job_url") or "")
                if not url or url in seen_urls:
                    continue
                comp = sanitize_dashes(str(row.get("company") or ""))
                title = sanitize_dashes(str(row.get("title") or ""))
                desc = strip_html(str(row.get("description") or ""))
                loc = sanitize_dashes(str(row.get("location") or ""))
                blob = f"{comp} {title} {desc}"

                if q["kind"] == "rbc_partner":
                    if not re.search(
                        r"\b(Royal Bank of Canada|RBC Wealth Management|RBC Capital Markets|City National Bank|Conquest)\b",
                        blob,
                        re.I,
                    ):
                        continue
                    p_note = f"{comp} explicitly references RBC / RBC Capital Markets as a strategic investor or enterprise customer."
                else:
                    # Must genuinely be finance/banking/wealth + AI
                    if not re.search(r"\b(bank|banking|wealth management|capital markets|financial services|asset management)\b", blob, re.I):
                        continue
                    p_note = (
                        "Austin / US-Remote Financial Services AI leadership or advisory role. Advisory and SOW directors "
                        "regularly serve Tier-1 banks (including RBC USWM, Capital Markets, and City National) without bank RTO locks."
                    )

                seen_urls.add(url)
                found.append({
                    "kind": q["kind"],
                    "source": f"JobSpy ({row.get('site', 'board')})",
                    "company": comp or "Enterprise Advisory",
                    "req_id": f"EXT-{len(found)+1:03d}",
                    "title": title,
                    "location": loc,
                    "country": "United States of America",
                    "remote_type": "Remote" if (bool(row.get("is_remote")) or "remote" in loc.lower()) else "Austin / Hybrid",
                    "posted_on": sanitize_dashes(str(row.get("date_posted") or "")),
                    "url": url,
                    "description": desc,
                    "partner_note": p_note,
                })
        except Exception as e:
            print(f"      JobSpy warning: {e}")

    print(f"      Pulled {len(found)} external RBC vendor & Banking AI consulting postings.")
    return found


# ---------------------------------------------------------------------------
# Classification & Scoring
# ---------------------------------------------------------------------------

def classify_and_score(all_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    print("[5/5] Scoring and classifying opportunities for 20-Yr Finance + Austin, TX...")
    curated: List[Dict[str, Any]] = []
    seen_keys = set()

    for item in all_items:
        base_comp = re.sub(r"\s*\(.*?\)", "", item["company"]).strip().lower()
        norm_title = re.sub(r"\s+", " ", item["title"].strip().lower())
        dedup_key = (base_comp, norm_title)
        if dedup_key in seen_keys:
            continue

        title = item["title"]
        desc = item["description"]
        loc = item["location"]
        loc_low = loc.lower()
        title_low = title.lower()
        country_low = item["country"].lower()
        kind = item.get("kind", "direct_rbc")

        is_us = (
            "united states" in country_low
            or "united states" in loc_low
            or any(m in loc_low for m in US_STATE_MARKERS)
        )
        is_austin = "austin" in loc_low or "central region" in loc_low
        is_texas = is_austin or any(t in loc_low for t in ["texas", "dallas", "houston", ", tx"])
        is_remote = bool(item["remote_type"]) or "remote" in loc_low or "virtual" in loc_low

        ai_signals = extract_ai_signals(title, desc)
        has_ai = len(ai_signals) > 0 or kind == "rbc_partner"
        ai_in_title = bool(re.search(r"\b(AI|Artificial Intelligence|Machine Learning|GenAI|Quant|Data|Analytics)\b", title, re.I))

        is_senior_finance = any(
            k in title_low
            for k in [
                "director", "vice president", "vp", "svp", "managing director", "head",
                "principal", "lead", "senior manager", "strategist", "consultant",
                "manager", "account executive", "partner", "corporate development", "advisor",
            ]
        )
        is_junior_or_unrelated_ic = any(
            k in title_low
            for k in [
                "summer associate", "intern", "co-op", "front desk", "administrative assistant",
                "teller", "part time", "client services professional i", "trainee",
                "chaos engineer", "web director", "content editor", "content strategist",
                "communications manager", "compensation", "corporate accounting", "sourcing lead",
                "talent partner", "design engineer", "security operations", "public sector",
                "us federal", "department of war", "intelligence community", "aerospace", "sled",
                "fed civilian", "cyber operate", "concierge", "telecom, media", "investor relations",
            ]
        )
        if is_junior_or_unrelated_ic:
            continue

        bucket = None
        score = 50
        austin_strategy = ""

        # Bucket 1: Direct RBC / CNB W-2 in Austin / TX / US-Remote + AI
        if kind == "direct_rbc" and is_us and (is_austin or is_texas or is_remote) and len(ai_signals) > 0:
            bucket = "1_direct_rbc_austin_remote_ai"
            score = 97 if is_austin else (93 if is_texas else 90)
            austin_strategy = "Direct RBC/CNB geographic + AI match. Confirm Texas home-office or Austin spoke-office seating in recruiter screen."

        # Bucket 2: RBC Strategic AI Partners (Cohere, Conquest Planning, Factory, Solace) in Austin / US-Remote
        elif kind == "rbc_partner" and is_us and (is_austin or is_texas or is_remote):
            if is_senior_finance or any(k in title_low for k in ["professional services", "solutions", "strategic", "commercial", "finance"]):
                bucket = "2_rbc_strategic_ai_partners"
                score = 91 if ("corporate development" in title_low or "conquest" in item["company"].lower() or is_austin) else 85
                austin_strategy = item.get("partner_note") or (
                    "RBC Strategic AI Partner hiring Remote in Austin/US with zero 4-day bank RTO lock."
                )

        # Bucket 3: Austin & US-Remote Finance AI Executive / SOW Consulting Leads
        elif kind == "sow_consulting" and has_ai and is_senior_finance and (
            ai_in_title or any(k in title_low for k in ["ai", "analytics", "data", "model", "transformation", "strategy", "innovation", "digital", "automation", "credit"])
        ):
            bucket = "3_banking_ai_consulting_sow"
            score = 86 if "austin" in loc_low else 82
            austin_strategy = item.get("partner_note") or (
                "Austin / US-Remote Financial Services AI executive or SOW consulting lead."
            )

        # Bucket 4: Direct RBC US Senior Finance + AI (Spoke-Office / Hybrid Negotiation)
        elif kind == "direct_rbc" and is_us and len(ai_signals) > 0 and is_senior_finance:
            bucket = "4_rbc_us_senior_finance_ai"
            score = 84 if "minneapolis" in loc_low else 78
            if "minneapolis" in loc_low:
                austin_strategy = (
                    "US Wealth Management role (Minneapolis HQ). Pitch badge-in spoke-office seating at "
                    "RBC Wealth Management Austin (5301 Southwest Pkwy, Suite 300) or Dallas + monthly MN travel."
                )
            else:
                austin_strategy = (
                    "Capital Markets / Institutional hub role (NY/JC/Charlotte). Standard FTEs face 4-day RTO; "
                    "approach via executive travel exception or approved US consulting SOW."
                )

        # Bucket 5: RBC / CNB Texas & US-Remote Precedents
        elif kind == "direct_rbc" and is_us and (is_texas or is_remote):
            if is_texas or any(k in title_low for k in ["consultant", "relationship", "strategist", "python", "data", "manager", "vp"]):
                bucket = "5_rbc_tx_remote_precedents"
                score = 75 if (is_texas and is_remote) else (72 if is_texas else 66)
                if is_texas and is_remote:
                    austin_strategy = "Confirmed Remote-in-Texas field classification (home office in Austin works natively)."
                elif is_texas:
                    austin_strategy = "Confirmed Texas corporate hub role (Dallas/Houston); establishes Texas payroll corridor."
                else:
                    austin_strategy = "Confirmed US Remote / Virtual precedent inside RBC / City National Bank."

        # Bucket 6: RBC Global 'AI Business Enablement' Executive Blueprints (Canada HQ)
        elif kind == "direct_rbc" and not is_us and ai_in_title and any(
            k in title_low for k in ["ai business enablement", "ai readiness", "ai product management", "ai governance", "ai/ml"]
        ) and any(s in title_low for s in ["director", "senior director", "senior technical product manager"]):
            bucket = "6_rbc_ai_enablement_blueprints"
            score = 76
            austin_strategy = (
                "Canadian HQ executive blueprint: exact role title & charter RBC uses for 20-year finance leaders driving AI adoption. "
                "Use this mandate language when pitching US Wealth Management (Minneapolis/Austin) leadership."
            )

        if not bucket:
            continue

        seen_keys.add(dedup_key)
        curated.append({
            "bucket": bucket,
            "score": score,
            "source": item["source"],
            "company": item["company"],
            "req_id": item["req_id"],
            "title": title,
            "location": loc,
            "remote_type": item["remote_type"] or ("Texas Hub" if is_texas else "Hybrid (4-Day Office)"),
            "pay_band": extract_pay_band(desc),
            "posted_on": item["posted_on"],
            "ai_signals": ", ".join(ai_signals) if ai_signals else ("Enterprise AI" if kind == "rbc_partner" else ""),
            "ai_snippet": extract_ai_snippet(desc),
            "austin_strategy": sanitize_dashes(austin_strategy),
            "url": item["url"],
            "description": desc[:3500],
        })

    curated.sort(key=lambda x: (x["bucket"], -x["score"], x["title"]))
    return curated


# ---------------------------------------------------------------------------
# HTML Dashboard Builder
# ---------------------------------------------------------------------------

def build_html_board(items: List[Dict[str, Any]], stats: Dict[str, Any], interactive_server: bool = False) -> str:
    now_str = stats.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M")
    counts = {k: sum(1 for x in items if x["bucket"] == k) for k in BUCKET_LABELS}

    server_controls = ""
    if interactive_server:
        server_controls = """
        <div class="server-actions">
          <button class="srv-btn" onclick="triggerScrape(true)" id="btnQuick">Refresh Fast APIs (~15s)</button>
          <button class="srv-btn srv-btn-gold" onclick="triggerScrape(false)" id="btnFull">Run Full Scrape (+ Indeed/LinkedIn)</button>
          <a class="srv-btn" href="/export.csv">Download CSV</a>
          <span id="scrapeStatus" class="status-pill">Ready</span>
        </div>
        """

    cards_html = []
    for job in items:
        b_key = job["bucket"]
        b_label = BUCKET_LABELS.get(b_key, b_key)
        job_key = html.escape(f"{job['company']}::{job['req_id']}::{job['title']}")
        pay_badge = f'<span class="badge badge-pay">{html.escape(job["pay_band"])}</span>' if job["pay_band"] else ""
        ai_badge = f'<span class="badge badge-ai">AI: {html.escape(job["ai_signals"])}</span>' if job["ai_signals"] else ""
        rem_badge = f'<span class="badge badge-loc">{html.escape(job["remote_type"])}</span>'
        ai_quote = (
            f'<div class="ai-quote"><strong>AI Context:</strong> "...{html.escape(job["ai_snippet"])}..."</div>'
            if job["ai_snippet"] else ""
        )
        search_blob = html.escape(
            f"{job['title']} {job['company']} {job['location']} {job['ai_signals']} {job['austin_strategy']} {job['req_id']}".lower()
        )

        cards_html.append(f"""
        <article class="job-card" data-bucket="{b_key}" data-key="{job_key}" data-search="{search_blob}">
          <div class="card-top">
            <div>
              <div class="bucket-tag">{html.escape(b_label)}</div>
              <h3 class="job-title">{html.escape(job['title'])}</h3>
              <div class="job-sub">
                <strong>{html.escape(job['company'])}</strong> &middot;
                <span>{html.escape(job['req_id'])}</span> &middot;
                <span>{html.escape(job['source'])}</span>
                {(' &middot; <span>' + html.escape(job['posted_on']) + '</span>') if job['posted_on'] else ''}
              </div>
              <div class="job-loc">{html.escape(job['location'])}</div>
            </div>
            <div class="card-right">
              <div class="right-row">
                <button class="star-btn" onclick="toggleStar('{job_key}', this)" title="Save to shortlist">&#9734;</button>
                <span class="score-pill">Fit {job['score']}</span>
              </div>
              <a class="apply-btn" href="{html.escape(job['url'])}" target="_blank" rel="noopener">Open Posting</a>
            </div>
          </div>
          <div class="badges">
            {rem_badge}
            {pay_badge}
            {ai_badge}
          </div>
          {ai_quote}
          <div class="strategy-box">
            <strong>Austin, TX Playbook Angle:</strong> {html.escape(job['austin_strategy'])}
          </div>
          <details class="desc-toggle">
            <summary>Read Full Posting Excerpt</summary>
            <p>{html.escape(job['description'])}</p>
          </details>
        </article>
        """)

    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RBC + Austin, TX Senior Finance AI Radar</title>
  <style>
    :root {{
      --rbc-blue: #0051a5;
      --rbc-navy: #002855;
      --rbc-gold: #ffd200;
      --bg: #f4f6fa;
      --card: #ffffff;
      --border: #dde3ee;
      --text: #182232;
      --muted: #56657a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    header {{
      background: linear-gradient(135deg, var(--rbc-navy), var(--rbc-blue));
      color: #fff;
      padding: 26px 24px;
      border-bottom: 4px solid var(--rbc-gold);
    }}
    .wrap {{ max-width: 1200px; margin: 0 auto; }}
    .hdr-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }}
    header h1 {{ margin: 0 0 6px 0; font-size: 25px; letter-spacing: -0.3px; }}
    header p {{ margin: 0; color: #dbe7ff; font-size: 14px; }}
    .server-actions {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
    .srv-btn {{
      background: rgba(255,255,255,0.14);
      color: #fff;
      border: 1px solid rgba(255,255,255,0.3);
      padding: 8px 12px;
      border-radius: 7px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      text-decoration: none;
    }}
    .srv-btn:hover {{ background: rgba(255,255,255,0.24); }}
    .srv-btn-gold {{ background: var(--rbc-gold); color: var(--rbc-navy); border-color: var(--rbc-gold); }}
    .srv-btn-gold:hover {{ background: #ffe047; }}
    .status-pill {{ font-size: 12px; color: #e2ecff; padding: 4px 8px; }}
    .kpi-strip {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .kpi {{
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 10px;
      padding: 12px 14px;
    }}
    .kpi .num {{ font-size: 22px; font-weight: 700; color: var(--rbc-gold); }}
    .kpi .lbl {{ font-size: 12px; color: #e4eeff; }}
    .playbook-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(270px, 1fr));
      gap: 14px;
      margin: 20px auto;
    }}
    .play-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-top: 4px solid var(--rbc-blue);
      border-radius: 10px;
      padding: 15px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .play-card h3 {{ margin: 0 0 6px 0; font-size: 14px; color: var(--rbc-navy); }}
    .play-card p {{ margin: 0; font-size: 13px; color: var(--muted); }}
    .controls {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .controls input[type="search"] {{
      flex: 1 1 260px;
      padding: 9px 12px;
      border: 1px solid #c6d0e1;
      border-radius: 7px;
      font-size: 14px;
    }}
    .filter-btn {{
      border: 1px solid #c6d0e1;
      background: #f8faff;
      color: var(--rbc-navy);
      padding: 7px 11px;
      border-radius: 7px;
      cursor: pointer;
      font-size: 12.5px;
      font-weight: 600;
    }}
    .filter-btn.active {{
      background: var(--rbc-blue);
      color: #fff;
      border-color: var(--rbc-blue);
    }}
    .job-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 18px;
      margin-bottom: 14px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }}
    .card-top {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }}
    .bucket-tag {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--rbc-blue);
      letter-spacing: 0.4px;
      margin-bottom: 4px;
    }}
    .job-title {{ margin: 0 0 4px 0; font-size: 18px; color: var(--rbc-navy); }}
    .job-sub {{ font-size: 13px; color: var(--muted); margin-bottom: 4px; }}
    .job-loc {{ font-size: 13px; font-weight: 600; color: #2b3a52; }}
    .card-right {{ display: flex; flex-direction: column; align-items: flex-end; gap: 8px; min-width: 140px; }}
    .right-row {{ display: flex; align-items: center; gap: 6px; }}
    .star-btn {{
      background: transparent;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      font-size: 16px;
      line-height: 1;
      padding: 4px 7px;
      cursor: pointer;
      color: #64748b;
    }}
    .star-btn.starred {{ background: #fef9c3; border-color: #eab308; color: #ca8a04; }}
    .score-pill {{
      background: #eef4ff;
      color: var(--rbc-blue);
      border: 1px solid #c7dbff;
      font-weight: 700;
      font-size: 13px;
      padding: 4px 10px;
      border-radius: 999px;
    }}
    .apply-btn {{
      background: var(--rbc-blue);
      color: #fff;
      text-decoration: none;
      padding: 7px 13px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
    }}
    .apply-btn:hover {{ background: var(--rbc-navy); }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .badge {{ font-size: 12px; padding: 3px 9px; border-radius: 5px; font-weight: 600; }}
    .badge-loc {{ background: #eef2f7; color: #334155; }}
    .badge-pay {{ background: #ecfdf3; color: #047857; border: 1px solid #a7f3d0; }}
    .badge-ai {{ background: #f5f3ff; color: #5b21b6; border: 1px solid #ddd6fe; }}
    .ai-quote {{
      margin-top: 10px;
      padding: 9px 12px;
      background: #faf8ff;
      border-left: 3px solid #7c3aed;
      font-size: 13px;
      color: #3b2a67;
      border-radius: 0 6px 6px 0;
    }}
    .strategy-box {{
      margin-top: 10px;
      padding: 9px 12px;
      background: #fffbeb;
      border-left: 3px solid #f59e0b;
      font-size: 13px;
      color: #78350f;
      border-radius: 0 6px 6px 0;
    }}
    details.desc-toggle {{ margin-top: 10px; font-size: 13px; color: #334155; }}
    details.desc-toggle summary {{ cursor: pointer; font-weight: 600; color: var(--rbc-blue); }}
    details.desc-toggle p {{
      margin: 8px 0 0 0;
      padding: 10px;
      background: #f8fafc;
      border-radius: 6px;
      border: 1px solid #e2e8f0;
    }}
    main {{ padding: 0 24px 48px 24px; }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <div class="hdr-top">
        <div>
          <h1>RBC + Austin, Texas: 20-Year Finance Veteran AI Radar</h1>
          <p>Last scraped: {html.escape(now_str)} &middot; Sources: RBC Workday, City National Bank, Cohere, Factory, Indeed USA, LinkedIn</p>
        </div>
        {server_controls}
      </div>
      <div class="kpi-strip">
        <div class="kpi">
          <div class="num">{stats.get('rbc_total', 0)}</div>
          <div class="lbl">RBC Workday Scanned</div>
        </div>
        <div class="kpi">
          <div class="num">{stats.get('cnb_total', 0)}</div>
          <div class="lbl">City National Bank Scanned</div>
        </div>
        <div class="kpi">
          <div class="num">{counts['2_rbc_strategic_ai_partners']}</div>
          <div class="lbl">RBC AI Partners (Austin/Remote)</div>
        </div>
        <div class="kpi">
          <div class="num">{counts['3_banking_ai_consulting_sow']}</div>
          <div class="lbl">Austin/Remote Banking AI SOWs</div>
        </div>
        <div class="kpi">
          <div class="num">{counts['4_rbc_us_senior_finance_ai']}</div>
          <div class="lbl">RBC US Senior Finance + AI</div>
        </div>
      </div>
    </div>
  </header>

  <main>
    <div class="wrap">
      <section class="playbook-grid">
        <div class="play-card">
          <h3>Lane 1: RBC Strategic AI Partners (100% Austin / Remote)</h3>
          <p>Work directly on RBC's AI stack without RBC's 4-day office mandate: Cohere (co-builder of RBC's North for Banking), Conquest Planning (RBC-backed AI wealth engine), Factory (Austin/Central), and Solace.</p>
        </div>
        <div class="play-card">
          <h3>Lane 2: Banking AI Consulting &amp; SOW Directors (Austin)</h3>
          <p>Enter through Tier-1 Financial Services AI &amp; Model Risk advisory practices in Austin or US-Remote that staff transformation SOWs inside RBC US Wealth Management, Capital Markets, and City National.</p>
        </div>
        <div class="play-card">
          <h3>Lane 3: Austin Spoke-Office Pitch (5301 Southwest Pkwy)</h3>
          <p>Target US Wealth Management leadership roles in Minneapolis and negotiate badge-in spoke-office seating at RBC Wealth Management's Austin office (5301 Southwest Pkwy, Suite 300) or Dallas hub.</p>
        </div>
        <div class="play-card">
          <h3>Lane 4: Remote-in-Texas Field Code (City National / Rochdale)</h3>
          <p>City National Rochdale and RBC USWM use Remote-in-Texas territory codes for regional consultants (see CNB-13012). Pitch Advisor AI Enablement on that exact Texas field payroll code.</p>
        </div>
      </section>

      <section class="controls">
        <input id="q" type="search" placeholder="Search title, company (Cohere, RBC, Conquest), Austin, Dallas, salary..." oninput="applyFilter()">
        <button class="filter-btn active" data-b="all" onclick="setBucket('all', this)">All ({len(items)})</button>
        <button class="filter-btn" data-b="starred" onclick="setBucket('starred', this)">Starred Shortlist</button>
        <button class="filter-btn" data-b="1_direct_rbc_austin_remote_ai" onclick="setBucket('1_direct_rbc_austin_remote_ai', this)">Direct RBC Austin+AI ({counts['1_direct_rbc_austin_remote_ai']})</button>
        <button class="filter-btn" data-b="2_rbc_strategic_ai_partners" onclick="setBucket('2_rbc_strategic_ai_partners', this)">RBC AI Partners ({counts['2_rbc_strategic_ai_partners']})</button>
        <button class="filter-btn" data-b="3_banking_ai_consulting_sow" onclick="setBucket('3_banking_ai_consulting_sow', this)">Banking AI SOWs ({counts['3_banking_ai_consulting_sow']})</button>
        <button class="filter-btn" data-b="4_rbc_us_senior_finance_ai" onclick="setBucket('4_rbc_us_senior_finance_ai', this)">RBC US Senior AI ({counts['4_rbc_us_senior_finance_ai']})</button>
        <button class="filter-btn" data-b="5_rbc_tx_remote_precedents" onclick="setBucket('5_rbc_tx_remote_precedents', this)">TX / Remote Precedents ({counts['5_rbc_tx_remote_precedents']})</button>
        <button class="filter-btn" data-b="6_rbc_ai_enablement_blueprints" onclick="setBucket('6_rbc_ai_enablement_blueprints', this)">RBC AI Blueprints ({counts['6_rbc_ai_enablement_blueprints']})</button>
      </section>

      <section id="cards">
        {''.join(cards_html)}
      </section>
    </div>
  </main>

  <script>
    let activeBucket = 'all';
    const STORAGE_KEY = 'rbc_austin_ai_starred_v1';

    function getStarred() {{
      try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }}
      catch (e) {{ return []; }}
    }}

    function initStars() {{
      const starred = new Set(getStarred());
      document.querySelectorAll('.job-card').forEach(card => {{
        const key = card.dataset.key;
        const btn = card.querySelector('.star-btn');
        if (starred.has(key) && btn) {{
          btn.classList.add('starred');
          btn.innerHTML = '&#9733;';
        }}
      }});
    }}

    function toggleStar(key, btn) {{
      const set = new Set(getStarred());
      if (set.has(key)) {{
        set.delete(key);
        btn.classList.remove('starred');
        btn.innerHTML = '&#9734;';
      }} else {{
        set.add(key);
        btn.classList.add('starred');
        btn.innerHTML = '&#9733;';
      }}
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...set]));
      applyFilter();
    }}

    function setBucket(b, btn) {{
      activeBucket = b;
      document.querySelectorAll('.filter-btn').forEach(el => el.classList.remove('active'));
      btn.classList.add('active');
      applyFilter();
    }}

    function applyFilter() {{
      const q = document.getElementById('q').value.toLowerCase().trim();
      const starred = new Set(getStarred());
      document.querySelectorAll('.job-card').forEach(card => {{
        let bMatch = true;
        if (activeBucket === 'starred') bMatch = starred.has(card.dataset.key);
        else if (activeBucket !== 'all') bMatch = (card.dataset.bucket === activeBucket);
        const qMatch = !q || card.dataset.search.includes(q);
        card.style.display = (bMatch && qMatch) ? 'block' : 'none';
      }});
    }}

    async function triggerScrape(quick) {{
      const st = document.getElementById('scrapeStatus');
      if (!st) return;
      st.textContent = 'Starting live scrape...';
      await fetch('/api/scrape?quick=' + (quick ? '1' : '0'), {{ method: 'POST' }});
      const timer = setInterval(async () => {{
        const r = await fetch('/api/status');
        const d = await r.json();
        st.textContent = d.running ? d.step : 'Reloading...';
        if (!d.running) {{
          clearInterval(timer);
          location.reload();
        }}
      }}, 1500);
    }}

    initStars();
  </script>
</body>
</html>
"""
    return sanitize_dashes_multiline(page)


# ---------------------------------------------------------------------------
# Pipeline Runner & Local Server
# ---------------------------------------------------------------------------

def run_pipeline(quick: bool = False) -> Path:
    SCRAPE_STATUS["running"] = True
    SCRAPE_STATUS["error"] = ""
    try:
        rbc_items, rbc_total = scrape_rbc_workday()
        cnb_items, cnb_total = scrape_cnb()
        ashby_items = scrape_ashby_partners()
        ext_items = [] if quick else scrape_jobspy_ecosystem_and_sow()

        curated = classify_and_score(rbc_items + cnb_items + ashby_items + ext_items)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        stats = {
            "timestamp": now_str,
            "rbc_total": rbc_total,
            "cnb_total": cnb_total,
            "ashby_total": len(ashby_items),
            "ext_total": len(ext_items),
        }

        (OUT_DIR / "rbc_austin_ai_jobs.json").write_text(
            json.dumps({"stats": stats, "jobs": curated}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        fieldnames = [
            "bucket", "score", "source", "company", "req_id", "title",
            "location", "remote_type", "pay_band", "posted_on", "ai_signals",
            "ai_snippet", "austin_strategy", "url", "description",
        ]
        with (OUT_DIR / "rbc_austin_ai_jobs.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(curated)

        html_path = OUT_DIR / "rbc_austin_ai_board.html"
        html_path.write_text(build_html_board(curated, stats, interactive_server=False), encoding="utf-8")

        SCRAPE_STATUS["last_updated"] = now_str
        SCRAPE_STATUS["step"] = "Complete"
        print("\n=== RADAR SUMMARY ===")
        for k, lbl in BUCKET_LABELS.items():
            print(f"  {sum(1 for x in curated if x['bucket'] == k):3d} | {lbl}")
        print(f"\nSaved board: {html_path}")
        return html_path
    except Exception as e:
        SCRAPE_STATUS["error"] = str(e)
        SCRAPE_STATUS["step"] = f"Error: {e}"
        raise
    finally:
        SCRAPE_STATUS["running"] = False


class RadarHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            body = json.dumps(SCRAPE_STATUS).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/export.csv":
            csv_file = OUT_DIR / "rbc_austin_ai_jobs.csv"
            data = csv_file.read_bytes() if csv_file.exists() else b""
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="rbc_austin_ai_jobs.csv"')
            self.end_headers()
            self.wfile.write(data)
            return

        json_file = OUT_DIR / "rbc_austin_ai_jobs.json"
        if json_file.exists():
            payload = json.loads(json_file.read_text(encoding="utf-8"))
            jobs = payload.get("jobs", payload if isinstance(payload, list) else [])
            stats = payload.get("stats", {}) if isinstance(payload, dict) else {}
        else:
            jobs, stats = [], {"timestamp": "Never (click Refresh above)"}

        body = build_html_board(jobs, stats, interactive_server=True).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/scrape":
            qs = parse_qs(parsed.query)
            quick = qs.get("quick", ["0"])[0] == "1"
            if not SCRAPE_STATUS["running"]:
                threading.Thread(target=run_pipeline, kwargs={"quick": quick}, daemon=True).start()
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"started":true}')
            return
        self.send_response(404)
        self.end_headers()


def serve_app(port: int = 8787) -> None:
    if not (OUT_DIR / "rbc_austin_ai_jobs.json").exists():
        print("No cached snapshot found; running initial fast API scrape...")
        run_pipeline(quick=True)
    url = f"http://127.0.0.1:{port}"
    server = ThreadingHTTPServer(("127.0.0.1", port), RadarHandler)
    print(f"\nRadar live at {url} (Press Ctrl+C to stop)")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down radar server.")
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="RBC + Austin, TX Senior Finance AI Radar")
    parser.add_argument("--quick", action="store_true", help="Fast API scrape (~15s, skips JobSpy Indeed/LinkedIn)")
    parser.add_argument("--serve", action="store_true", help="Run interactive local web server on http://127.0.0.1:8787")
    parser.add_argument("--port", type=int, default=8787, help="Port for --serve mode (default: 8787)")
    parser.add_argument("--no-open", action="store_true", help="Do not automatically open browser after CLI scrape")
    args = parser.parse_args()

    if args.serve:
        serve_app(port=args.port)
    else:
        html_path = run_pipeline(quick=args.quick)
        if not args.no_open:
            webbrowser.open(html_path.as_uri())


if __name__ == "__main__":
    main()
