"""⚓ DEFCON RECHT RADAR V44.0 "HERTZ-SHIELD" (OPERATION PROVENIENZ)

Architektur: Playwright + Secure-PDF-Bypass + Config-Gate + Strict-Evidence +
Triage + Vault
Gebiet: BUND, PFORZHEIM, ENZKREIS, BW (Strikt isoliertes Geofencing)
"""

import asyncio
import datetime
import hashlib
import io
import ipaddress
import json
import os
import random
import re
import socket
import tempfile
import unicodedata
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from enum import Enum
from google import genai
from google.genai import types
from google.genai.errors import APIError
from playwright.async_api import Browser, Request, Route, async_playwright
import pypdf
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

# ==========================================
# 1. KONFIGURATION & CONFIG-GATE
# ==========================================
EXPECTED_SLOT_COUNT = (
    35  # Exakte Anzahl inkl. Unterteilungen (A/B) und BA-Slots
)
BASE_DIR = r"C:\DefconRecht"
STATE_FILE = os.path.join(BASE_DIR, "radar_state_v44.json")
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
  if len(arsenal) != EXPECTED_SLOT_COUNT:
    raise ValueError(
        f"CONFIG ERROR: {EXPECTED_SLOT_COUNT} Slots erwartet, {len(arsenal)}"
        " geladen."
    )
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
  norm: str = Field(
      ..., description="Rechtsnorm, Aktenzeichen oder Urteil/Satzung"
  )
  extracted_value: str = Field(
      ...,
      description=(
          "Vollständige Kernaussage, der Leitsatz oder konkreter Betrag"
      ),
  )
  value_type: ValueType = Field(
      ..., description="Typ des Wertes (Bei Urteilen zwingend URTEIL_TEXT)"
  )
  context: str = Field(
      ..., description="Zusammenfassung des rechtlichen Sachverhalts"
  )
  evidence_location: str = Field(
      ...,
      description=(
          "Exakter Original-Textausschnitt aus der Webseite als absoluter"
          " Beweis"
      ),
  )


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
  with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=4, ensure_ascii=False)
    f.flush()
    os.fsync(f.fileno())
  os.replace(tmp, STATE_FILE)


def compute_hash(text: str) -> str:
  return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
  return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


# ==========================================
# 3. SECURITY-GATES & SECURE-FETCHING
# ==========================================
class SecurityGate:
  BLOCKED_CMP = [
      "usercentrics",
      "cookiebot",
      "etracker",
      "matomo",
      "consentmanager",
  ]

  @staticmethod
  async def resolve_and_check_ip(hostname: str):
    loop = asyncio.get_running_loop()
    addr_info = await loop.getaddrinfo(
        hostname, 443, family=socket.AF_INET, type=socket.SOCK_STREAM
    )
    for _, _, _, _, sockaddr in addr_info:
      ip = ipaddress.ip_address(sockaddr[0])
      if (
          ip.is_private
          or ip.is_loopback
          or ip.is_link_local
          or ip.is_multicast
          or ip.is_reserved
      ):
        raise Exception(
            f"TOCTOU/SSRF-Blockade: Private IP {sockaddr[0]} detektiert."
        )
    return True

  @staticmethod
  async def intercept_route(
      route: Route, request: Request, allowed_domains: List[str]
  ):
    try:
      parsed = urlparse(request.url)
      if parsed.scheme not in ["https", "http"] or not parsed.hostname:
        return await route.abort()
      if any(cmp in parsed.hostname for cmp in SecurityGate.BLOCKED_CMP):
        return await route.abort()
      if not any(
          parsed.hostname == d or parsed.hostname.endswith("." + d)
          for d in allowed_domains
      ):
        return await route.abort()
      await SecurityGate.resolve_and_check_ip(parsed.hostname)
      await route.continue_()
    except:
      await route.abort()


