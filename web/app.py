# web/app.py
import io
from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from strategies import load_strategies
from reports.report_service import generate_pdf

# --- reuse your extraction helpers (copy/paste or import) ---
from scanner_report_generator import extract_text_and_preview  # if you prefer, paste those funcs here

app = FastAPI(title="AutoAudit Evidence Scanner")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# list of strategies as names shown to the user
STRATEGY_NAMES = [s.name for s in load_strategies()]

@app.get("/api/strategies")
def list_strategies():
    return {"strategies": STRATEGY_NAMES}

@app.post("/api/scan")
async def scan(
    strategy: str = Form(...),
    user_id: str = Form("user"),
    evidence: UploadFile = File(...)
):
    # 1) validate strategy
    strategies = load_strategies()
    chosen = next((s for s in strategies if s.name == strategy), None)
    if not chosen:
        raise HTTPException(status_code=400, detail="Unknown strategy")

    # 2) save the uploaded file to ./evidence/tmp/
    ev_dir = Path("evidence/tmp")
    ev_dir.mkdir(parents=True, exist_ok=True)
    ev_path = ev_dir / evidence.filename
    content = await evidence.read()
    ev_path.write_bytes(content)

    # 3) extract text + preview image (uses your helper)
    previews_dir = Path("previews")
    previews_dir.mkdir(parents=True, exist_ok=True)
    text, preview = extract_text_and_preview(ev_path, previews_dir)

    # 4) run strategy logic
    rows = []
    if hasattr(chosen, "emit_hits"):
        rows = chosen.emit_hits(text or "", source_file=ev_path.name) or []
    else:
        hits = chosen.match(text or "") or []
        if hits:
            rows = [{
              "test_id": "", "sub_strategy": "", "detected_level": "",
              "pass_fail": "HIT", "priority": "Medium",
              "recommendation": "Heuristic match.",
              "evidence": hits
            }]

    # 5) if rows exist, render a PDF for each row
    generated = []
    for i, r in enumerate(rows, 1):
        data = {
            "UniqueID": f"{user_id}-{strategy}-{ev_path.stem}-{i}",
            "UserID": user_id,
            "Evidence": str(ev_path),
            "Evidence Preview": str(preview) if preview else "",
            "Strategy": strategy,
            "TestID": r.get("test_id",""),
            "Sub-Strategy": r.get("sub_strategy",""),
            "ML Level": r.get("detected_level",""),
            "Pass/Fail": r.get("pass_fail",""),
            "Priority": r.get("priority",""),
            "Recommendation": r.get("recommendation",""),
            "Evidence Extract": "; ".join(r.get("evidence", [])),
        }
        pdf_path = generate_pdf(
            data,
            template_path="templates/report_template.docx",
            output_dir="reports_out",
            base_dir="."
        )
        generated.append(str(pdf_path))

    return JSONResponse({
        "strategy": strategy,
        "user_id": user_id,
        "file": ev_path.name,
        "rows": rows,                 # what we detected
        "reports": generated          # paths to generated PDFs
    })

@app.get("/api/report")
def get_report(path: str):
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(str(p), media_type="application/pdf", filename=p.name)
