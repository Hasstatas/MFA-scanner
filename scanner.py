# scanner.py
import os
import csv
from pathlib import Path
from typing import List
import pytesseract
from PIL import Image, UnidentifiedImageError

from strategies import load_strategies  # your plugin loader

# ---------- Folder mapping for the 8 Essential Eight strategies ----------
STRAT_DIR_MAP = {
    "application control": "application_control",
    "restrict admin privileges": "restrict_admin_privileges",
    "patch applications": "patch_applications",
    "patch operating systems": "patch_operating_systems",
    "configure microsoft office macro settings": "configure_macro_settings",
    "multi-factor authentication": "multi_factor_authentication",
    "regular backups": "regular_backups",
    "user application hardening": "user_application_hardening",
}

# ---------- File type support ----------
SUPPORTED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")
SUPPORTED_TEXT_EXTS  = (".txt", ".log", ".reg", ".csv", ".ini", ".json", ".xml", ".htm", ".html")

# ---------- UI helpers ----------
def choose_from_menu(title: str, options: List[str]) -> List[str]:
    print(title)
    for i, o in enumerate(options, 1):
        print(f"{i}. {o}")
    raw = input("Select the strategy by number(s) e.g. 1,3,5 for multiple strategies: ")
    idxs = []
    for tok in raw.split(","):
        tok = tok.strip()
        if tok.isdigit() and 1 <= int(tok) <= len(options):
            idxs.append(int(tok) - 1)
    return [options[i] for i in idxs]

# ---------- Content extraction ----------
def run_ocr(path: Path) -> str:
    """OCR image -> text (safe)."""
    try:
        with Image.open(path) as img:
            return pytesseract.image_to_string(img)
    except (UnidentifiedImageError, OSError):
        return ""

def read_text_file(path: Path) -> str:
    """Read small text-like files into a single string."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            return path.read_text(errors="ignore")
        except Exception:
            return ""

def extract_text(path: Path) -> str:
    """Choose OCR for images, direct read for text files."""
    ext = path.suffix.lower()
    if ext in SUPPORTED_IMAGE_EXTS:
        return run_ocr(path)
    if ext in SUPPORTED_TEXT_EXTS:
        return read_text_file(path)
    return ""  # unsupported

def list_supported_files(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    out = []
    for p in folder.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() in SUPPORTED_IMAGE_EXTS or p.suffix.lower() in SUPPORTED_TEXT_EXTS:
            out.append(p)
    return sorted(out, key=lambda x: x.name.lower())

# ---------- Main ----------
def main():
    # 1) user id
    user_id = input("Enter your username: ").strip()

    # 2) load strategies
    strategies = load_strategies()
    if not strategies:
        print("No strategies found")
        return

    # 3) pick strategies
    names_for_menu = [f"{s.name} — {s.description()}" for s in strategies]
    chosen_menu = choose_from_menu("\nAvailable strategies:", names_for_menu)

    chosen_names = {n.split(" — ")[0] for n in chosen_menu}
    chosen_strategies = [s for s in strategies if s.name in chosen_names]

    if not chosen_strategies:
        print("Not a valid selection. Exiting the application.")
        return

    print("\n📋 Scanning using strategies:", ", ".join(s.name for s in chosen_strategies), "\n")

    # 4) where screenshots/files live
    base_dir = Path("screenshots")

    # 5) CSV header
    report_rows = [(
        "UserID", "Image", "Strategy", "TestID", "Sub-Strategy",
        "ML Level", "Pass/Fail", "Priority", "Recommendation", "Evidence Extract"
    )]

    # 6) scan per strategy
    for strat in chosen_strategies:
        strat_key = strat.name.lower().strip()
        strat_sub = STRAT_DIR_MAP.get(strat_key, None)
        preferred = (base_dir / strat_sub) if strat_sub else base_dir
        fallback  = base_dir

        files = list_supported_files(preferred)
        using_dir = preferred
        if not files:
            files = list_supported_files(fallback)
            using_dir = fallback

        if not files:
            print(f"⚠️  No files found for '{strat.name}' in '{preferred}' or '{fallback}'. Skipping.")
            continue

        print(f"\n🔎 Strategy: {strat.name}")
        print(f"   Using inputs from: {using_dir}")

        for fpath in files:
            print(f"📄 {fpath.name}:")
            raw_text = extract_text(fpath)
            if not raw_text.strip():
                print("   (no readable text found)\n")
                continue

            preview = (raw_text[:200] + "…") if len(raw_text) > 200 else raw_text
            print("📝 Extracted:", preview.replace("\n", " ")[:200], "\n")

            if hasattr(strat, "emit_hits"):
                # ✅ pass filename for ML1-OM-02 comparison
                rows = strat.emit_hits(raw_text, source_file=fpath.name)  # <— updated
                for r in rows:
                    report_rows.append((
                        user_id,
                        fpath.name,
                        strat.name,
                        r.get("test_id", ""),
                        r.get("sub_strategy", ""),
                        r.get("detected_level", ""),
                        r.get("pass_fail", ""),
                        r.get("priority", ""),
                        r.get("recommendation", ""),
                        "; ".join(r.get("evidence", [])),
                    ))
            else:
                # fallback if a strategy only provides .match()
                hits = strat.match(raw_text)
                if hits:
                    report_rows.append((
                        user_id, fpath.name, strat.name, "", "", "", "", "", "", ", ".join(hits)
                    ))

    # 7) save
    try:
        with open("scan_report.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(report_rows)
        print("\n✅ Report saved as: scan_report.csv")
    except PermissionError:
        temp_name = "scan_report_temp.csv"
        with open(temp_name, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(report_rows)
        print(f"\n⚠️  'scan_report.csv' was locked. Saved as: {temp_name}")

if __name__ == "__main__":
    main()
