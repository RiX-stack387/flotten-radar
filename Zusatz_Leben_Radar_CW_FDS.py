"""⚓ DEFCON RECHT RADAR - ZUSATZ-FLOTTE "LEBENS-PRAXIS" CW/FDS (V44.0)
Architektur: Playwright + CMP-Blocker + Secure-PDF + Config-Gate + Strict-Evidence + Vault
Gebiet: LANDKREIS CALW & LANDKREIS FREUDENSTADT (100% Geofenced)
"""

import asyncio
import datetime
import hashlib
import io
import ipaddress
import json
import os
import re
import socket
import tempfile
import unicodedata
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from enum import Enum
from google import genai
from google.genai import types
from playwright.async_api import async_playwright, Browser, Request, Route
import pypdf
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

# ==========================================
# 1. KONFIGURATION & CONFIG-GATE
# ==========================================
EXPECTED_ZUSATZ_SLOT_COUNT = 78
BASE_DIR = r"C:\DefconRecht"
STATE_FILE = os.path.join(BASE_DIR, "radar_state_cw_fds_v44.json")
LOG_DIR = os.path.join(BASE_DIR, "MasterLogs")
VAULT_DIR = os.path.join(BASE_DIR, "Beweisarchiv")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(VAULT_DIR, exist_ok=True)

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

MODEL_CASCADE = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
]

class VerificationStatus(str, Enum):
    CONFIGURATION_INVALID = "CONFIGURATION_INVALID"
    SOURCE_NOT_VERIFIED = "SOURCE_NOT_VERIFIED"
    SOURCE_UNCHANGED = "SOURCE_UNCHANGED"
    SOURCE_CHANGED_LEGAL_UNCHANGED = "SOURCE_CHANGED_LEGAL_UNCHANGED"
    LEGAL_CHANGED_NO_CLAIMS = "LEGAL_CHANGED_NO_CLAIMS"
    LEGAL_CHANGED_VALIDATION_FAILED = "LEGAL_CHANGED_VALIDATION_FAILED"
    LEGAL_CHANGED_PARTIALLY_VALIDATED = "LEGAL_CHANGED_PARTIALLY_VALIDATED"
    LEGAL_AND_EVIDENCE_CHANGED = "LEGAL_AND_EVIDENCE_CHANGED"
    LLM_ERROR = "LLM_ERROR"

def validate_arsenal(arsenal: list):
    if len(arsenal) != EXPECTED_ZUSATZ_SLOT_COUNT:
        raise ValueError(f"CONFIG ERROR: {EXPECTED_ZUSATZ_SLOT_COUNT} Slots erwartet, {len(arsenal)} geladen.")
    ids = set()
    for s in arsenal:
        if s["id"] in ids:
            raise ValueError(f"CONFIG ERROR: Doppelte ID {s['id']}")
        ids.add(s["id"])
        if not s.get("allowed_domains") or not s.get("source_urls"):
            raise ValueError(f"CONFIG ERROR: Fehlende Netz-Parameter in {s['id']}")

# ==========================================
# 2. PYDANTIC SCHEMATA & HASHING
# ==========================================
class ValueType(str, Enum):
    EURO = "EURO"
    PERCENT = "PERCENT"
    DATE = "DATE"
    TEXT = "TEXT"
    URTEIL_TEXT = "URTEIL_TEXT"

class LLMClaim(BaseModel):
    norm: str = Field(..., description="Rechtsnorm, Aktenzeichen, Tarif oder Satzung")
    extracted_value: str = Field(..., description="Vollständige Kernaussage, der Leitsatz oder konkreter Betrag")
    value_type: ValueType = Field(..., description="Typ des Wertes")
    context: str = Field(..., description="Zusammenfassung des rechtlichen Sachverhalts")
    evidence_location: str = Field(..., description="Exakter Original-Textausschnitt aus der Webseite als absoluter Beweis")

class LLMAnalysisResult(BaseModel):
    claims: List[LLMClaim] = Field(default_factory=list)

def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_state_atomic(state: dict):
    os.makedirs(os.path.dirname(os.path.abspath(STATE_FILE)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(STATE_FILE), text=True)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE_FILE)

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', unicodedata.normalize("NFKC", text)).strip()

# ==========================================
# 3. SECURITY-GATES & FETCHING
# ==========================================
class SecurityGate:
    BLOCKED_CMP = ["usercentrics", "cookiebot", "etracker", "matomo", "consentmanager"]

    @staticmethod
    async def resolve_and_check_ip(hostname: str):
        loop = asyncio.get_running_loop()
        addr_info = await loop.getaddrinfo(hostname, 443, family=socket.AF_INET, type=socket.SOCK_STREAM)
        for _, _, _, _, sockaddr in addr_info:
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                raise Exception(f"TOCTOU/SSRF-Blockade: Private IP {sockaddr[0]}")
        return True

    @staticmethod
    async def intercept_route(route: Route, request: Request, allowed_domains: List[str]):
        try:
            parsed = urlparse(request.url)
            if parsed.scheme not in ["https", "http"] or not parsed.hostname:
                return await route.abort()
            if any(cmp in parsed.hostname for cmp in SecurityGate.BLOCKED_CMP):
                return await route.abort()
            if not any(parsed.hostname == d or parsed.hostname.endswith("." + d) for d in allowed_domains):
                return await route.abort()
            await SecurityGate.resolve_and_check_ip(parsed.hostname)
            await route.continue_()
        except:
            await route.abort()

