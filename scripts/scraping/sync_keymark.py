#!/usr/bin/env python3
"""
Incremental Keymark Scraper
===========================
Syncs heat pump data from heatpumpkeymark.com to /data/source/

Features:
- Detects new heat pumps not yet in local database
- Downloads both CSV and PDF for new entries
- Parallel processing for faster syncs
- Logs all additions with timestamps
- Resumes from interruption

Usage:
    python sync_keymark.py              # Sync new entries (parallel)
    python sync_keymark.py --dry-run    # Preview what would be downloaded
    python sync_keymark.py --workers 4  # Use 4 parallel workers
    python sync_keymark.py --force      # Re-download all (careful!)
"""

import os
import sys
import json
import time
import re
import argparse
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ==============================================================================
# Configuration
# ==============================================================================

BASE_URL = "https://www.heatpumpkeymark.com"
MANUFACTURERS_URL = f"{BASE_URL}/?type=109126"

# Paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_SOURCE = PROJECT_ROOT / "data" / "source"
LOGS_DIR = PROJECT_ROOT / "data" / "logs"

# Files
SYNC_LOG = LOGS_DIR / "sync_log.jsonl"
STATE_FILE = LOGS_DIR / "sync_state.json"

# Request settings
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 90
SLEEP_BETWEEN_REQUESTS = 0.3  # seconds (can be lower with parallel)
DEFAULT_WORKERS = 6  # parallel workers

# Thread-local storage for sessions
thread_local = threading.local()

# ==============================================================================
# Logging setup
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ==============================================================================
# HTTP Session (thread-safe)
# ==============================================================================

def get_session() -> requests.Session:
    """Get a thread-local session for thread-safe HTTP requests."""
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
        thread_local.session.headers.update(HEADERS)
    return thread_local.session


def fetch(url: str, retries: int = 3, backoff: int = 10) -> str:
    """Fetch URL with retries and exponential backoff."""
    session = get_session()
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.text
        except Exception as e:
            logger.warning(f"Fetch attempt {attempt} failed for {url}: {e}")
            if attempt < retries:
                time.sleep(backoff * attempt)
            else:
                raise