async def secure_fetch_pdf(
    url: str, allowed_domains: List[str], context
) -> Optional[Dict[str, str]]:
  parsed = urlparse(url)
  if not parsed.hostname or not any(
      parsed.hostname == d or parsed.hostname.endswith("." + d)
      for d in allowed_domains
  ):
    return None
  try:
    await SecurityGate.resolve_and_check_ip(parsed.hostname)
    response = await context.request.get(url, timeout=30000)
    if not response.ok:
      return None
    reader = pypdf.PdfReader(io.BytesIO(await response.body()), strict=False)
    text = "\n".join([
        f"[PAGE {i+1}] {normalize_text(p.extract_text() or '')}"
        for i, p in enumerate(reader.pages)
    ])
    return {
        "requested": url,
        "resolved": response.url,
        "canonical": url,
        "text": text,
    }
  except Exception as e:
    print(f"[PDF SECURE FETCH ERROR] {e}")
    return None


async def fetch_provenance_source(
    url: str, allowed_domains: List[str], browser: Browser
) -> Optional[Dict[str, str]]:
  context = await browser.new_context(
        ignore_https_errors=False,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="de-DE"
    )
  if url.lower().endswith(".pdf") or "blob=" in url.lower():
    res = await secure_fetch_pdf(url, allowed_domains, context)
    await context.close()
    return res

  await context.route(
      "**/*",
      lambda route, req: SecurityGate.intercept_route(
          route, req, allowed_domains
      ),
  )
  page = await context.new_page()
    await page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver;")
  try:
    response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    if not response:
      return None
    resolved = response.url
    await page.wait_for_timeout(3000)

    soup = BeautifulSoup(await page.content(), "html.parser")
    canon = soup.find("link", rel="canonical")
    canonical = canon["href"] if canon and canon.has_attr("href") else resolved

    target = (
        soup.find("main") or soup.find("div", class_="view-content") or soup
    )
    for el in target([
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "meta",
        "noscript",
    ]):
      el.decompose()

    return {
        "requested": url,
        "resolved": resolved,
        "canonical": canonical,
        "text": normalize_text(target.get_text(separator=" ", strip=True)),
    }
  except Exception as e:
    print(f"[FETCH ERROR] {e}")
    return None
  finally:
    await context.close()


