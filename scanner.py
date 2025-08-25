import pytesseract
from PIL import Image
import os
import csv
from pathlib import Path
from strategies import load_strategies # to link to the new strategies folder

# a numbered list of the strategies and return them
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

# open the image and extracts text using Tesseract OCR with raw text 
def run_ocr(path: str) -> str:
    img = Image.open(path)
    return pytesseract.image_to_string(img)

# main scanner 
def main():
    # step 1: request for User ID
    user_id = input("Enter your username: ").strip() 
    # step 2: load strategies from the folders
    strategies = load_strategies()
    if not strategies:
        print("No strategies found")
        return

    # step 3: user to chooset the strategy with description to run 
    names_for_menu = [f"{s.name} — {s.description()}" for s in strategies]
    chosen_menu = choose_from_menu("\nAvailable strategies:", names_for_menu)

    chosen_names = {n.split(" — ")[0] for n in chosen_menu}
    chosen_strategies = [s for s in strategies if s.name in chosen_names]

    if not chosen_strategies:
        print("Not a valid selection. Exiting the application.")  # if none or wrong number
        return

    print("\n📋 Scanning using strategies:", ", ".join(s.name for s in chosen_strategies), "\n")

    # step 4: scans all .png files in the screenshots folder - next step: to have option to select the screenshot instead of running all 
    screenshots_dir = Path("screenshots")
    if not screenshots_dir.exists():
        print("Please add your screenshots before proceeding")
        return

    SUPPORTED_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp") # allow different formats of screenshots

    image_files = [f for f in os.listdir(screenshots_dir) if f.lower().endswith(SUPPORTED_EXTS)]
    if not image_files:
        print("No files found in screenshots folder.")
        return

    # step 5: Prepare report fields
    report_rows = [(
        "UserID", "Image", "Strategy", "TestID", "Sub-Strategy",
        "ML Level", "Pass/Fail", "Priority", "Recommendation", "Evidence Extract"
    )]

# step 6: OCR each image in the "screenshots" folder
    for file in image_files:
        print(f"🖼️  {file}:")
        img_path = screenshots_dir / file
        raw_text = run_ocr(str(img_path))

        print("📝 OCR Text:", raw_text)  # Optional debug print

        for strat in chosen_strategies:
            if hasattr(strat, "emit_hits"):
                rows = strat.emit_hits(raw_text)  # list[dict]
                for r in rows:
                    report_rows.append((
                        user_id,
                        file,
                        strat.name, #strategy name 
                        r.get("test_id",""),
                        r.get("sub_strategy",""),
                        r.get("detected_level",""),
                        r.get("pass_fail",""),
                        r.get("priority",""),
                        r.get("recommendation",""),
                        "; ".join(r.get("evidence", [])),
                    ))
            else:
                # contingency fallback if none detected
                hits = strat.match(raw_text)
                if hits:
                    report_rows.append((user_id, file, strat.name, "", "", "", "", "", "", ", ".join(hits)))

    # Save CSV
    with open("scan_report.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(report_rows)

    print("\n✅ Report saved as: scan_report.csv")

if __name__ == "__main__":
    main()