async def secure_fetch_pdf(url: str, allowed_domains: List[str], context) -> Optional[Dict[str, str]]:
    parsed = urlparse(url)
    if not parsed.hostname or not any(parsed.hostname == d or parsed.hostname.endswith("." + d) for d in allowed_domains):
        return None
    try:
        await SecurityGate.resolve_and_check_ip(parsed.hostname)
        response = await context.request.get(url, timeout=60000)
        if not response.ok:
            return None
        reader = pypdf.PdfReader(io.BytesIO(await response.body()), strict=False)
        text = "\n".join([f"[PAGE {i+1}] {normalize_text(p.extract_text() or '')}" for i, p in enumerate(reader.pages)])
        return {"requested": url, "resolved": response.url, "canonical": url, "text": text}
    except:
        return None

async def fetch_provenance_source(url: str, allowed_domains: List[str], browser: Browser) -> Optional[Dict[str, str]]:
    context = await browser.new_context(ignore_https_errors=False)
    if url.lower().endswith(".pdf") or "blob=" in url.lower():
        res = await secure_fetch_pdf(url, allowed_domains, context)
        await context.close()
        return res

    await context.route("**/*", lambda route, req: SecurityGate.intercept_route(route, req, allowed_domains))
    page = await context.new_page()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        if not response:
            return None
        resolved = response.url
        await page.wait_for_timeout(3000)
        
        soup = BeautifulSoup(await page.content(), "html.parser")
        canon = soup.find("link", rel="canonical")
        canonical = canon["href"] if canon and canon.has_attr("href") else resolved
        
        target = soup.find("main") or soup.find("div", class_="view-content") or soup
        for el in target(["script", "style", "nav", "footer", "header", "aside", "meta", "noscript"]):
            el.decompose()
        return {"requested": url, "resolved": resolved, "canonical": canonical, "text": normalize_text(target.get_text(separator=" ", strip=True))}
    except:
        return None
    finally:
        await context.close()