# ==========================================
# 4. ORCHESTRATOR & DIFF-ENGINE
# ==========================================
async def process_slot(slot: dict, state: dict, browser: Browser) -> dict:
  print(f"Haupt-Flotte Scan V44.0: [{slot['id']}] -> {slot['name']}")
  fetch_results = [
      await fetch_provenance_source(url, slot["allowed_domains"], browser)
      for url in slot["source_urls"]
  ]
  valid_fetches = [r for r in fetch_results if r]

  if not valid_fetches:
    return {
        "id": slot["id"],
        "name": slot["name"],
        "status": VerificationStatus.SOURCE_NOT_VERIFIED,
        "diff": "Keine Quelle erreichbar.",
    }

  agg_text = "\n".join(
      [f"[CANONICAL: {r['canonical']}]\n{r['text']}" for r in valid_fetches]
  )
  curr_source_hash = compute_hash(agg_text)

  legal_elements = re.findall(
      r"(§\s*\d+[a-z]*|(?:\d{1,3}(?:\.\d{3})*|\d+)(?:,\d{1,2})?\s*(?:€|EUR|Euro|%))",
      agg_text,
  )
  curr_legal_hash = compute_hash(" | ".join(sorted(set(legal_elements))))

  slot_key = f"slot_{slot['id']}"
  saved = state.get(slot_key, {})

  if saved.get("source_hash") == curr_source_hash:
    return {
        "id": slot["id"],
        "name": slot["name"],
        "status": VerificationStatus.SOURCE_UNCHANGED,
        "diff": "Quelle bitgenau identisch.",
    }

  if saved.get("legal_hash") == curr_legal_hash:
    state[slot_key] = {**saved, "source_hash": curr_source_hash}
    return {
        "id": slot["id"],
        "name": slot["name"],
        "status": VerificationStatus.SOURCE_CHANGED_LEGAL_UNCHANGED,
        "diff": "Nur kosmetische HTML-Änderungen.",
    }

  sys_instruct = (
      f"DU BIST EIN GERICHTLICHER DATENEXTRAKTOR FÜR {slot['jurisdiction']}."
      " Extrahiere Beträge, Fristen, Fakten UND VOLLSTÄNDIGE URTEILS-LEITSÄTZE"
      " SOWIE AKTENZEICHEN. ACHTE BEI SGB II BESONDERS AUF DIE TERMINOLOGIE"
      " 'Grundsicherungsgeld' UND DIE KARENZZEIT- SOWIE"
      " KDU-OBERWEG-REGELUNGEN (§ 22 SGB II). Die 'evidence_location' muss ein"
      " exakter Satz/Absatz aus der Quelle sein, der dies zweifelsfrei belegt."
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
              temperature=0.0,
          ),
      )
      llm_res = resp.parsed
      break
    except Exception:
      await asyncio.sleep(0.5)

  if not llm_res:
    return {
        "id": slot["id"],
        "name": slot["name"],
        "status": VerificationStatus.LLM_ERROR,
        "diff": "LLM-Kaskade gescheitert.",
    }

  raw_lower = agg_text.lower()
  valid_claims = []
  for claim in llm_res.claims:
    ev_lower = claim.evidence_location.strip().lower()
    if len(ev_lower) > 15 and ev_lower in raw_lower:
      valid_claims.append(claim.model_dump())

  if not valid_claims:
    state[slot_key] = {**saved, "source_hash": curr_source_hash, "legal_hash": curr_legal_hash}
    return {
        "id": slot["id"],
        "name": slot["name"],
        "status": (
            VerificationStatus.LEGAL_CHANGED_VALIDATION_FAILED
            if llm_res.claims
            else VerificationStatus.LEGAL_CHANGED_NO_CLAIMS
        ),
        "diff": "Rechts-Hash geändert, aber keine Claims belegbar.",
    }

  old_claims = saved.get("claims", [])
  diff_lines = []

  diff_lines.append(f"[ZIEL-LINK]: {valid_fetches[0]['canonical']}")
  diff_lines.append("--- STATUS ALT (Vorheriger Scan) ---")

  if not old_claims:
    diff_lines.append(
        "Keine historischen Daten erfasst (Erster Scan oder leer)."
    )
  else:
    for oc in old_claims:
      diff_lines.append(
          f"Norm/AZ: {oc['norm']} | Wert: {oc['extracted_value']}"
          f" ({oc['value_type']})\nKontext: {oc['context']}\nBeweis:"
          f" {oc['evidence_location']}\n"
      )

  diff_lines.append("--- STATUS NEU (Aktueller Scan) ---")

  if not valid_claims:
    diff_lines.append("Keine extrahierbaren rechtlichen Parameter gefunden.")
  else:
    for nc in valid_claims:
      is_new = not any(
          oc["extracted_value"] == nc["extracted_value"]
          and oc["norm"] == nc["norm"]
          for oc in old_claims
      )
      marker = "[GEÄNDERT/NEU] " if is_new else "[UNVERÄNDERT] "
      diff_lines.append(
          f"{marker}Norm/AZ: {nc['norm']} | Wert: {nc['extracted_value']}"
          f" ({nc['value_type']})\nKontext: {nc['context']}\nBeweis:"
          f" {nc['evidence_location']}\n"
      )

  diff_summary = "\n".join(diff_lines)
  final_status = (
      VerificationStatus.LEGAL_CHANGED_PARTIALLY_VALIDATED
      if len(valid_claims) < len(llm_res.claims)
      else VerificationStatus.LEGAL_AND_EVIDENCE_CHANGED
  )

  if final_status in [
      VerificationStatus.LEGAL_AND_EVIDENCE_CHANGED,
      VerificationStatus.LEGAL_CHANGED_PARTIALLY_VALIDATED,
  ]:
    vault_file = os.path.join(
        VAULT_DIR, f"{datetime.date.today()}_{slot['id']}_Beweis.txt"
    )
    with open(vault_file, "w", encoding="utf-8") as vf:
      vf.write(f"QUELL-LINK: {valid_fetches[0]['canonical']}\n\n{agg_text}")
    diff_summary += f"\n[🔒 BEWEIS GESICHERT]: {vault_file}"

  state[slot_key] = {
      "source_hash": curr_source_hash,
      "legal_hash": curr_legal_hash,
      "claims": valid_claims,
      "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  }
  return {
      "id": slot["id"],
      "name": slot["name"],
      "status": final_status,
      "diff": diff_summary,
      "claims": valid_claims,
      "canonical": valid_fetches[0]["canonical"],
  }


# ==========================================
# 5. ZIELKOORDINATEN (EXAKT 34 SEKTOR-ZIELE)
# ==========================================
TARGETS_ARSENAL = [
    {
        "id": "1",
        "name": "SGB II - KdU & Karenzzeit",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/sgb_2/__22.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/sgb_2/__22.pdf"],
    },
    {
        "id": "2",
        "name": "SGB II - Regelbedarf",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/sgb_2/__20.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/sgb_2/__20.pdf"],
    },
    {
        "id": "3",
        "name": "SGB II - Mehrbedarfe",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/sgb_2/__21.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/sgb_2/__21.pdf"],
    },
    {
        "id": "4",
        "name": "SGB XII - Grundsicherung",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/sgb_12/__41.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/sgb_12/__41.pdf"],
    },
    {
        "id": "5",
        "name": "SGB XII - KdU",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/sgb_12/__35.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/sgb_12/__35.pdf"],
    },
    {
        "id": "6",
        "name": "SGB XI - Entlastungsbetrag",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/sgb_11/__45b.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/sgb_11/__45b.pdf"],
    },
    {
        "id": "7",
        "name": "SGB XI - Pflegegeld",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/sgb_11/__37.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/sgb_11/__37.pdf"],
    },
    {
        "id": "8",
        "name": "SGB XI - Pflegesachleistung",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/sgb_11/__36.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/sgb_11/__36.pdf"],
    },
    {
        "id": "9A",
        "name": "SGB XI - Verhinderungspflege",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/sgb_11/__39.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/sgb_11/__39.pdf"],
    },
    {
        "id": "9B",
        "name": "SGB XI - Jahresbetrag",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/sgb_11/__42a.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/sgb_11/__42a.pdf"],
    },
    {
        "id": "10A",
        "name": "WoGG - Zu berücksichtigende Miete und Belastung",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/wogg/__11.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/wogg/__11.pdf"],
    },
    {
        "id": "10B",
        "name": "WoGG - Höchstbeträge und Mietenstufen",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/wogg/__12.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/wogg/anlage_1.pdf"],
    },
    {
        "id": "11A",
        "name": "Kinderzuschlag",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": [
            "https://www.gesetze-im-internet.de/bkgg_1996/__6a.html"
        ],
        "deep_urls": ["https://www.gesetze-im-internet.de/bkgg_1996/__6a.pdf"],
    },
    {
        "id": "11B",
        "name": "Kindergeld",
        "jurisdiction": "BUND",
        "allowed_domains": ["gesetze-im-internet.de"],
        "source_urls": ["https://www.gesetze-im-internet.de/estg/__66.html"],
        "deep_urls": ["https://www.gesetze-im-internet.de/estg/__66.pdf"],
    },
    {
        "id": "12A",
        "name": "KdU-Richtlinie Pforzheim (Grundsicherungsgeld)",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["jobcenter.pforzheim.de"],
        "source_urls": [
            "https://jobcenter.pforzheim.de/finanzielle-leistungen/leistungen-fuer-unterkunft-und-heizung.html"
        ],
        "deep_urls": [
            "https://jobcenter.pforzheim.de/fileadmin/user_upload/Richtlinien/KdU_Richtlinie_Pforzheim_aktuell.pdf"
        ],
    },
    {
        "id": "12B",
        "name": "KdU-Enzkreis Info",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["enzkreis.de"],
        "source_urls": [
            "https://www.enzkreis.de/Landratsamt/%C3%84mter-Dezernate/Dezernat-4-Familie-und-Soziales/Jobcenter-Enzkreis/"
        ],
        "deep_urls": [
            "https://www.enzkreis.de/media/custom/3397_KdU_Richtwerte_Enzkreis.PDF"
        ],
    },
    {
        "id": "13",
        "name": "SG Karlsruhe",
        "jurisdiction": "GERICHT_KARLSRUHE",
        "allowed_domains": ["sozialgerichtsbarkeit.de"],
        "source_urls": ["https://sozialgerichtsbarkeit.de/entscheidungen"],
        "deep_urls": [
            "https://sozialgerichtsbarkeit.de/entscheidungen/aktuell_sg_karlsruhe.rss"
        ],
    },
    {
        "id": "14",
        "name": "LSG Baden-Württemberg",
        "jurisdiction": "GERICHT_LSG_BW",
        "allowed_domains": ["sozialgerichtsbarkeit.de"],
        "source_urls": ["https://sozialgerichtsbarkeit.de/entscheidungen"],
        "deep_urls": [
            "https://sozialgerichtsbarkeit.de/entscheidungen/aktuell_lsg_bw.rss"
        ],
    },
    {
        "id": "15",
        "name": "BA - SGB III & Sperrzeiten",
        "jurisdiction": "BUND",
        "allowed_domains": ["arbeitsagentur.de", "gesetze-im-internet.de"],
        "source_urls": [
            "https://www.gesetze-im-internet.de/sgb_3/__159.html"
        ],
        "deep_urls": ["https://www.gesetze-im-internet.de/sgb_3/__159.pdf"],
    },
    {
        "id": "16",
        "name": "BVerfG - Sozialrecht & Entscheidungsübersicht",
        "jurisdiction": "BUND",
        "allowed_domains": ["bundesverfassungsgericht.de"],
        "source_urls": [
            "https://www.bundesverfassungsgericht.de/DE/Entscheidungen/entscheidungen_node.html"
        ],
        "deep_urls": [
            "https://www.bundesverfassungsgericht.de/DE/Entscheidungen/Pressemitteilungen/pressemitteilungen_node.html"
        ],
    },
    {
        "id": "17",
        "name": "Stadt Pforzheim - Stadtrecht",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/gemeinderat/stadtrecht/4-soziale-sicherung.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/stadtrecht/Ortsrecht_Sammelband.pdf"
        ],
    },
    {
        "id": "18",
        "name": "Landesrecht BW",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["landesrecht-bw.de"],
        "source_urls": ["https://www.landesrecht-bw.de/bsbw/search"],
        "deep_urls": [
            "https://www.landesrecht-bw.de/jportal/docs/anlage_landesrecht.pdf"
        ],
    },
    {
        "id": "19",
        "name": "BAG Entscheidungsdatenbank",
        "jurisdiction": "BUND",
        "allowed_domains": ["bundesarbeitsgericht.de"],
        "source_urls": ["https://www.bundesarbeitsgericht.de/entscheidungen/"],
        "deep_urls": ["https://www.bundesarbeitsgericht.de/rss/entscheidungen.xml"],
    },
    {
        "id": "20",
        "name": "Arbeitsrechte.de Ratgeber",
        "jurisdiction": "BUND",
        "allowed_domains": ["arbeitsrechte.de"],
        "source_urls": ["https://www.arbeitsrechte.de/ratgeber/"],
        "deep_urls": [
            "https://www.arbeitsrechte.de/downloads/arbeitsrecht_merkblatt.pdf"
        ],
    },
    {
        "id": "21",
        "name": "DGB Ratgeber Arbeitsrecht",
        "jurisdiction": "BUND",
        "allowed_domains": ["dgb.de"],
        "source_urls": ["https://www.dgb.de/service/ratgeber/arbeitsrecht/"],
        "deep_urls": [
            "https://www.dgb.de/fileadmin/user_upload/DGB_Ratgeber_Arbeitsrecht_Broschuere.pdf"
        ],
    },
    {
        "id": "22",
        "name": "DRV - Erwerbsminderungsrente",
        "jurisdiction": "BUND",
        "allowed_domains": ["deutsche-rentenversicherung.de"],
        "source_urls": [
            "https://www.deutsche-rentenversicherung.de/DRV/DE/Rente/Allgemeine-Informationen/Rentenarten-und-Leistungen/Erwerbsminderungsrente"
        ],
        "deep_urls": [
            "https://www.deutsche-rentenversicherung.de/SharedDocs/Downloads/DE/Broschueren/national/erwerbsminderungsrente_das_netz_fuer_alle_faelle.pdf"
        ],
    },
    {
        "id": "23",
        "name": "BMAS - Soziales Entschädigungsrecht",
        "jurisdiction": "BUND",
        "allowed_domains": ["bmas.de"],
        "source_urls": [
            "https://www.bmas.de/DE/Soziales/Soziale-Entschaedigung/Neues-Soziales-Entschaedigungsrecht/neues-soziales-entschaedigungsrecht.html"
        ],
        "deep_urls": [
            "https://www.bmas.de/SharedDocs/Downloads/DE/Broschueren/a712-soziales-entschaedigungsrecht.pdf"
        ],
    },
    {
        "id": "24",
        "name": "Service-BW - Antrag Entschädigung",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/leistung/-/sbw/Soziale-Entschaedigung-beantragen-1549-leistung-0"
        ],
        "deep_urls": [
            "https://www.service-bw.de/zufi/formulare/OEG_Antrag.pdf"
        ],
    },
    {
        "id": "25",
        "name": "UPD - Unabhängige Patientenberatung",
        "jurisdiction": "BUND",
        "allowed_domains": ["patientenberatung.de"],
        "source_urls": ["https://www.patientenberatung.de/"],
        "deep_urls": [
            "https://www.patientenberatung.de/fileadmin/user_upload/UPD_Jahresbericht.pdf"
        ],
    },
    {
        "id": "26",
        "name": "BMJ - Patientenverfügung",
        "jurisdiction": "BUND",
        "allowed_domains": ["bmj.de"],
        "source_urls": [
            "https://www.bmj.de/DE/service/formulare/form_patientenverfuegung/form_patientenverfuegung_node.html"
        ],
        "deep_urls": [
            "https://www.bmj.de/SharedDocs/Downloads/DE/Service/Formulare/Patientenverfuegung_Textbausteine_pdf.pdf"
        ],
    },
  {
        "id": "27",
        "name": "BMJ - Vorsorgevollmacht",
        "jurisdiction": "BUND",
        "allowed_domains": ["bmj.de", "www.bmj.de", "bmjv.de", "www.bmjv.de"],
        "source_urls": [
            "https://www.bmj.de/DE/service/formulare/form_vorsorgevollmacht/form_vorsorgevollmacht_artikel.html"
        ],
        "deep_urls": [
            "https://www.bmj.de/SharedDocs/Downloads/DE/Service/Formulare/Vorsorgevollmacht_Formular.pdf"
        ],
    },
    {
        "id": "28",
        "name": "Zentrales Vorsorgeregister (ZVR)",
        "jurisdiction": "BUND",
        "allowed_domains": ["vorsorgeregister.de"],
        "source_urls": ["https://www.vorsorgeregister.de/"],
        "deep_urls": [
            "https://www.vorsorgeregister.de/fileadmin/user_upload/ZVR_Gebuehrenordnung.pdf"
        ],
    },
    {
        "id": "29",
        "name": "BA - Arbeitslosengeld (SGB III)",
        "jurisdiction": "BUND",
        "allowed_domains": ["arbeitsagentur.de"],
        "source_urls": ["https://www.arbeitsagentur.de/arbeitslos-arbeit-finden/arbeitslosengeld"],
        "deep_urls": [
            "https://www.arbeitsagentur.de/datei/merkblatt-fuer-arbeitslose_ba015368.pdf"
        ],
    },
    {
        "id": "30",
        "name": "BA - Grundsicherungsgeld (SGB II)",
        "jurisdiction": "BUND",
        "allowed_domains": ["arbeitsagentur.de"],
        "source_urls": [
            "https://www.arbeitsagentur.de/grundsicherung/grundsicherungsgeld-beantragen"
        ],
        "deep_urls": [
            "https://www.arbeitsagentur.de/datei/merkblatt-buergergeld_ba015397.pdf"
        ],
    },
    {
        "id": "31",
        "name": "Bürgergeld.org - Richtwerte & Rechner",
        "jurisdiction": "BUND",
        "allowed_domains": ["buergergeld.org"],
        "source_urls": [
            "https://www.buergergeld.org/rechner/",
            "https://www.buergergeld.org/einkommen/",
            "https://www.buergergeld.org/kosten-der-unterkunft/",
            "https://www.buergergeld.org/regelbedarf/"
        ],
        "deep_urls": [
            "https://www.buergergeld.org/"
        ]
    },
]


