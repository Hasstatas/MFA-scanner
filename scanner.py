import os
import csv
from pathlib import Path

import pytesseract
from PIL import Image

from strategies import load_strategies  # to link to the new strategies folder


# ----------------------------
# Ensure pytesseract can find the engine
# ----------------------------
def _set_tesseract_path() -> str | None:
    """
    Resolve the Tesseract executable path once per run.
    Priority:
      1) TESSERACT_PATH environment variable (if you want to override)
      2) Common Windows install locations
    """
    candidates = [
        os.environ.get("TESSERACT_PATH"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for p in candidates:
        if p and Path(p).exists():
            pytesseract.pytesseract.tesseract_cmd = p
            return p
    return None


_TESS = _set_tesseract_path()
if not _TESS:
    print("[!] Tesseract not found automatically. Set env var TESSERACT_PATH "
          "or install to C:\\Program Files\\Tesseract-OCR.")


# ----------------------------
# Simple menu helper
# ----------------------------
def choose_from_menu(title, options):
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


# ----------------------------
# OCR helper
# ----------------------------
def run_ocr(path: str) -> str:
    """Open the image and extract raw text via Tesseract OCR."""
    with Image.open(path) as img:
        return pytesseract.image_to_string(img)


# ----------------------------
# Main
# ----------------------------
def main():
    # 1) Ask for a username label (goes to the CSV)
    user_id = input("Enter your username: ").strip()

    # 2) Load strategies
    strategies = load_strategies()
    if not strategies:
        print("No strategies found")
        return

    # 3) Let user pick strategies
    names_for_menu = [f"{s.name} — {s.description()}" for s in strategies]
    chosen_menu = choose_from_menu("\nAvailable strategies:", names_for_menu)

    chosen_names = {n.split(" — ")[0] for n in chosen_menu}
    chosen_strategies = [s for s in strategies if s.name in chosen_names]

    if not chosen_strategies:
        print("Not a valid selection. Exiting the application.")
        return

    print("\n📋 Scanning using strategies:", ", ".join(s.name for s in chosen_strategies), "\n")

    # 4) Collect evidence images
    screenshots_dir = Path("screenshots")
    if not screenshots_dir.exists():
        print("Please add your screenshots before proceeding (missing ./screenshots)")
        return

    SUPPORTED_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")
    image_files = [f for f in os.listdir(screenshots_dir) if f.lower().endswith(SUPPORTED_EXTS)]
    if not image_files:
        print("No image files found in ./screenshots.")
        return

    # 5) Prepare CSV header
    report_rows = [(
        "UserID", "Image", "Strategy", "TestID", "Sub-Strategy",
        "ML Level", "Pass/Fail", "Priority", "Recommendation", "Evidence Extract"
    )]

    # 6) Process each image
    for file in image_files:
        print(f"🖼️  {file}:")
        img_path = screenshots_dir / file

        try:
            raw_text = run_ocr(str(img_path))
            # Optional debug
            # print("📝 OCR Text:", raw_text)
        except Exception as e:
            print(f"   [x] OCR failed for {file}: {e}")
            # still write a row so the user sees failures in the CSV
            report_rows.append((
                user_id, file, "OCR", "", "", "", "FAIL", "High",
                "OCR failed (check Tesseract installation/path and image file).",
                str(e)
            ))
            continue

        for strat in chosen_strategies:
            if hasattr(strat, "emit_hits"):
                rows = strat.emit_hits(raw_text)  # list[dict]
                for r in rows:
                    report_rows.append((
                        user_id,
                        file,
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
                # Fallback: simple keyword matching if a strategy doesn't implement emit_hits
                hits = strat.match(raw_text)
                if hits:
                    report_rows.append((
                        user_id, file, strat.name, "", "", "", "", "", "", ", ".join(hits)
                    ))

    # 7) Save CSV
    with open("scan_report.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(report_rows)

    print("\n✅ Report saved as: scan_report.csv")


if __name__ == "__main__":
    main()