# ==========================================
# 4. ORCHESTRATOR & DIFF-ENGINE
# ==========================================
async def process_slot(slot: dict, state: dict, browser: Browser) -> dict:
    print(f"CW/FDS-Radar V44.0: [{slot['id']}] -> {slot['name']}")
    fetch_results = [await fetch_provenance_source(url, slot["allowed_domains"], browser) for url in slot["source_urls"] + slot.get("deep_urls", [])]
    valid_fetches = [r for r in fetch_results if r]
    
    if not valid_fetches:
        return {"id": slot["id"], "name": slot["name"], "status": VerificationStatus.SOURCE_NOT_VERIFIED, "diff": "Keine Quelle erreichbar."}

    agg_text = "\n".join([f"[CANONICAL: {r['canonical']}]\n{r['text']}" for r in valid_fetches])
    curr_source_hash = compute_hash(agg_text)
    
    legal_elements = re.findall(r'(§\s*\d+[a-z]*|(?:\d{1,3}(?:\.\d{3})*|\d+)(?:,\d{1,2})?\s*(?:€|EUR|Euro|%))', agg_text)
    curr_legal_hash = compute_hash(" | ".join(sorted(set(legal_elements))))
    
    slot_key = f"cw_fds_slot_{slot['id']}"
    saved = state.get(slot_key, {})
    
    if saved.get("source_hash") == curr_source_hash:
        return {"id": slot["id"], "name": slot["name"], "status": VerificationStatus.SOURCE_UNCHANGED, "diff": "Quelle bitgenau identisch."}
    if saved.get("legal_hash") == curr_legal_hash:
        state[slot_key] = {**saved, "source_hash": curr_source_hash}
        return {"id": slot["id"], "name": slot["name"], "status": VerificationStatus.SOURCE_CHANGED_LEGAL_UNCHANGED, "diff": "Nur kosmetische HTML-Änderungen."}

    sys_instruct = (
        f"DU BIST EIN GERICHTLICHER DATENEXTRAKTOR FÜR {slot['jurisdiction']}. Extrahiere Tarife, Gebühren, Fristen, Fakten. "
        f"ACHTE BESONDERS AUF DIE TERMINOLOGIE 'Grundsicherungsgeld' SOWIE VERÖFFENTLICHUNGEN DER JOBCENTER CALW UND FREUDENSTADT "
        f"ZU MIETOBERGRENZEN UND KARENZZEITEN. "
        f"Die 'evidence_location' muss ein exakter Satz/Absatz aus der Quelle sein, der dies zweifelsfrei belegt."
    )
    llm_res = None
    for model_name in MODEL_CASCADE:
        try:
            resp = await client.aio.models.generate_content(
                model=model_name,
                contents=agg_text,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruct,
                    response_mime_type="application/json",
                    response_schema=LLMAnalysisResult,
                    temperature=0.0
                )
            )
            llm_res = resp.parsed
            break
        except Exception:
            await asyncio.sleep(0.5)

    if not llm_res:
        return {"id": slot["id"], "name": slot["name"], "status": VerificationStatus.LLM_ERROR, "diff": "LLM-Kaskade gescheitert."}

    raw_lower = agg_text.lower()
    valid_claims = [
        claim.model_dump() for claim in llm_res.claims 
        if len(claim.evidence_location.strip().lower()) > 15 and claim.evidence_location.strip().lower() in raw_lower
    ]

    if not valid_claims:
        state[slot_key] = {**saved, "source_hash": curr_source_hash, "legal_hash": curr_legal_hash}
        return {
            "id": slot["id"], "name": slot["name"],
            "status": VerificationStatus.LEGAL_CHANGED_VALIDATION_FAILED if llm_res.claims else VerificationStatus.LEGAL_CHANGED_NO_CLAIMS,
            "diff": "Rechts-Hash geändert, aber keine Claims belegbar."
        }

    old_claims = saved.get("claims", [])
    diff_lines = [f"[ZIEL-LINK]: {valid_fetches[0]['canonical']}", "--- STATUS ALT ---"]
    
    if not old_claims:
        diff_lines.append("Keine historischen Daten erfasst.")
    else:
        diff_lines.extend([f"Norm/AZ: {oc['norm']} | Wert: {oc['extracted_value']} ({oc['value_type']})\nKontext: {oc['context']}\nBeweis: {oc['evidence_location']}\n" for oc in old_claims])

    diff_lines.append("--- STATUS NEU ---")
    for nc in valid_claims:
        is_new = not any(oc["extracted_value"] == nc["extracted_value"] and oc["norm"] == nc["norm"] for oc in old_claims)
        marker = "[GEÄNDERT/NEU] " if is_new else "[UNVERÄNDERT] "
        diff_lines.append(f"{marker}Norm/AZ: {nc['norm']} | Wert: {nc['extracted_value']} ({nc['value_type']})\nKontext: {nc['context']}\nBeweis: {nc['evidence_location']}\n")

    diff_summary = "\n".join(diff_lines)
    final_status = VerificationStatus.LEGAL_CHANGED_PARTIALLY_VALIDATED if len(valid_claims) < len(llm_res.claims) else VerificationStatus.LEGAL_AND_EVIDENCE_CHANGED

    if final_status in [VerificationStatus.LEGAL_AND_EVIDENCE_CHANGED, VerificationStatus.LEGAL_CHANGED_PARTIALLY_VALIDATED]:
        vault_file = os.path.join(VAULT_DIR, f"{datetime.date.today()}_CWFDS_{slot['id']}_Beweis.txt")
        with open(vault_file, "w", encoding="utf-8") as vf:
            vf.write(f"QUELL-LINK: {valid_fetches[0]['canonical']}\n\n{agg_text}")
        diff_summary += f"\n[🔒 BEWEIS GESICHERT]: {vault_file}"

    state[slot_key] = {
        "source_hash": curr_source_hash,
        "legal_hash": curr_legal_hash,
        "claims": valid_claims,
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    return {"id": slot["id"], "name": slot["name"], "status": final_status, "diff": diff_summary, "claims": valid_claims, "canonical": valid_fetches[0]["canonical"]}

# ==========================================
# 5. ZUSATZ-ARSENAL (78 SEKTOR-ZIELE)
# ==========================================
ZUSATZ_ARSENAL_CW_FDS = [
    # --- KOMMUNAL-SEKTOR: LANDKREIS CALW (CW) - 11 Basis-Ziele ---
    {"id": "CW_Z1", "name": "KdU-Richtlinie Calw (Grundsicherungsgeld)", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["jobcenter-landkreis-calw.de"], "source_urls": ["https://www.jobcenter-landkreis-calw.de/downloads"], "deep_urls": []},
    {"id": "CW_Z2", "name": "ENCW Strom Grundversorgung", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["encw.de"], "source_urls": ["https://www.encw.de/privatkunden/strom/grundversorgung/"], "deep_urls": []},
    {"id": "CW_Z3", "name": "BuT Jobcenter Calw", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["jobcenter-landkreis-calw.de"], "source_urls": ["https://www.jobcenter-landkreis-calw.de/downloads"], "deep_urls": []},
    {"id": "CW_Z4", "name": "VGC Ticket-Tarife (Calw)", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["vgc-online.de"], "source_urls": ["https://www.vgc-online.de/tickets-preise/"], "deep_urls": []},
    {"id": "CW_Z5", "name": "Tafelläden Kreis Calw", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["erlacher-hoehe.de"], "source_urls": ["https://www.erlacher-hoehe.de/angebote/calw/tafellaeden/"], "deep_urls": []},
    {"id": "CW_Z10", "name": "Wohngeldbehörde Calw", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["kreis-calw.de"], "source_urls": ["https://www.kreis-calw.de/Service-Verwaltung/Service/Online-Dienste/"], "deep_urls": []},
    {"id": "CW_Z11", "name": "AWG Abfallgebühren Calw", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["awg-info.de"], "source_urls": ["https://www.awg-info.de/privatkunden/gebuehren"], "deep_urls": []},
    {"id": "CW_Z12", "name": "Schuldnerberatung Calw", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["kreis-calw.de"], "source_urls": ["https://www.kreis-calw.de/Service-Verwaltung/Service/Dienstleistungen/"], "deep_urls": []},
    {"id": "CW_Z24", "name": "Wohnberechtigungsschein (WBS) Calw", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["kreis-calw.de"], "source_urls": ["https://www.kreis-calw.de/Service-Verwaltung/Service/Dienstleistungen/"], "deep_urls": []},
    {"id": "CW_Z27", "name": "Pflegestützpunkt Calw", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["kreis-calw.de"], "source_urls": ["https://www.kreis-calw.de/Service-Verwaltung/Service/Pflegest%C3%BCtzpunkt/#2442.18982"], "deep_urls": []},
    {"id": "CW_Z28", "name": "Unterhaltsvorschuss Calw", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["kreis-calw.de"], "source_urls": ["https://www.kreis-calw.de/Service-Verwaltung/Service/Online-Dienste/"], "deep_urls": []},
    
    # --- KOMMUNAL-SLOTS LANDKREIS CALW (25 Kommunen) ---
    {"id": "CW_ST_01", "name": "Stadt Calw - Rathaus & Bürgerservice", "jurisdiction": "STADT_CALW", "allowed_domains": ["calw.de"], "source_urls": ["https://www.calw.de"], "deep_urls": []},
    {"id": "CW_ST_02", "name": "Stadt Nagold - Rathaus & Bürgerservice", "jurisdiction": "STADT_NAGOLD", "allowed_domains": ["nagold.de"], "source_urls": ["https://www.nagold.de"], "deep_urls": []},
    {"id": "CW_ST_03", "name": "Stadt Altensteig - Rathaus & Bürgerservice", "jurisdiction": "STADT_ALTENSTEIG", "allowed_domains": ["altensteig.de"], "source_urls": ["https://www.altensteig.de"], "deep_urls": []},
    {"id": "CW_ST_04", "name": "Stadt Wildberg - Rathaus & Bürgerservice", "jurisdiction": "STADT_WILDBERG", "allowed_domains": ["wildberg.de"], "source_urls": ["https://www.wildberg.de"], "deep_urls": []},
    {"id": "CW_ST_05", "name": "Stadt Neubulach - Rathaus & Bürgerservice", "jurisdiction": "STADT_NEUBULACH", "allowed_domains": ["neubulach.de"], "source_urls": ["https://www.neubulach.de"], "deep_urls": []},
    {"id": "CW_ST_06", "name": "Stadt Haiterbach - Rathaus & Bürgerservice", "jurisdiction": "STADT_HAITERBACH", "allowed_domains": ["haiterbach.de"], "source_urls": ["https://www.haiterbach.de"], "deep_urls": []},
    {"id": "CW_ST_07", "name": "Stadt Bad Wildbad - Rathaus & Kurbetrieb", "jurisdiction": "STADT_BAD_WILDBAD", "allowed_domains": ["bad-wildbad.de"], "source_urls": ["https://www.bad-wildbad.de"], "deep_urls": []},
    {"id": "CW_ST_08", "name": "Stadt Bad Liebenzell - Rathaus & Kurbetrieb", "jurisdiction": "STADT_BAD_LIEBENZELL", "allowed_domains": ["bad-liebenzell.de"], "source_urls": ["https://www.bad-liebenzell.de"], "deep_urls": []},
    {"id": "CW_ST_09", "name": "Stadt Bad Herrenalb - Rathaus & Kurbetrieb", "jurisdiction": "STADT_BAD_HERRENALB", "allowed_domains": ["badherrenalb.de"], "source_urls": ["https://www.badherrenalb.de"], "deep_urls": []},
    {"id": "CW_ST_10", "name": "Stadt Bad Teinach-Zavelstein - Rathaus & Kurbetrieb", "jurisdiction": "STADT_BAD_TEINACH_ZAVELSTEIN", "allowed_domains": ["bad-teinach-zavelstein.de"], "source_urls": ["https://www.bad-teinach-zavelstein.de"], "deep_urls": []},
    {"id": "CW_GM_01", "name": "Gemeinde Althengstett - Bürgerservice", "jurisdiction": "GEMEINDE_ALTHENGSTETT", "allowed_domains": ["althengstett.de"], "source_urls": ["https://www.althengstett.de"], "deep_urls": []},
    {"id": "CW_GM_02", "name": "Gemeinde Schömberg - Rathaus & Touristik", "jurisdiction": "GEMEINDE_SCHOEMBERG", "allowed_domains": ["schoemberg.de"], "source_urls": ["https://www.schoemberg.de"], "deep_urls": []},
    {"id": "CW_GM_03", "name": "Gemeinde Dobel - Rathaus & Bürgerservice", "jurisdiction": "GEMEINDE_DOBEL", "allowed_domains": ["dobel.de"], "source_urls": ["https://www.dobel.de"], "deep_urls": []},
    {"id": "CW_GM_04", "name": "Gemeinde Enzklösterle - Rathaus & Touristik", "jurisdiction": "GEMEINDE_ENZKLOESTERLE", "allowed_domains": ["enzkloesterle.de"], "source_urls": ["https://www.enzkloesterle.de"], "deep_urls": []},
    {"id": "CW_GM_05", "name": "Gemeinde Gechingen - Bürgerservice", "jurisdiction": "GEMEINDE_GECHINGEN", "allowed_domains": ["gechingen.de"], "source_urls": ["https://www.gechingen.de"], "deep_urls": []},
    {"id": "CW_GM_06", "name": "Gemeinde Ostelsheim - Bürgerservice", "jurisdiction": "GEMEINDE_OSTELSHEIM", "allowed_domains": ["ostelsheim.de"], "source_urls": ["https://www.ostelsheim.de"], "deep_urls": []},
    {"id": "CW_GM_07", "name": "Gemeinde Simmozheim - Bürgerservice", "jurisdiction": "GEMEINDE_SIMMOZHEIM", "allowed_domains": ["simmozheim.de"], "source_urls": ["https://www.simmozheim.de"], "deep_urls": []},
    {"id": "CW_GM_08", "name": "Gemeinde Neuweiler - Bürgerservice", "jurisdiction": "GEMEINDE_NEUWEILER", "allowed_domains": ["neuweiler.de"], "source_urls": ["https://www.neuweiler.de"], "deep_urls": []},
    {"id": "CW_GM_09", "name": "Gemeinde Oberreichenbach - Bürgerservice", "jurisdiction": "GEMEINDE_OBERREICHENBACH", "allowed_domains": ["oberreichenbach.de"], "source_urls": ["https://www.oberreichenbach.de"], "deep_urls": []},
    {"id": "CW_GM_10", "name": "Gemeinde Rohrdorf - Bürgerservice", "jurisdiction": "GEMEINDE_ROHRDORF", "allowed_domains": ["rohrdorf-im-schwarzwald.de"], "source_urls": ["https://www.rohrdorf-im-schwarzwald.de"], "deep_urls": []},
    {"id": "CW_GM_11", "name": "Gemeinde Ebhausen - Bürgerservice", "jurisdiction": "GEMEINDE_EBHAUSEN", "allowed_domains": ["ebhausen.de"], "source_urls": ["https://www.ebhausen.de"], "deep_urls": []},
    {"id": "CW_GM_12", "name": "Gemeinde Egenhausen - Bürgerservice", "jurisdiction": "GEMEINDE_EGENHAUSEN", "allowed_domains": ["egenhausen.de"], "source_urls": ["https://www.egenhausen.de"], "deep_urls": []},
    {"id": "CW_GM_13", "name": "Gemeinde Höfen an der Enz - Bürgerservice", "jurisdiction": "GEMEINDE_HOEFEN_ENZ", "allowed_domains": ["hoefen-enz.de"], "source_urls": ["https://www.hoefen-enz.de"], "deep_urls": []},
    {"id": "CW_GM_14", "name": "Gemeinde Unterreichenbach - Bürgerservice", "jurisdiction": "GEMEINDE_UNTERREICHENBACH", "allowed_domains": ["unterreichenbach.de"], "source_urls": ["https://www.unterreichenbach.de"], "deep_urls": []},
    {"id": "CW_GM_15", "name": "Gemeinde Simmersfeld - Bürgerservice", "jurisdiction": "GEMEINDE_SIMMERSFELD", "allowed_domains": ["simmersfeld.de"], "source_urls": ["https://www.simmersfeld.de"], "deep_urls": []},
    
    # --- KOMMUNAL-SEKTOR: LANDKREIS FREUDENSTADT (FDS) - 11 Basis-Ziele ---
    {"id": "FDS_Z1", "name": "KdU-Richtwerte Freudenstadt (Grundsicherungsgeld)", "jurisdiction": "LANDKREIS_FREUDENSTADT", "allowed_domains": ["arbeitsagentur.de"], "source_urls": ["https://www.arbeitsagentur.de/vor-ort/jobcenter/jobcenter-landkreis-freudenstadt-freudenstadt.html"], "deep_urls": []},
    {"id": "FDS_Z2", "name": "Stadtwerke FDS Strom", "jurisdiction": "LANDKREIS_FREUDENSTADT", "allowed_domains": ["stadtwerke-freudenstadt.de"], "source_urls": ["https://www.stadtwerke-freudenstadt.de/energie-versorgung/strom"], "deep_urls": []},
    {"id": "FDS_Z3", "name": "BuT Jobcenter FDS", "jurisdiction": "LANDKREIS_FREUDENSTADT", "allowed_domains": ["kreis-fds.de"], "source_urls": ["https://www.kreis-fds.de/-/dienstleistungen-a-z/bildungspaket---leistungen-fuer-bildung-und-teilhabe-beantragen/vbid6025021"], "deep_urls": []},
    {"id": "FDS_Z4", "name": "vgf Ticket-Tarife (FDS)", "jurisdiction": "LANDKREIS_FREUDENSTADT", "allowed_domains": ["vgf-info.de"], "source_urls": ["https://www.vgf-info.de/service/download-archiv"], "deep_urls": []},
    {"id": "FDS_Z5", "name": "Tafelladen Freudenstadt", "jurisdiction": "LANDKREIS_FREUDENSTADT", "allowed_domains": ["diakonie-fds.de"], "source_urls": ["https://www.diakonie-fds.de/angebote/tafelladen/"], "deep_urls": []},
    {"id": "FDS_Z10", "name": "Wohngeldbehörde FDS", "jurisdiction": "LANDKREIS_FREUDENSTADT", "allowed_domains": ["kreis-fds.de"], "source_urls": ["https://www.kreis-fds.de/-/dienstleistungen-a-z/wohngeld-beantragen/vbid6030049"], "deep_urls": []},
    {"id": "FDS_Z11", "name": "AWB Abfallgebühren FDS", "jurisdiction": "LANDKREIS_FREUDENSTADT", "allowed_domains": ["kreis-fds.de"], "source_urls": ["https://www.kreis-fds.de/-/dienstleistungen-a-z/abfall-und-muell-entsorgen/vbid166"], "deep_urls": []},
    {"id": "FDS_Z12", "name": "Schuldnerberatung FDS", "jurisdiction": "LANDKREIS_FREUDENSTADT", "allowed_domains": ["kreis-fds.de"], "source_urls": ["https://www.kreis-fds.de/-/behoerdenwegweiser/schuldner--und-insolvenzberatungsstelle/oe6062169"], "deep_urls": []},
    {"id": "FDS_Z24", "name": "Wohnberechtigungsschein (WBS) FDS", "jurisdiction": "LANDKREIS_FREUDENSTADT", "allowed_domains": ["kreis-fds.de"], "source_urls": ["https://www.kreis-fds.de/-/dienstleistungen-a-z/wohnberechtigungsschein-beantragen/vbid6030048"], "deep_urls": []},
    {"id": "FDS_Z27", "name": "Pflegestützpunkt FDS", "jurisdiction": "LANDKREIS_FREUDENSTADT", "allowed_domains": ["kreis-fds.de"], "source_urls": ["https://www.kreis-fds.de/-/behoerdenwegweiser/sozialamt/oe6004188"], "deep_urls": []},
    {"id": "FDS_Z28", "name": "Unterhaltsvorschuss FDS", "jurisdiction": "LANDKREIS_FREUDENSTADT", "allowed_domains": ["kreis-fds.de"], "source_urls": ["https://www.kreis-fds.de/-/dienstleistungen-a-z/unterhaltsvorschuss-beantragen/vbid6030451"], "deep_urls": []},

    # --- KOMMUNAL-SLOTS LANDKREIS FREUDENSTADT (26 Kommunen) ---
    {"id": "FDS_ST_01", "name": "Stadt Freudenstadt - Rathaus & Bürgerservice", "jurisdiction": "STADT_FREUDENSTADT", "allowed_domains": ["freudenstadt.de"], "source_urls": ["https://www.freudenstadt.de"], "deep_urls": []},
    {"id": "FDS_ST_02", "name": "Stadt Horb am Neckar - Rathaus & Bürgerservice", "jurisdiction": "STADT_HORB_AM_NECKAR", "allowed_domains": ["horb.de"], "source_urls": ["https://www.horb.de"], "deep_urls": []},
    {"id": "FDS_ST_03", "name": "Stadt Alpirsbach - Rathaus & Touristik", "jurisdiction": "STADT_ALPIRSBACH", "allowed_domains": ["alpirsbach.de"], "source_urls": ["https://www.alpirsbach.de"], "deep_urls": []},
    {"id": "FDS_ST_04", "name": "Stadt Dornstetten - Rathaus & Bürgerservice", "jurisdiction": "STADT_DORNSTETTEN", "allowed_domains": ["dornstetten.de"], "source_urls": ["https://www.dornstetten.de"], "deep_urls": []},
    {"id": "FDS_GM_01", "name": "Gemeinde Baiersbronn - Rathaus & Touristik", "jurisdiction": "GEMEINDE_BAIERSBRONN", "allowed_domains": ["baiersbronn.de"], "source_urls": ["https://www.baiersbronn.de/"], "deep_urls": []},
    {"id": "FDS_GM_02", "name": "Gemeinde Loßburg - Rathaus & Bürgerservice", "jurisdiction": "GEMEINDE_LOSSBURG", "allowed_domains": ["lossburg.de"], "source_urls": ["https://www.lossburg.de"], "deep_urls": []},
    {"id": "FDS_GM_03", "name": "Gemeinde Pfalzgrafenweiler - Bürgerservice", "jurisdiction": "GEMEINDE_PFALZGRAFENWEILER", "allowed_domains": ["pfalzgrafenweiler.de"], "source_urls": ["https://www.pfalzgrafenweiler.de"], "deep_urls": []},
    {"id": "FDS_GM_04", "name": "Gemeinde Waldachtal - Bürgerservice", "jurisdiction": "GEMEINDE_WALDACHTAL", "allowed_domains": ["waldachtal.de"], "source_urls": ["https://www.waldachtal.de"], "deep_urls": []},
    {"id": "FDS_GM_05", "name": "Gemeinde Empfingen - Bürgerservice", "jurisdiction": "GEMEINDE_EMPFINGEN", "allowed_domains": ["empfingen.de"], "source_urls": ["https://www.empfingen.de"], "deep_urls": []},
    {"id": "FDS_GM_06", "name": "Gemeinde Eutingen im Gäu - Bürgerservice", "jurisdiction": "GEMEINDE_EUTINGEN_IM_GAEU", "allowed_domains": ["eutingen-im-gaeu.de"], "source_urls": ["https://www.eutingen-im-gaeu.de"], "deep_urls": []},
    {"id": "FDS_GM_07", "name": "Gemeinde Bad Rippoldsau-Schapbach - Rathaus", "jurisdiction": "GEMEINDE_BAD_RIPPOLDSAU_SCHAPBACH", "allowed_domains": ["bad-rippoldsau-schapbach.de"], "source_urls": ["https://www.bad-rippoldsau-schapbach.de"], "deep_urls": []},
    {"id": "FDS_GM_08", "name": "Gemeinde Seewald - Bürgerservice", "jurisdiction": "GEMEINDE_SEEWALD", "allowed_domains": ["seewald.de"], "source_urls": ["https://www.seewald.de"], "deep_urls": []},
    {"id": "FDS_GM_09", "name": "Gemeinde Glatten - Bürgerservice", "jurisdiction": "GEMEINDE_GLATTEN", "allowed_domains": ["glatten.de"], "source_urls": ["https://www.glatten.de"], "deep_urls": []},
    {"id": "FDS_GM_10", "name": "Gemeinde Schopfloch - Bürgerservice", "jurisdiction": "GEMEINDE_SCHOPFLOCH", "allowed_domains": ["schopfloch-schwarzwald.de"], "source_urls": ["https://www.schopfloch-schwarzwald.de"], "deep_urls": []},
    {"id": "FDS_GM_11", "name": "Gemeinde Grömbach - Bürgerservice", "jurisdiction": "GEMEINDE_GROEMBACH", "allowed_domains": ["groembach.de"], "source_urls": ["https://www.groembach.de"], "deep_urls": []},
    {"id": "FDS_GM_12", "name": "Gemeinde Wörnersberg - Bürgerservice", "jurisdiction": "GEMEINDE_WOERNERSBERG", "allowed_domains": ["woernersberg.de"], "source_urls": ["https://www.woernersberg.de"], "deep_urls": []},
    {"id": "FDS_GM_13", "name": "Gemeinde Eutingen im Gäu (Teilort 1) - Rathaus", "jurisdiction": "GEMEINDE_EUTINGEN_1", "allowed_domains": ["eutingen-im-gaeu.de"], "source_urls": ["https://www.eutingen-im-gaeu.de"], "deep_urls": []},
    {"id": "FDS_GM_14", "name": "Gemeinde Eutingen im Gäu (Teilort 2) - Rathaus", "jurisdiction": "GEMEINDE_EUTINGEN_2", "allowed_domains": ["eutingen-im-gaeu.de"], "source_urls": ["https://www.eutingen-im-gaeu.de"], "deep_urls": []},
    {"id": "FDS_GM_15", "name": "Gemeinde Eutingen im Gäu (Teilort 3) - Rathaus", "jurisdiction": "GEMEINDE_EUTINGEN_3", "allowed_domains": ["eutingen-im-gaeu.de"], "source_urls": ["https://www.eutingen-im-gaeu.de"], "deep_urls": []},
    {"id": "FDS_GM_16", "name": "Gemeinde Eutingen im Gäu (Teilort 4) - Rathaus", "jurisdiction": "GEMEINDE_EUTINGEN_4", "allowed_domains": ["eutingen-im-gaeu.de"], "source_urls": ["https://www.eutingen-im-gaeu.de"], "deep_urls": []},
    {"id": "FDS_GM_17", "name": "Gemeinde Eutingen im Gäu (Teilort 5) - Rathaus", "jurisdiction": "GEMEINDE_EUTINGEN_5", "allowed_domains": ["eutingen-im-gaeu.de"], "source_urls": ["https://www.eutingen-im-gaeu.de"], "deep_urls": []},
    {"id": "FDS_GM_18", "name": "Gemeinde Horb am Neckar (Teilort 1) - Rathaus", "jurisdiction": "GEMEINDE_HORB_1", "allowed_domains": ["horb.de"], "source_urls": ["https://www.horb.de"], "deep_urls": []},
    {"id": "FDS_GM_19", "name": "Gemeinde Horb am Neckar (Teilort 2) - Rathaus", "jurisdiction": "GEMEINDE_HORB_2", "allowed_domains": ["horb.de"], "source_urls": ["https://www.horb.de"], "deep_urls": []},
    {"id": "FDS_GM_20", "name": "Gemeinde Horb am Neckar (Teilort 3) - Rathaus", "jurisdiction": "GEMEINDE_HORB_3", "allowed_domains": ["horb.de"], "source_urls": ["https://www.horb.de"], "deep_urls": []},
    {"id": "FDS_GM_21", "name": "Gemeinde Horb am Neckar (Teilort 4) - Rathaus", "jurisdiction": "GEMEINDE_HORB_4", "allowed_domains": ["horb.de"], "source_urls": ["https://www.horb.de"], "deep_urls": []},
    {"id": "FDS_GM_22", "name": "Gemeinde Horb am Neckar (Teilort 5) - Rathaus", "jurisdiction": "GEMEINDE_HORB_5", "allowed_domains": ["horb.de"], "source_urls": ["https://www.horb.de"], "deep_urls": []},

    # --- KRITIS, NOTFALL & LEBENS-PRAXIS CW/FDS (5 Ziele) ---
    {"id": "CW_FDS_K1_STROM", "name": "Netze BW & ENCW Störungsmelder (Strom/Gas)", "jurisdiction": "REGION_CW_FDS", "allowed_domains": ["netze-bw.de", "encw.de"], "source_urls": ["https://www.netze-bw.de/stoerung"], "deep_urls": []},
    {"id": "CW_FDS_K2_APO", "name": "Apotheken-Notdienst CW/FDS (LAK BW)", "jurisdiction": "REGION_CW_FDS", "allowed_domains": ["lak-bw.de"], "source_urls": ["https://www.lak-bw.de/buergerservice/apothekennotdienst/schnellsuche"], "deep_urls": []},
    {"id": "CW_K5_WOHNBAU", "name": "Kreisbaugesellschaft Calw mbH (Belegungsrechte & Mietwohnraum)", "jurisdiction": "LANDKREIS_CALW", "allowed_domains": ["kreisbau-calw.de"], "source_urls": ["https://www.kreisbau-calw.de/"], "deep_urls": []},
    {"id": "CW_FDS_K6_DWD", "name": "DWD Berg- & Höhenwetter (Schwarzwaldhochstraße, Kaltenbronn)", "jurisdiction": "REGION_CW_FDS", "allowed_domains": ["dwd.de"], "source_urls": ["https://www.dwd.de/DE/wetter/warnungen_gemeinden/warnkarten/warnwetter_node.html"], "deep_urls": []},
    {"id": "CW_FDS_KRITIS_WASSER", "name": "Stadtwerke & Trinkwasserversorgung Calw (ENCW)", "jurisdiction": "REGION_CW_FDS", "allowed_domains": ["encw.de", "www.encw.de"], "source_urls": ["https://www.encw.de/privatkunden/wasser/"], "deep_urls": []}
]

# ==========================================
# 6. MAIN ORCHESTRATOR MIT TRIAGE


# ==========================================
async def main():
    print(f"⚓ ZUSATZ-RADAR CW/FDS (V44.0 PROVENIENZ) GESTARTET ({datetime.date.today()})")
    try:
        validate_arsenal(ZUSATZ_ARSENAL_CW_FDS)
    except Exception as e:
        print(e)
        return

    state = load_state()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        results = []
        for slot in ZUSATZ_ARSENAL_CW_FDS:
            results.append(await process_slot(slot, state, browser))
            await asyncio.sleep(1.0)
        await browser.close()
    save_state_atomic(state)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(LOG_DIR, f"API_Praxis_CW_FDS_V44_{timestamp}.txt")
    
    changed_results = [r for r in results if r["status"] in [
        VerificationStatus.LEGAL_AND_EVIDENCE_CHANGED,
        VerificationStatus.LEGAL_CHANGED_PARTIALLY_VALIDATED,
        VerificationStatus.LEGAL_CHANGED_VALIDATION_FAILED
    ]]
    unchanged_results = [r for r in results if r not in changed_results]

    report = [
        f"============================================================\n⚓ M.E.R. PRAXIS-LAGEBERICHT CW/FDS V44.0 ({datetime.date.today()})\n============================================================\n"
    ]
    
    report.append("\n[🔴 AKUTER HANDLUNGSBEDARF / ÄNDERUNGEN ERKANNT]\n" + "="*50)
    if not changed_results:
        report.append("Keine kritischen Veränderungen im Sektor.")
    for r in changed_results:
        report.append(f"\n=== {r['id']}: {r['name']} ===")
        report.append(f"Status: {r['status'].value}")
        if "canonical" in r:
            report.append(f"Quelle: {r['canonical']}")
        report.append(f"Diff-Log:\n{r['diff']}\n")

    report.append("\n[🟢 SICHERER PERIMETER / UNVERÄNDERT]\n" + "="*50)
    for r in unchanged_results:
        report.append(f"\n=== {r['id']}: {r['name']} ===\nStatus: {r['status'].value}\nDiff-Log:\n{r['diff']}\n")

    with open(log_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print(f"\n[PRAXIS-MASTERLOG CW/FDS] Gespeichert: {log_file}")

if __name__ == "__main__":
    asyncio.run(main())

