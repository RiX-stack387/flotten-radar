"""⚓ DEFCON RECHT RADAR - ZUSATZ-RADAR "LEBENS-PRAXIS" (V44.0 OPERATION PROVENIENZ)

Architektur: Playwright + CMP-Blocker + Secure-PDF + Config-Gate +
Strict-Evidence + Triage + Vault
Gebiet: STADTKREIS PFORZHEIM & LANDKREIS ENZKREIS (100% Geofenced)
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
EXPECTED_ZUSATZ_SLOT_COUNT = 126
BASE_DIR = r"C:\DefconRecht"
STATE_FILE = os.path.join(BASE_DIR, "radar_state_zusatz_v44.json")
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
    raise ValueError(
        f"CONFIG ERROR: {EXPECTED_ZUSATZ_SLOT_COUNT} Slots erwartet,"
        f" {len(arsenal)} geladen."
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
      ..., description="Rechtsnorm, Aktenzeichen, Tarif oder Satzung"
  )
  extracted_value: str = Field(
      ...,
      description=(
          "Vollständige Kernaussage, der Leitsatz, das Urteil oder konkreter"
          " Betrag"
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
# 3. SECURITY-GATES & FETCHING
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
  context = await browser.new_context(ignore_https_errors=False)
  if url.lower().endswith(".pdf") or "blob=" in url.lower():
    res = await secure_fetch_pdf(url, allowed_domains, context)
    try:
        await context.close()
    except Exception:
        pass
    return res

  await context.route(
      "**/*",
      lambda route, req: SecurityGate.intercept_route(
          route, req, allowed_domains
      ),
  )
  page = await context.new_page()
  try:
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    except Exception as e:
        print(f"   Ã¢â€â€Ã¢â€â‚¬ [WARNUNG] Laden der URL {url} fehlgeschlagen oder Timeout: {e}")
        return None
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
    try:
        await context.close()
    except Exception:
        pass


# ==========================================
# 4. ORCHESTRATOR & DIFF-ENGINE
# ==========================================
async def process_slot(slot: dict, state: dict, browser: Browser) -> dict:
  print(f"Zusatz-Radar V44.0: [{slot['id']}] -> {slot['name']}")
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

  slot_key = f"praxis_slot_{slot['id']}"
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
      " Extrahiere Tarife, Gebühren, Fristen, Fakten UND VOLLSTÄNDIGE"
      " URTEILS-LEITSÄTZE SOWIE AKTENZEICHEN. ACHTE BESONDERS AUF DIE ANPASSUNG"
      " AN DAS 'Grundsicherungsgeld' (ehem. Bürgergeld) SOWIE KOMMUNALE"
      " KdU-RICHTWERTE. Die 'evidence_location' muss ein exakter Satz/Absatz aus"
      " der Quelle sein, der dies zweifelsfrei belegt."
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
    diff_summary += f"\n[Ã°Å¸â€â€™ BEWEIS GESICHERT]: {vault_file}"

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
# 5. ZUSATZ-ARSENAL (120 SEKTOR-ZIELE)
# ==========================================
ZUSATZ_ARSENAL = [
    {
        "id": "Z1",
        "name": "Mietspiegel Pforzheim",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/bauen-wohnen/mietspiegel.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/bauen-wohnen/mietspiegel/Mietspiegel_Broschuere.pdf"
        ],
    },
    {
        "id": "Z2",
        "name": "SWP Strom Grundversorgung",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["stadtwerke-pforzheim.de"],
        "source_urls": [
            "https://www.stadtwerke-pforzheim.de/strom/grund-und-ersatzversorgung/"
        ],
        "deep_urls": [
            "https://www.stadtwerke-pforzheim.de/strom/grund-und-ersatzversorgung/"
        ],
    },
    {
        "id": "Z3",
        "name": "Bildung & Teilhabe Pforzheim",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["jobcenter.pforzheim.de", "pforzheim.de", "www.pforzheim.de"],
        "source_urls": [
            "https://jobcenter.pforzheim.de/"
        ],
        "deep_urls": [
            "https://jobcenter.pforzheim.de/fileadmin/user_upload/Formulare/Antrag_auf_Leistungen_fuer_Bildung_und_Teilhabe.pdf"
        ],
    },
    {
        "id": "Z4",
        "name": "VPE Ticket-Tarife",
        "jurisdiction": "REGION_NTS",
        "allowed_domains": ["vpe.de", "www.vpe.de"],
        "source_urls": ["https://vpe.de/fahrschein-jugendbw"],
        "deep_urls": [
            "https://www.vpe.de/fileadmin/user_upload/Tarife/VPE_Tarifzonenplan_Preistabelle.pdf"
        ],
    },
    {
        "id": "Z5",
        "name": "Pforzheimer Tafel (GBE Pforzheim)",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["gbe-pforzheim.de"],
        "source_urls": [
            "https://gbe-pforzheim.de/gbe-einrichtungen/pforzheimer-tafel.html"
        ],
        "deep_urls": [
            "https://gbe-pforzheim.de/fileadmin/user_upload/Downloads/Einkaufsberechtigung_Tafel.pdf"
        ],
    },
    {
        "id": "Z6",
        "name": "Auszahlungstermine Kindergeld",
        "jurisdiction": "BUND",
        "allowed_domains": ["arbeitsagentur.de"],
        "source_urls": [
            "https://www.arbeitsagentur.de/familie-und-kinder/auszahlungstermine"
        ],
        "deep_urls": [
            "https://www.arbeitsagentur.de/datei/auszahlungstermine-kindergeld_ba041696.pdf"
        ],
    },
    {
        "id": "Z7",
        "name": "Finanzielle Hilfen",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/rat-hilfe/finanzielle-hilfen.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/buerger/rat-hilfe/finanzielle-hilfen/uebersicht-hilfen.html"
        ],
    },
    {
        "id": "Z8",
        "name": "Verbraucherzentrale Pforzheim",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["verbraucherzentrale-bw.de"],
        "source_urls": [
            "https://www.verbraucherzentrale-bw.de/beratungsstellen/pforzheim"
        ],
        "deep_urls": [
            "https://www.verbraucherzentrale-bw.de/sites/default/files/2023-10/Preisverzeichnis_VZBW.pdf"
        ],
    },
    {
        "id": "Z9",
        "name": "BuT Enzkreis (Jobcenter)",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["enzkreis.de"],
        "source_urls": [
            "https://www.enzkreis.de/Unsere-Leistungen/Dienstleistungen/Bildungs-und-Teilhabepaket.php?ModID=10&FID=2032.111.1"
        ],
        "deep_urls": ["https://www.enzkreis.de/media/custom/3397_1234_1.PDF"],
    },
    {
        "id": "Z10",
        "name": "Wohngeldbehörde Enzkreis",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["enzkreis.de"],
        "source_urls": ["https://www.enzkreis.de/?object=tx,3397.11173.1"],
        "deep_urls": [
            "https://www.enzkreis.de/media/custom/3397_Wohngeldantrag_Mietzuschuss.PDF"
        ],
    },
    {
        "id": "Z11",
        "name": "Müllgebühren Enzkreis",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["enzkreis.de", "abfallwirtschaft-enzkreis.de"],
        "source_urls": [
            "https://www.enzkreis.de/Unsere-Leistungen/Dienstleistungen/Abfallgeb%C3%BChren.php?ModID=10&FID=2032.7.1",
            "https://www.abfallwirtschaft-enzkreis.de/gebuehren/",
        ],
        "deep_urls": [
            "https://www.abfallwirtschaft-enzkreis.de/fileadmin/user_upload/Abfallwirtschaft/Gebuehren/Abfallgebuehrensatzung.pdf"
        ],
    },
    {
        "id": "Z12",
        "name": "Schuldnerberatung Enzkreis",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["enzkreis.de"],
        "source_urls": [
            "https://www.enzkreis.de/Landratsamt/%C3%84mter-Dezernate/Dezernat-4-Familie-und-Soziales/Jobcenter-Enzkreis/index.php?object=tx%7C3397.2.1&ModID=10&FID=2032.334.1"
        ],
        "deep_urls": [
            "https://www.enzkreis.de/media/custom/3397_Faltblatt_Schuldnerberatung.PDF"
        ],
    },
    {
        "id": "Z13",
        "name": "Tafelladen Enzkreis",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["diakonie-enzkreis.de"],
        "source_urls": [
            "https://www.diakonie-enzkreis.de/guenstig-einkaufen/tafelladen"
        ],
        "deep_urls": [
            "https://www.diakonie-enzkreis.de/fileadmin/user_upload/Flyer_Tafelladen.pdf"
        ],
    },
    {
        "id": "Z14",
        "name": "Schuldnerberatung",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/rat-hilfe/finanzielle-hilfen/schuldnerberatung.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/rat-hilfe/Schuldnerberatung_Flyer.pdf"
        ],
    },
    {
        "id": "Z15",
        "name": "Finanzielle Hilfen für Eltern",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/rat-hilfe/finanzielle-hilfen/finanzielle-hilfen-fuer-eltern.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/buerger/rat-hilfe/finanzielle-hilfen/uebersicht-eltern-leistungen.html"
        ],
    },
    {
        "id": "Z16",
        "name": "Finanzielle Hilfen bei einer Behinderung",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/rat-hilfe/finanzielle-hilfen/finanzielle-hilfen-bei-einer-behinderung.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/rat-hilfe/Eingliederungshilfe_Antrag.pdf"
        ],
    },
    {
        "id": "Z17",
        "name": "Finanzielle Hilfen für Senioren",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/rat-hilfe/finanzielle-hilfen/finanzielle-hilfen-fuer-senioren.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/senioren/Seniorenratgeber.pdf"
        ],
    },
    {
        "id": "Z18",
        "name": "Finanzielle Hilfen für die Jugendarbeit",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/rat-hilfe/finanzielle-hilfen/finanzielle-hilfen-fuer-die-jugendarbeit.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/jugend/Foerderrichtlinien_Jugendarbeit.pdf"
        ],
    },
    {
        "id": "Z19",
        "name": "Goldstadt-Pass (Voraussetzungen & Antrag)",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/buergerservice/info/service-bw/leistungen/show/6005679-goldstadt-pass.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/buergerservice/Antrag_Goldstadtpass.pdf"
        ],
    },
    {
        "id": "Z20",
        "name": "Förderverein Pforzheimer Tafel e.V.",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["foerderverein-pforzheimertafel.eu"],
        "source_urls": ["http://www.foerderverein-pforzheimertafel.eu/"],
        "deep_urls": [
            "http://www.foerderverein-pforzheimertafel.eu/mitgliedsantrag.pdf"
        ],
    },
    {
        "id": "Z21",
        "name": "Mieterverein Pforzheim und Enzkreis e.V.",
        "jurisdiction": "REGION_NTS",
        "allowed_domains": ["service-bw.de"],
        "source_urls": ["https://www.service-bw.de/zufi/leistungen/4495"],
        "deep_urls": [
            "https://www.mieterverein-pforzheim.de/fileadmin/user_upload/Beitragsordnung.pdf"
        ],
    },
    {
        "id": "Z22",
        "name": "Finanzielle Hilfe für obdachlose Menschen",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/rat-hilfe/finanzielle-hilfen/finanzielle-hilfe-fuer-obdachlose-menschen.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/rat-hilfe/Notunterkuenfte_Uebersicht.pdf"
        ],
    },
    {
        "id": "Z23",
        "name": "Wohngeldbehörde Pforzheim (Anträge & Vordrucke)",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["form-solutions.net", "landbw.de", "komm.one"],
        "source_urls": [
            "https://pdf.form-solutions.net/forms/frm/4dakhDtg1P7pF3HkmGQ4CCCjv98qkk3C",
            "https://sbwmedia.landbw.de/documents/wm/wohngeld/Mietzuschuss%20nach%20dem%20Wohngeldgesetz%20BUND.pdf",
        ],
        "deep_urls": [
            "https://pdf.form-solutions.net/forms/frm/4dakhDtg1P7pF3HkmGQ4CCCjv98qkk3C",
            "https://sbwmedia.landbw.de/documents/wm/wohngeld/Lastenzuschuss%20nach%20dem%20Wohngeldgesetz%20BUND.pdf",
        ],
    },
    {
        "id": "Z24",
        "name": "Wohnberechtigungsschein (WBS)",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/buergerservice/pf0/service-bw/organisationseinheiten/show/6021731-354-wohnungswesen-wohnungssicherung-sachgebiet.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/buergerservice/Antrag_WBS.pdf"
        ],
    },
    {
        "id": "Z25",
        "name": "Abfallgebühren Pforzheim",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["abfallwirtschaft-pforzheim.de"],
        "source_urls": [
            "https://www.abfallwirtschaft-pforzheim.de/abfallwirtschaft/muellgebuehren"
        ],
        "deep_urls": [
            "https://www.abfallwirtschaft-pforzheim.de/fileadmin/user_upload/abfallwirtschaft/Gebuehrentabelle_PF.pdf"
        ],
    },
    {
        "id": "Z26",
        "name": "Wirtschaftliche Jugendhilfe (Kita)",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/buergerservice/info/service-bw/leistungen/show/82-kindertageseinrichtungen-gebuehrenermaessigung-oder-gebuehrenbefreiung-beantragen.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/jugend/Kita_Gebuehrenordnung.pdf"
        ],
    },
    {
        "id": "Z27",
        "name": "Pflegestützpunkt Pforzheim",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/gesellschaft-soziales/senioren/pflegestuetzpunkt.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/senioren/Pflegestuetzpunkt_Flyer.pdf"
        ],
    },
    {
        "id": "Z28",
        "name": "Unterhaltsvorschuss Pforzheim",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["pforzheim.de"],
        "source_urls": [
            "https://www.pforzheim.de/buerger/buergerservice/info/service-bw/leistungen/show/170-unterhaltsvorschuss-beantragen.html"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/jugend/Antrag_Unterhaltsvorschuss.pdf"
        ],
    },
    {
        "id": "Z29",
        "name": "LL: Arbeitnehmer",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001353"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/900"],
    },
    {
        "id": "Z30",
        "name": "LL: Arbeitslos, Grundsicherungsgeld",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001012"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/14"],
    },
    {
        "id": "Z31",
        "name": "LL: Berufsausbildung",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000950"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/200"],
    },
    {
        "id": "Z32",
        "name": "LL: Schule",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000243"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/300"],
    },
    {
        "id": "Z33",
        "name": "LL: Studium",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001119"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/400"],
    },
    {
        "id": "Z34",
        "name": "LL: Weiterbildung",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000199"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/500"],
    },
    {
        "id": "Z35",
        "name": "LL: Führerschein",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000396"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/352"],
    },
    {
        "id": "Z36",
        "name": "LL: Personalausweis, Reisepass",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001046"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/141"],
    },
    {
        "id": "Z37",
        "name": "LL: Tierhaltung, Tierschutz, Fischerei und Jagd",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001339"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/832"],
    },
    {
        "id": "Z38",
        "name": "LL: Bauen und Modernisieren",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000427"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/102"],
    },
    {
        "id": "Z39",
        "name": "LL: Grundstück",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000612"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/104"],
    },
    {
        "id": "Z40",
        "name": "LL: Umzug",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000726"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/120"],
    },
    {
        "id": "Z41",
        "name": "LL: Wohnen",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000525"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/130"],
    },
    {
        "id": "Z42",
        "name": "LL: Bürgerschaftliches Engagement",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000892"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/150"],
    },
    {
        "id": "Z43",
        "name": "LL: Freiwilligendienste",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000069"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/160"],
    },
    {
        "id": "Z44",
        "name": "LL: Wahlen und Bürgerbeteiligung",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000463"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/170"],
    },
    {
        "id": "Z45",
        "name": "LL: Adoption",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000531"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/180"],
    },
    {
        "id": "Z46",
        "name": "LL: Der Bund fürs Leben",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000928"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/190"],
    },
    {
        "id": "Z47",
        "name": "LL: Der Bund fürs Leben - Auflösung",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001057"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/200"],
    },
    {
        "id": "Z48",
        "name": "LL: Familie und Kinder",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000312"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/210"],
    },
    {
        "id": "Z49",
        "name": "LL: Kinderbetreuung",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001280"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/82"],
    },
    {
        "id": "Z50",
        "name": "LL: Pflegeeltern",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000919"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/230"],
    },
    {
        "id": "Z51",
        "name": "LL: Geburt",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000783"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/240"],
    },
    {
        "id": "Z52",
        "name": "LL: Sterbefall",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000053"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/250"],
    },
    {
        "id": "Z53",
        "name": "LL: Behinderung",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001206"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/260"],
    },
    {
        "id": "Z54",
        "name": "LL: Gesetzliche Unfallversicherung, Kinder und Schüler",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000388"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/270"],
    },
    {
        "id": "Z55",
        "name": "LL: Gesundheit",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000349"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/280"],
    },
    {
        "id": "Z56",
        "name": "LL: Gläubiger und Schuldner",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000945"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/290"],
    },
    {
        "id": "Z57",
        "name": "LL: Notlagen",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000779"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/300"],
    },
    {
        "id": "Z58",
        "name": "LL: Opferschutz und Opferhilfe",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000887"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/310"],
    },
    {
        "id": "Z59",
        "name": "LL: Stiftungen",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000722"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/320"],
    },
    {
        "id": "Z60",
        "name": "LL: Verbraucherschutz und Ernährung",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001207"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/330"],
    },
    {
        "id": "Z61",
        "name": "LL: Altersvorsorge und Ruhestand",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000667"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/340"],
    },
    {
        "id": "Z62",
        "name": "LL: Erben und Vererben",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000666"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/350"],
    },
    {
        "id": "Z63",
        "name": "LL: Vormundschaft und rechtliche Betreuung",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001456"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/360"],
    },
    {
        "id": "Z64",
        "name": "LL: Fahrzeuge",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001410"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/355"],
    },
    {
        "id": "Z65",
        "name": "LL: Reisen",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001054"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/380"],
    },
    {
        "id": "Z66",
        "name": "LL: Vereine",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000500"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/390"],
    },
    {
        "id": "Z67",
        "name": "LL: Verkehr und Verkehrswege",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000952"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/400"],
    },
    {
        "id": "Z68",
        "name": "LL: Sicherheit und Gefahrenabwehr",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000006"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/410"],
    },
    {
        "id": "Z69",
        "name": "LL: Umwelt",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000229"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/420"],
    },
    {
        "id": "Z70",
        "name": "LL: Umwelt- und Naturgefahren",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000833"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/430"],
    },
    {
        "id": "Z71",
        "name": "LL: Arbeitgeber",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000437"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/440"],
    },
    {
        "id": "Z72",
        "name": "LL: Freiberufler",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001440"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/450"],
    },
    {
        "id": "Z73",
        "name": "LL: Gewerbe",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000218"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/460"],
    },
    {
        "id": "Z74",
        "name": "LL: Patente, Marken, Ideentransfer",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001195"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/470"],
    },
    {
        "id": "Z75",
        "name": "LL: Unternehmen führen",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001018"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/480"],
    },
    {
        "id": "Z76",
        "name": "LL: Unternehmen gründen",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000792"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/490"],
    },
    {
        "id": "Z77",
        "name": "LL: Unternehmensnachfolge",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000810"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/500"],
    },
    {
        "id": "Z78",
        "name": "LL: Vergabe öffentlicher Aufträge",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000476"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/510"],
    },
    {
        "id": "Z79",
        "name": "LL: Deutsche Staatsangehörigkeit",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000729"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/520"],
    },
    {
        "id": "Z80",
        "name": "LL: Spätaussiedler",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000884"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/530"],
    },
    {
        "id": "Z81",
        "name": "LL: Zuwanderung",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000993"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/540"],
    },
    {
        "id": "Z82",
        "name": (
            "LL: Tierhaltung, Tierschutz, Fischerei und Jagd"
            " (Duplikat-Sicherung)"
        ),
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001339"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/832"],
    },
    {
        "id": "Z83",
        "name": "LL: Notlagen (Sicherheits-Check)",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000779"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/300"],
    },
    {
        "id": "Z84",
        "name": "LL: Gläubiger und Schuldner (Sicherheits-Check)",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000945"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/290"],
    },
    {
        "id": "Z85",
        "name": "LL: Wohnen (Sicherheits-Check)",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5000525"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/130"],
    },
    {
        "id": "Z86",
        "name": "LL: Arbeitnehmer (Sicherheits-Check)",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/lebenslagen/5001353"
        ],
        "deep_urls": ["https://www.service-bw.de/zufi/leistungen/900"],
    },
    {
        "id": "Z87",
        "name": "Rente: Regelaltersrente beantragen",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["service-bw.de"],
        "source_urls": ["https://www.service-bw.de/zufi/leistungen/1519"],
        "deep_urls": [
            "https://www.service-bw.de/zufi/formulare/Rentenantrag_R0100.pdf"
        ],
    },
    {
        "id": "Z88",
        "name": "Rente: Altersrente für schwerbehinderte Menschen",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["service-bw.de"],
        "source_urls": ["https://www.service-bw.de/zufi/leistungen/1251"],
        "deep_urls": [
            "https://www.service-bw.de/zufi/formulare/Rentenantrag_Schwerbehinderung_R0100.pdf"
        ],
    },
    {
        "id": "Z89",
        "name": "Rente: Erwerbsminderungsrente beantragen",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["service-bw.de"],
        "source_urls": ["https://www.service-bw.de/zufi/leistungen/1240"],
        "deep_urls": [
            "https://www.service-bw.de/zufi/formulare/Rentenantrag_Erwerbsminderung_R0210.pdf"
        ],
    },
    {
        "id": "Z90",
        "name": "Rente: Rentenauskunft und Kontenklärung",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["service-bw.de"],
        "source_urls": ["https://www.service-bw.de/zufi/leistungen/85"],
        "deep_urls": [
            "https://www.service-bw.de/zufi/formulare/Kontenklaerung_V0100.pdf"
        ],
    },
    {
        "id": "Z91",
        "name": "Rentenstelle Stadt Pforzheim",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/organisationseinheiten/6021568"
        ],
        "deep_urls": [
            "https://www.pforzheim.de/fileadmin/user_upload/stadtpforzheim/buergerservice/Rentenstelle_Merkblatt.pdf"
        ],
    },
    {
        "id": "Z92",
        "name": "Deutsche Rentenversicherung Außenstelle Pforzheim",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["service-bw.de"],
        "source_urls": [
            "https://www.service-bw.de/zufi/organisationseinheiten/6008274"
        ],
        "deep_urls": [
            "https://www.deutsche-rentenversicherung.de/SharedDocs/Downloads/DE/Broschueren/regional/bw/beratungsstellen.pdf"
        ],
    },
    # ==========================================
    # DIE 5 STÄDTE IM ENZKREIS
    # ==========================================
    {
        "id": "ENZ_ST_01",
        "name": "Stadt Heimsheim",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["heimsheim.de"],
        "source_urls": ["https://www.heimsheim.de"],
    },
    {
        "id": "ENZ_ST_02",
        "name": "Stadt Knittlingen",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["knittlingen.de"],
        "source_urls": ["https://www.knittlingen.de"],
    },
    {
        "id": "ENZ_ST_03",
        "name": "Stadt Maulbronn",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["maulbronn.de"],
        "source_urls": ["https://www.maulbronn.de"],
    },
    {
        "id": "ENZ_ST_04",
        "name": "Stadt Mühlacker",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["muehlacker.de"],
        "source_urls": ["https://www.muehlacker.de"],
    },
    {
        "id": "ENZ_ST_05",
        "name": "Stadt Neuenbürg",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["neuenbuerg.de"],
        "source_urls": ["https://www.neuenbuerg.de"],
    },
    # ==========================================
    # DIE 23 GEMEINDEN IM ENZKREIS
    # ==========================================
    {
        "id": "ENZ_GM_01",
        "name": "Gemeinde Birkenfeld",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["birkenfeld-enzkreis.de"],
        "source_urls": ["https://www.birkenfeld-enzkreis.de"],
    },
    {
        "id": "ENZ_GM_02",
        "name": "Gemeinde Eisingen",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["eisingen-enzkreis.de"],
        "source_urls": ["https://www.eisingen-enzkreis.de"],
    },
    {
        "id": "ENZ_GM_03",
        "name": "Gemeinde Engelsbrand",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["engelsbrand.de"],
        "source_urls": ["https://www.engelsbrand.de"],
    },
    {
        "id": "ENZ_GM_04",
        "name": "Gemeinde Friolzheim",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["friolzheim.de"],
        "source_urls": ["https://www.friolzheim.de"],
    },
    {
        "id": "ENZ_GM_05",
        "name": "Gemeinde Illingen",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["illingen-online.de"],
        "source_urls": ["https://www.illingen-online.de"],
    },
    {
        "id": "ENZ_GM_06",
        "name": "Gemeinde Ispringen",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["ispringen.de"],
        "source_urls": ["https://www.ispringen.de"],
    },
    {
        "id": "ENZ_GM_07",
        "name": "Gemeinde Kämpfelbach",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["kaempfelbach.de"],
        "source_urls": ["https://www.kaempfelbach.de"],
    },
    {
        "id": "ENZ_GM_08",
        "name": "Gemeinde Keltern",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["keltern.de"],
        "source_urls": ["https://www.keltern.de"],
    },
    {
        "id": "ENZ_GM_09",
        "name": "Gemeinde Kieselbronn",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["kieselbronn.de"],
        "source_urls": ["https://www.kieselbronn.de"],
    },
    {
        "id": "ENZ_GM_10",
        "name": "Gemeinde Königsbach-Stein",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["koenigsbach-stein.de"],
        "source_urls": ["https://www.koenigsbach-stein.de"],
    },
    {
        "id": "ENZ_GM_11",
        "name": "Gemeinde Mönsheim",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["moensheim.de"],
        "source_urls": ["https://www.moensheim.de"],
    },
    {
        "id": "ENZ_GM_12",
        "name": "Gemeinde Neuhausen",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["neuhausen-enzkreis.de"],
        "source_urls": ["https://www.neuhausen-enzkreis.de"],
    },
    {
        "id": "ENZ_GM_13",
        "name": "Gemeinde Neulingen",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["neulingen.de"],
        "source_urls": ["https://www.neulingen.de"],
    },
    {
        "id": "ENZ_GM_14",
        "name": "Gemeinde Niefern-Öschelbronn",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["niefern-oeschelbronn.de"],
        "source_urls": ["https://www.niefern-oeschelbronn.de"],
    },
    {
        "id": "ENZ_GM_15",
        "name": "Gemeinde Ölbronn-Dürrn",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["oelbronn-duerrn.de"],
        "source_urls": ["https://www.oelbronn-duerrn.de"],
    },
    {
        "id": "ENZ_GM_16",
        "name": "Gemeinde Ötisheim",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["oetisheim.de"],
        "source_urls": ["https://www.oetisheim.de"],
    },
    {
        "id": "ENZ_GM_17",
        "name": "Gemeinde Remchingen",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["remchingen.de"],
        "source_urls": ["https://www.remchingen.de"],
    },
    {
        "id": "ENZ_GM_18",
        "name": "Gemeinde Sternenfels",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["sternenfels.de"],
        "source_urls": ["https://www.sternenfels.de"],
    },
    {
        "id": "ENZ_GM_19",
        "name": "Gemeinde Straubenhardt",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["straubenhardt.de"],
        "source_urls": ["https://www.straubenhardt.de"],
    },
    {
        "id": "ENZ_GM_20",
        "name": "Gemeinde Tiefenbronn",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["tiefenbronn.de"],
        "source_urls": ["https://www.tiefenbronn.de"],
    },
    {
        "id": "ENZ_GM_21",
        "name": "Gemeinde Wiernsheim",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["wiernsheim.de"],
        "source_urls": ["https://www.wiernsheim.de"],
    },
    {
        "id": "ENZ_GM_22",
        "name": "Gemeinde Wimsheim",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["wimsheim.de"],
        "source_urls": ["https://www.wimsheim.de"],
    },
    {
        "id": "ENZ_GM_23",
        "name": "Gemeinde Wurmberg",
        "jurisdiction": "LANDKREIS_ENZKREIS",
        "allowed_domains": ["wurmberg.de"],
        "source_urls": ["https://www.wurmberg.de"],
    },
 # === KRITIS- & FRÜHWARN-SENSOREN: PF / ENZ / LANDESEBENE BW ===
    {
        "id": "PF_ENZ_K1_STROM",
        "name": "Netze BW & SWP Störungsmelder (Strom/Gas)",
        "jurisdiction": "REGION_PF_ENZ",
        "allowed_domains": ["netze-bw.de", "www.netze-bw.de"],
        "source_urls": ["https://www.netze-bw.de/stoerung"],
        "wait_selector": "main, #main-content, body",
        "content_selector": "main, .disruption-list, .stoerung-content, body",
        "category": "kritis_energie"
    },
    {
        "id": "PF_ENZ_K2_APO",
        "name": "Apotheken-Notdienst Pforzheim & Enzkreis (LAK BW)",
        "jurisdiction": "REGION_PF_ENZ",
        "allowed_domains": ["lak-bw.de", "www.lak-bw.de", "lak-bw.notdienst-portal.de"],
        "source_urls": ["https://www.lak-bw.de/buergerservice/apothekennotdienst/schnellsuche"],
        "wait_selector": "#content, .emergency-search, body",
        "content_selector": "#content, .tx-emergency-service, .results-container, body",
        "category": "daseinsvorsorge_apotheke"
    },
    {
        "id": "BW_KRITIS_K3_CYBER",
        "name": "BSI & Cyberwehr BW (IT-Sicherheitslage & KRITIS-Ausfälle)",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["bsi.bund.de", "www.bsi.bund.de"],
        "source_urls": ["https://www.bsi.bund.de/DE/Service-Navi/Presse/Pressemitteilungen/pressemitteilungen_node.html"],
        "wait_selector": "main, .c-teaser-list, body",
        "content_selector": "main, .c-teaser-list, .c-press-releases, body",
        "category": "kritis_cyber"
    },
    {
        "id": "BW_KRITIS_K4_LEBENSMITTEL",
        "name": "BVL Lebensmittelwarnungen & Produktrückrufe (BW)",
        "jurisdiction": "LAND_BW",
        "allowed_domains": ["lebensmittelwarnung.de", "www.lebensmittelwarnung.de"],
        "source_urls": ["https://www.lebensmittelwarnung.de/bvl-lmw-de/liste/lebensmittel/baden-wuerttemberg"],
        "wait_selector": ".table, .teaser-list, body",
        "content_selector": ".table, .teaser-list, #maincontent, body",
        "category": "daseinsvorsorge_lebensmittel"
    },
    {
        "id": "PF_K5_WOHNBAU",
        "name": "Bau und Heim eG Pforzheim (Sozialer Wohnraum & Bauprojekte)",
        "jurisdiction": "STADTKREIS_PFORZHEIM",
        "allowed_domains": ["bauundheim.de", "www.bauundheim.de"],
        "source_urls": ["https://www.bauundheim.de/"],
        "wait_selector": "main, #content, body",
        "content_selector": "main, #content, .news-list, body",
        "category": "wohnen_sozialraum"
    },
    {
        "id": "PF_ENZ_K6_DWD",
        "name": "DWD Amtliche Warnungen (Stadtkreis Pforzheim & Enzkreis)",
        "jurisdiction": "REGION_PF_ENZ",
        "allowed_domains": ["dwd.de", "www.dwd.de", "warnungen.dwd.de"],
        "source_urls": ["https://www.dwd.de/DE/wetter/warnungen_gemeinden/warnWetter_node.html"],
        "wait_selector": "#warnungen, .warn_table, body",
        "content_selector": "#warnungen, .warn_table, .warning-content, body",
        "category": "sensor_wetter"
    }
]


# ==========================================
# 6. MAIN ORCHESTRATOR MIT TRIAGE
# ==========================================
async def main():
  print(
      f"⚓ ZUSATZ-RADAR (V44.0 PROVENIENZ) GESTARTET ({datetime.date.today()})"
  )
  try:
    validate_arsenal(ZUSATZ_ARSENAL)
  except Exception as e:
    print(e)
    return

  state = load_state()
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    results = []
    for slot in ZUSATZ_ARSENAL:
      results.append(await process_slot(slot, state, browser))
      await asyncio.sleep(1.0)
    await browser.close()
  save_state_atomic(state)

  timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
  log_file = os.path.join(LOG_DIR, f"API_Praxis_V44_{timestamp}.txt")

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
      f" PRAXIS-LAGEBERICHT V44.0 ({datetime.date.today()})\n============================================================\n"
  ]

  report.append(
      "\n[Ã°Å¸â€Â´ AKUTER HANDLUNGSBEDARF / ÄNDERUNGEN ERKANNT]\n" + "=" * 50
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
  print(f"\n[PRAXIS-MASTERLOG] Gespeichert: {log_file}")


if __name__ == "__main__":
  asyncio.run(main())