# ==========================================
# 6. MAIN ORCHESTRATOR MIT TRIAGE
# ==========================================
async def main():
  print(
      f"⚓ HAUPT-RADAR (V44.0 PROVENIENZ) GESTARTET ({datetime.date.today()})"
  )
  try:
    validate_arsenal(TARGETS_ARSENAL)
  except Exception as e:
    print(e)
    return

  state = load_state()
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    results = []
    for slot in TARGETS_ARSENAL:
      results.append(await process_slot(slot, state, browser))
      await asyncio.sleep(1.0)
    await browser.close()
  save_state_atomic(state)

  timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
  log_file = os.path.join(LOG_DIR, f"API_Master_V44_{timestamp}.txt")

  changed_results = [
      r
      for r in results
      if r["status"]
      in [
          VerificationStatus.LEGAL_AND_EVIDENCE_CHANGED,
          VerificationStatus.LEGAL_CHANGED_PARTIALLY_VALIDATED,
          VerificationStatus.LEGAL_CHANGED_VALIDATION_FAILED,
      ]
  ]
  unchanged_results = [r for r in results if r not in changed_results]

  report = [
      "============================================================\n⚓ M.E.R."
      f" LAGEBERICHT V44.0 ({datetime.date.today()})\n============================================================\n"
  ]

  report.append(
      "\n[🔴 AKUTER HANDLUNGSBEDARF / ÄNDERUNGEN ERKANNT]\n" + "=" * 50
  )
  if not changed_results:
    report.append("Keine kritischen Veränderungen im Sektor.")
  for r in changed_results:
    report.append(f"\n=== {r['id']}: {r['name']} ===")
    report.append(f"Status: {r['status'].value}")
    if "canonical" in r:
      report.append(f"Quelle: {r['canonical']}")
    report.append(f"Diff-Log:\n{r['diff']}\n")

  report.append("\n[🟢 SICHERER PERIMETER / UNVERÄNDERT]\n" + "=" * 50)
  for r in unchanged_results:
    report.append(
        f"\n=== {r['id']}: {r['name']} ===\nStatus:"
        f" {r['status'].value}\nDiff-Log:\n{r['diff']}\n"
    )

  with open(log_file, "w", encoding="utf-8") as f:
    f.write("\n".join(report))
  print(f"\n[MASTERLOG] Gespeichert: {log_file}")


if __name__ == "__main__":
  asyncio.run(main())