def fetch_binary(url: str, retries: int = 3) -> bytes:
    """Fetch binary content (for PDFs)."""
    session = get_session()
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.content
        except Exception as e:
            logger.warning(f"Binary fetch attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(5 * attempt)
            else:
                raise


# ==============================================================================
# Filename utilities (matching original scraper patterns)
# ==============================================================================

def safe_filename_csv(name: str) -> str:
    """Make filename safe for CSV (matches original scrape_single_csvs.py)."""
    name = re.sub(r'[<>:"/\\|?*\t\r\n]', '_', name)
    name = name.strip(" .")
    return name


def safe_filename_pdf(text: str) -> str:
    """Make filename safe for PDF (matches original scrape_single_pdfs.py)."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text)


def make_csv_filename(manufacturer: str, model: str) -> str:
    """Generate CSV filename matching existing pattern."""
    filename = manufacturer + model
    filename = filename.replace(' ', '_')
    filename = safe_filename_csv(filename)
    return f"_{filename}.csv"


def make_pdf_filename(manufacturer: str, subtype: str, hp_type: str, count: int) -> str:
    """Generate PDF filename matching existing pattern."""
    manu = safe_filename_pdf(manufacturer)[:40]
    sub = safe_filename_pdf(subtype)[:60]
    hpt = safe_filename_pdf(hp_type)[:40]
    return f"{manu}_{sub}_{hpt}_{count}.pdf"


def get_next_pdf_number(manufacturer: str) -> int:
    """
    Find the next available PDF number for a manufacturer.
    Scans existing PDFs and returns max + 1.
    """
    manu_prefix = safe_filename_pdf(manufacturer)[:40] + "_"
    max_num = 0
    
    for pdf_file in DATA_SOURCE.glob("*.pdf"):
        if pdf_file.name.startswith(manu_prefix):
            # Extract the number at the end (before .pdf)
            # Pattern: Manufacturer_Model_Type_N.pdf
            try:
                # Get the part before .pdf and split by _
                parts = pdf_file.stem.rsplit("_", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    num = int(parts[1])
                    max_num = max(max_num, num)
            except (ValueError, IndexError):
                pass
    
    return max_num + 1


# ==============================================================================
# Keymark parsing
# ==============================================================================

def get_manufacturers() -> list[tuple[str, str]]:
    """Get list of (manufacturer_name, manufacturer_url) from Keymark."""
    html = fetch(MANUFACTURERS_URL)
    soup = BeautifulSoup(html, "html.parser")
    
    manufacturers = []
    for td in soup.find_all("td"):
        a = td.find("a")
        if a and a.get("href"):
            name = td.get_text(strip=True)
            url = urljoin(BASE_URL, a["href"])
            manufacturers.append((name, url))
    
    logger.info(f"Found {len(manufacturers)} manufacturers on Keymark")
    return manufacturers


def get_models_for_manufacturer(manufacturer_url: str) -> list[dict]:
    """Get all models for a manufacturer."""
    html = fetch(manufacturer_url)
    soup = BeautifulSoup(html, "html.parser")
    
    models = []
    seen_urls = set()  # Deduplicate
    
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) >= 1:
            first_td = tds[0]
            a = first_td.find("a")
            if a and "subtype" in str(a.get("href", "")):
                model_name = first_td.get_text(strip=True)
                model_url = urljoin(BASE_URL, a["href"])
                
                if model_url not in seen_urls:
                    seen_urls.add(model_url)
                    models.append({
                        "name": model_name,
                        "url": model_url,
                    })
    
    return models


def get_model_details(model_url: str) -> dict:
    """Get detailed info for a model (metadata + download links)."""
    html = fetch(model_url)
    soup = BeautifulSoup(html, "html.parser")
    
    details = {
        "refrigerant": "",
        "mass_of_refrigerant": "",
        "certification_date": "",
        "hp_type": "",
        "driving_energy": "",
        "registration_number": "",
        "model_names": [],  # All model name variants on this certificate
        "csv_export_url": None,
        "pdf_url": None,
    }
    
    # Parse metadata
    for info_col in soup.find_all(class_="info-coll"):
        label_elem = info_col.find(class_="info-label")
        data_elem = info_col.find(class_="info-data")
        if not label_elem or not data_elem:
            continue
        
        label_span = label_elem.find("span")
        if not label_span:
            continue
        
        label = label_span.get_text(strip=True)
        data = data_elem.get_text(strip=True)
        
        if label == "Refrigerant":
            details["refrigerant"] = data.replace(" ", "").replace("\n", "")
        elif label == "Mass of Refrigerant":
            details["mass_of_refrigerant"] = data.replace("\n", "")
        elif label == "Certification Date":
            details["certification_date"] = data.replace(" ", "").replace("\n", "")
        elif label == "Registration number":
            # Clean up registration number
            details["registration_number"] = " ".join(data.split())
        elif label == "Model name":
            # Collect all model name variants
            details["model_names"].append(data.strip())
        elif label == "Heat Pump Type":
            # Clean up the type string
            raw = data_elem.get_text()
            details["hp_type"] = raw.replace("\n", "").strip()
            if len(details["hp_type"]) > 22:
                details["hp_type"] = details["hp_type"][13:-9]  # Original extraction
        elif label == "Driving energy":
            raw = data_elem.get_text()
            details["driving_energy"] = raw.replace("\n", "").strip()
            if len(details["driving_energy"]) > 22:
                details["driving_energy"] = details["driving_energy"][13:-9]
    
    # Find export/download links
    for a in soup.find_all("a"):
        text = a.get_text(strip=True)
        href = a.get("href", "")
        
        if text.startswith("Export"):
            details["csv_export_url"] = urljoin(BASE_URL, href)
        elif "generatePdf" in href:
            details["pdf_url"] = urljoin(BASE_URL, href)
    
    return details


def get_csv_download_url(export_page_url: str) -> str | None:
    """Get the actual CSV download URL from the export page."""
    html = fetch(export_page_url)
    soup = BeautifulSoup(html, "html.parser")
    
    for a in soup.find_all("a"):
        if a.get_text(strip=True) == "Download":
            return urljoin(BASE_URL, a["href"])
    return None


# ==============================================================================
# File operations
# ==============================================================================

def normalize_for_comparison(text: str) -> str:
    """Normalize text for comparison (lowercase, stripped, collapsed whitespace)."""
    return " ".join(text.lower().strip().split())


def get_existing_files() -> tuple[set[str], set[str]]:
    """Get sets of existing CSV and PDF filenames."""
    DATA_SOURCE.mkdir(parents=True, exist_ok=True)
    
    csv_files = {f.name for f in DATA_SOURCE.glob("*.csv")}
    pdf_files = {f.name for f in DATA_SOURCE.glob("*.pdf")}
    
    return csv_files, pdf_files


def build_existing_models_index() -> tuple[set[tuple[str, str]], dict[tuple[str, str], str], set[str]]:
    """
    Build index of existing models from CSV content (not filenames).
    
    Returns:
        - Set of (normalized_manufacturer, normalized_title) tuples
        - Dict mapping (manu, title) -> filename for reference
        - Set of all normalized titles (for fast title-only matching)
    """
    import csv as csv_module
    csv_module.field_size_limit(500000)
    
    DATA_SOURCE.mkdir(parents=True, exist_ok=True)
    
    existing_models = set()
    model_to_file = {}
    all_titles = set()  # For fast title-only lookup
    
    for csv_file in DATA_SOURCE.glob("*.csv"):
        try:
            with open(csv_file, "r", encoding="utf-8", errors="replace") as f:
                reader = csv_module.reader(f)
                manufacturer = None
                titles = []  # A CSV can have multiple model names
                
                for row in reader:
                    if len(row) >= 3:
                        if row[1] == "Manufacturer":
                            manufacturer = row[2].strip()
                        elif row[1] == "title":
                            titles.append(row[2].strip())
                
                # If no manufacturer in content, try to extract from filename
                # Filename pattern: _ManufacturerModelname.csv
                if not manufacturer and csv_file.name.startswith("_"):
                    # Best effort: can't reliably parse, but try common patterns
                    pass
                
                if manufacturer and titles:
                    manu_norm = normalize_for_comparison(manufacturer)
                    for title in titles:
                        title_norm = normalize_for_comparison(title)
                        key = (manu_norm, title_norm)
                        existing_models.add(key)
                        model_to_file[key] = csv_file.name
                        all_titles.add(title_norm)
                elif titles and not manufacturer:
                    # File has titles but no manufacturer - index by title only
                    # This allows matching on title across all manufacturers
                    for title in titles:
                        title_norm = normalize_for_comparison(title)
                        # Use empty string for manufacturer to enable title-only matching
                        key = ("", title_norm)
                        existing_models.add(key)
                        model_to_file[key] = csv_file.name
                        all_titles.add(title_norm)
        except Exception:
            pass  # Skip problematic files
    
    logger.info(f"Indexed {len(existing_models)} existing models from CSV content ({len(all_titles)} unique titles)")
    return existing_models, model_to_file, all_titles


def download_csv(url: str, filepath: Path, metadata: dict) -> bool:
    """Download CSV and append metadata."""
    try:
        content = fetch_binary(url)
        
        with open(filepath, "wb") as f:
            f.write(content)
        
        # Append metadata (matching original format)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f'"","Refrigerant","{metadata.get("refrigerant", "")}","0","0","0","0"\r\n')
            f.write(f'"","Mass of Refrigerant","{metadata.get("mass_of_refrigerant", "")}","0","0","0","0"\r\n')
            f.write(f'"","Date","{metadata.get("certification_date", "")}","0","0","0","0"\r\n')
            f.write(f'"","Manufacturer","{metadata.get("manufacturer", "")}","0","0","0","0"\r\n')
            f.write(f'"","Modelname","{metadata.get("model", "")}","0","0","0","0"\r\n')
            f.write(f'"","Type","{metadata.get("hp_type", "")}","0","0","0","0"\r\n')
            f.write(f'"","Energy","{metadata.get("driving_energy", "")}","0","0","0","0"\r\n')
        
        return True
    except Exception as e:
        logger.error(f"Failed to download CSV {url}: {e}")
        return False


def download_pdf(url: str, filepath: Path) -> bool:
    """Download PDF file."""
    try:
        content = fetch_binary(url)
        with open(filepath, "wb") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Failed to download PDF {url}: {e}")
        return False


# ==============================================================================
# Sync log
# ==============================================================================

def log_sync_entry(entry: dict):
    """Append entry to sync log (JSONL format)."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    entry["timestamp"] = datetime.now().isoformat()
    
    with open(SYNC_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def save_state(state: dict):
    """Save sync state for resume."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def load_state() -> dict:
    """Load sync state."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ==============================================================================
# Main sync logic
# ==============================================================================

def process_model(
    model: dict,
    model_idx: int,
    manufacturer: str,
    existing_csv: set,
    existing_models: set,
    all_titles: set,
    dry_run: bool,
    force: bool,
) -> dict:
    """
    Process a single model - fetch details and download files if new.
    Returns a result dict with status and any new entry info.
    """
    model_name = model["name"]
    model_url = model["url"]
    
    result = {
        "status": "skipped",
        "entry": None,
        "csv_downloaded": False,
        "pdf_downloaded": False,
        "error": None,
        "fast_path": False,
    }
    
    # Generate expected filenames
    csv_filename = make_csv_filename(manufacturer, model_name)
    
    # In force mode, skip existence check
    if not force:
        # FAST PATH 1: Filename check (instant)
        if csv_filename in existing_csv:
            result["fast_path"] = True
            return result
        
        # FAST PATH 2: Check if listing model name exists in our title index
        manu_norm = normalize_for_comparison(manufacturer)
        model_name_norm = normalize_for_comparison(model_name)
        
        # Check (manufacturer, model_name) combo
        if (manu_norm, model_name_norm) in existing_models:
            result["fast_path"] = True
            return result
        
        # Check title-only index (fast lookup)
        if model_name_norm in all_titles:
            result["fast_path"] = True
            return result
    
    # Only fetch details if we couldn't match from listing info
    # This is the SLOW path - only for genuinely new models
    try:
        details = get_model_details(model_url)
        time.sleep(SLEEP_BETWEEN_REQUESTS)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        return result
    
    # Double-check with detail page model names (more thorough)
    manu_norm = normalize_for_comparison(manufacturer)
    is_existing = False
    
    for model_title in details.get("model_names", []):
        title_norm = normalize_for_comparison(model_title)
        # Check with manufacturer
        if (manu_norm, title_norm) in existing_models:
            is_existing = True
            break
        # Also check title-only (for files without manufacturer in content)
        if ("", title_norm) in existing_models:
            is_existing = True
            break
        # Check all_titles set
        if title_norm in all_titles:
            is_existing = True
            break
    
    if is_existing and not force:
        result["status"] = "skipped"
        return result
    
    # New model found!
    result["status"] = "new"
    
    # Prepare metadata
    metadata = {
        "manufacturer": manufacturer,
        "model": model_name,
        "refrigerant": details.get("refrigerant", ""),
        "mass_of_refrigerant": details.get("mass_of_refrigerant", ""),
        "certification_date": details.get("certification_date", ""),
        "hp_type": details.get("hp_type", ""),
        "driving_energy": details.get("driving_energy", ""),
    }
    
    entry = {
        "manufacturer": manufacturer,
        "model": model_name,
        "model_names": details.get("model_names", []),
        "registration_number": details.get("registration_number", ""),
        "certification_date": details.get("certification_date", ""),
        "csv_file": csv_filename,
        "pdf_file": None,
        "action": "new",
    }
    result["entry"] = entry
    result["details"] = details
    result["metadata"] = metadata
    result["model_idx"] = model_idx
    
    # Check if PDF needs downloading (for both dry run reporting and actual download)
    pdf_needs_download = False
    pdf_filename = None
    if details.get("pdf_url"):
        # Get next available number for this manufacturer
        next_num = get_next_pdf_number(manufacturer)
        pdf_filename = make_pdf_filename(
            manufacturer,
            model_name,
            details.get("hp_type", "Unknown"),
            next_num
        )
        pdf_path = DATA_SOURCE / pdf_filename
        # Check if exact filename exists (unlikely with incrementing numbers, but safe)
        pdf_needs_download = not pdf_path.exists() or force
        result["pdf_needs_download"] = pdf_needs_download
        if pdf_needs_download:
            entry["pdf_file"] = pdf_filename
    
    if not dry_run:
        # Download CSV
        if details.get("csv_export_url"):
            csv_download_url = get_csv_download_url(details["csv_export_url"])
            if csv_download_url:
                csv_path = DATA_SOURCE / csv_filename
                if download_csv(csv_download_url, csv_path, metadata):
                    result["csv_downloaded"] = True
                time.sleep(SLEEP_BETWEEN_REQUESTS)
        
        # Download PDF (if needed)
        if pdf_needs_download and pdf_filename:
            if download_pdf(details["pdf_url"], pdf_path):
                result["pdf_downloaded"] = True
            time.sleep(SLEEP_BETWEEN_REQUESTS)
        
        # Log the entry
        log_sync_entry(entry)
    
    return result


def sync_keymark(dry_run: bool = False, force: bool = False, workers: int = DEFAULT_WORKERS):
    """
    Main sync function with parallel processing.
    
    Uses content-based matching to detect new models:
    - Extracts (manufacturer, title) pairs from existing CSV files
    - Fetches each model's detail page to get actual model names
    - Only downloads if model names don't exist in index
    - Processes models in parallel for speed
    
    Args:
        dry_run: If True, only report what would be downloaded
        force: If True, re-download all files
        workers: Number of parallel workers
    """
    logger.info("=" * 60)
    logger.info("Keymark Heat Pump Data Sync")
    logger.info("=" * 60)
    
    if dry_run:
        logger.info("DRY RUN MODE - No files will be downloaded")
    logger.info(f"Using {workers} parallel workers")
    
    # Ensure directories exist
    DATA_SOURCE.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Build content-based index of existing models
    existing_models, model_to_file, all_titles = build_existing_models_index()
    
    # Get existing filenames
    existing_csv, existing_pdf = get_existing_files()
    logger.info(f"Existing files: {len(existing_csv)} CSVs, {len(existing_pdf)} PDFs")
    
    # Get all manufacturers
    manufacturers = get_manufacturers()
    
    # Track statistics
    stats = {
        "manufacturers_processed": 0,
        "models_found": 0,
        "models_checked": 0,
        "new_csvs": 0,
        "new_pdfs": 0,
        "skipped_existing": 0,
        "skipped_fast_path": 0,  # Skipped without fetching details
        "details_fetched": 0,    # Had to fetch detail pages
        "errors": 0,
    }
    
    new_entries = []
    new_entries_lock = threading.Lock()
    stats_lock = threading.Lock()
    
    for manu_idx, (manufacturer, manu_url) in enumerate(manufacturers):
        logger.info(f"[{manu_idx + 1}/{len(manufacturers)}] Processing: {manufacturer}")
        
        try:
            models = get_models_for_manufacturer(manu_url)
            with stats_lock:
                stats["models_found"] += len(models)
            
            if not models:
                continue
            
            # Process models in parallel within this manufacturer
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(
                        process_model,
                        model,
                        model_idx,
                        manufacturer,
                        existing_csv,
                        existing_models,
                        all_titles,
                        dry_run,
                        force,
                    ): model
                    for model_idx, model in enumerate(models)
                }
                
                for future in as_completed(futures):
                    model = futures[future]
                    try:
                        result = future.result()
                        
                        with stats_lock:
                            stats["models_checked"] += 1
                            
                            if result["status"] == "error":
                                stats["errors"] += 1
                                logger.error(f"  Error: {model['name']}: {result['error']}")
                            elif result["status"] == "skipped":
                                stats["skipped_existing"] += 1
                                if result["fast_path"]:
                                    stats["skipped_fast_path"] += 1
                            elif result["status"] == "new":
                                stats["details_fetched"] += 1
                                
                                entry = result["entry"]
                                logger.info(f"  NEW: {model['name']}")
                                if result.get("details", {}).get("model_names"):
                                    logger.info(f"       Model names: {', '.join(result['details']['model_names'][:3])}")
                                if result.get("details", {}).get("certification_date"):
                                    logger.info(f"       Cert date: {result['details']['certification_date']}")
                                
                                if dry_run:
                                    # Dry run: count what would be downloaded
                                    stats["new_csvs"] += 1
                                    if result.get("pdf_needs_download"):
                                        stats["new_pdfs"] += 1
                                else:
                                    # Actual download: count what was downloaded
                                    if result["csv_downloaded"]:
                                        stats["new_csvs"] += 1
                                        logger.info(f"    ✓ Downloaded CSV: {entry['csv_file']}")
                                    if result["pdf_downloaded"]:
                                        stats["new_pdfs"] += 1
                                        logger.info(f"    ✓ Downloaded PDF: {entry.get('pdf_file', 'unknown')}")
                                
                                with new_entries_lock:
                                    new_entries.append(entry)
                    
                    except Exception as e:
                        logger.error(f"  Future error for {model['name']}: {e}")
                        with stats_lock:
                            stats["errors"] += 1
            
            with stats_lock:
                stats["manufacturers_processed"] += 1
            
            # Save state for resume
            save_state({
                "last_manufacturer_index": manu_idx,
                "last_sync": datetime.now().isoformat(),
            })
            
        except Exception as e:
            logger.error(f"Error processing manufacturer {manufacturer}: {e}")
            with stats_lock:
                stats["errors"] += 1
            continue
    
    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SYNC COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Manufacturers processed: {stats['manufacturers_processed']}")
    logger.info(f"Total models found: {stats['models_found']}")
    logger.info(f"Skipped (fast path - no HTTP): {stats['skipped_fast_path']}")
    logger.info(f"Detail pages fetched: {stats['details_fetched']}")
    logger.info(f"Skipped (already existing): {stats['skipped_existing']}")
    logger.info(f"New CSVs {'would be' if dry_run else ''} downloaded: {stats['new_csvs']}")
    logger.info(f"New PDFs {'would be' if dry_run else ''} downloaded: {stats['new_pdfs']}")
    logger.info(f"Errors: {stats['errors']}")
    
    if new_entries:
        logger.info("")
        logger.info("New heat pumps added:")
        for entry in new_entries[:20]:  # Show first 20
            logger.info(f"  - {entry['manufacturer']}: {entry['model']}")
            if entry.get('certification_date'):
                logger.info(f"    Cert: {entry['certification_date']}")
        if len(new_entries) > 20:
            logger.info(f"  ... and {len(new_entries) - 20} more")
    
    return stats


# ==============================================================================
# CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Sync heat pump data from Keymark database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sync_keymark.py              # Sync new entries (6 workers)
  python sync_keymark.py --dry-run    # Preview what would be downloaded
  python sync_keymark.py --workers 10 # Use 10 parallel workers
  python sync_keymark.py --force      # Re-download everything

Log files are written to: data/logs/
  - sync_log.jsonl: Record of all synced entries
  - sync_state.json: Resume state
        """,
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without downloading",
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download all files (use with caution)",
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of parallel workers (default: {DEFAULT_WORKERS})",
    )
    
    args = parser.parse_args()
    
    try:
        sync_keymark(dry_run=args.dry_run, force=args.force, workers=args.workers)
    except KeyboardInterrupt:
        logger.info("\nSync interrupted. Resume by running again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
