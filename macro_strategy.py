# strategies/macro_strategy.py
# Essential Eight – Macro Settings (ML1-OM-01 .. ML1-OM-07)
# Fuzzy-friendly detection: partial/case-insensitive matching, token coverage,
# and tolerant number parsing for registry/GPO exports.

from __future__ import annotations
import re
from pathlib import Path
from typing import List, Dict

# -------------------------
# Helpers
# -------------------------

def _norm(s: str) -> str:
    s = (s or "").lower()
    # collapse whitespace, remove some punctuation that OCR often mangles
    s = re.sub(r"[^\w\s:/\-\.]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _token_set(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", _norm(text)))

def _word_coverage(text: str, phrase: str, threshold: float = 0.6) -> bool:
    """
    Rough fuzzy: a phrase 'matches' if at least `threshold` of its words
    are present as tokens in the text (order not required).
    """
    tset = _token_set(text)
    words = re.findall(r"[a-z0-9]+", _norm(phrase))
    if not words:
        return False
    hits = sum(1 for w in words if w in tset)
    return (hits / len(words)) >= threshold

def _any_fuzzy(text: str, phrases: List[str], threshold: float = 0.6) -> bool:
    t = _norm(text)
    for p in phrases:
        p_norm = _norm(p)
        if p_norm in t:
            return True
        if _word_coverage(t, p_norm, threshold):
            return True
    return False

def _int_after(token: str, text: str):
    """
    Find an integer that appears after token (tolerant to separators/whitespace).
    Accepts decimal or hex (0x..). Returns int or None.
    """
    t = _norm(text)
    # allow token broken by spaces or punctuation
    token_re = re.sub(r"\s+", r"\\s*", re.escape(token.lower()))
    m = re.search(rf"{token_re}[^0-9a-fx]*((?:0x)?[0-9a-f]+)", t, flags=re.I)
    if not m:
        return None
    try:
        return int(m.group(1), 0)
    except Exception:
        return None

# -------------------------
# Phrases we look for
# -------------------------

BANNER_PHRASES = [
    "microsoft has blocked macros",
    "macros from the internet have been disabled",
    "security risk: macros have been blocked",
    "this file came from the internet",
    "mark of the web",
]

LOCK_PHRASES = [
    "managed by your organization",
    "some settings are managed by your organization",
    "trust center settings are disabled",
    "these settings are enforced by your administrator",
]

DISABLE_NO_NOTIFY_PHRASES = [
    "disable all macros without notification",
    "disable without notification",
    "vba macros disabled without notification",
]

AV_HIT_PHRASES = [
    "eicar",
    "threat found",
    "quarantined",
    "blocked",
    "virus detected",
    "malware detected",
]

# -------------------------
# Strategy
# -------------------------

class MacroStrategy:
    name = "Configure Microsoft Office Macro Settings"

    def __init__(self):
        self._om02_emitted = False

    def description(self) -> str:
        return "Checks Essential Eight Macro Settings (ML1-OM-01 → ML1-OM-07) with fuzzy OCR matching"

    def emit_hits(self, text: str) -> List[Dict]:
        text_l = _norm(text)
        rows: List[Dict] = []

        # 01: Macros disabled for unapproved users
        vbaw = _int_after("vbawarnings", text_l)
        if vbaw == 3 or _any_fuzzy(text_l, DISABLE_NO_NOTIFY_PHRASES, 0.6):
            rows.append(self._row(
                "ML1-OM-01", "Disable macros (unapproved users)", "ML1",
                "PASS", "High",
                "Macros disabled for unapproved users (Disable without notification / VBAWarnings=3).",
                [f"VBAWarnings={vbaw}" if vbaw is not None else "Disable without notification (fuzzy)"]
            ))
        else:
            rows.append(self._row(
                "ML1-OM-01", "Disable macros (unapproved users)", "ML1",
                "FAIL", "High",
                "Apply GPO: 'Disable without notification' or set VBAWarnings=3.",
                []
            ))

        # 03: MoTW banner / Internet macros blocked
        if _any_fuzzy(text_l, BANNER_PHRASES, 0.55):
            rows.append(self._row(
                "ML1-OM-03", "Block macros from Internet (MoTW)", "ML1",
                "PASS", "High",
                "Banner or equivalent wording detected that macros from the Internet are blocked.",
                ["MoTW/banner phrase present (fuzzy)"]
            ))
        else:
            rows.append(self._row(
                "ML1-OM-03", "Block macros from Internet (MoTW)", "ML1",
                "FAIL", "High",
                "Enable GPO to block macros in Office files from the Internet for all Office apps.",
                []
            ))

        # 04: Registry/GPO enforce Internet block
        bcei = _int_after("blockcontentexecutionfrominternet", text_l)
        if bcei == 1:
            rows.append(self._row(
                "ML1-OM-04", "Registry: blockcontentexecutionfromInternet", "ML1",
                "PASS", "High",
                "blockcontentexecutionfromInternet=1 detected.",
                [f"blockcontentexecutionfromInternet={bcei}"]
            ))
        else:
            rows.append(self._row(
                "ML1-OM-04", "Registry: blockcontentexecutionfromInternet", "ML1",
                "FAIL", "High",
                "Set blockcontentexecutionfromInternet=1 (Word/Excel/PowerPoint).",
                []
            ))

        # 05: Macro runtime scan scope
        mrs = _int_after("macroruntimescope", text_l)
        if mrs in (1, 2):
            rows.append(self._row(
                "ML1-OM-05", "Macro runtime scanning", "ML1",
                "PASS", "Medium",
                "Macro Runtime Scan Scope is enabled.",
                [f"macroruntimescope={mrs}"]
            ))
        else:
            rows.append(self._row(
                "ML1-OM-05", "Macro runtime scanning", "ML1",
                "FAIL", "Medium",
                "Enable Macro Runtime Scan Scope (1 or 2) via policy.",
                []
            ))

        # 06: AV detects macro/EICAR
        if _any_fuzzy(text_l, AV_HIT_PHRASES, 0.6):
            rows.append(self._row(
                "ML1-OM-06", "AV detects macro payload", "ML1",
                "PASS", "High",
                "AV alert/log contains EICAR/Threat/Quarantined keywords.",
                ["AV log keywords present (fuzzy)"]
            ))
        else:
            rows.append(self._row(
                "ML1-OM-06", "AV detects macro payload", "ML1",
                "FAIL", "High",
                "Validate AV with an EICAR macro test in a safe environment.",
                []
            ))

        # 07: Users cannot change settings (locked)
        if _any_fuzzy(text_l, LOCK_PHRASES, 0.6):
            rows.append(self._row(
                "ML1-OM-07", "Prevent user changes (locked Trust Center)", "ML1",
                "PASS", "Medium",
                "Trust Center shows settings managed/enforced by organization.",
                ["Lock/managed phrase present (fuzzy)"]
            ))
        else:
            rows.append(self._row(
                "ML1-OM-07", "Prevent user changes (locked Trust Center)", "ML1",
                "FAIL", "Medium",
                "Lock macro policies via GPO so users cannot modify Trust Center settings.",
                []
            ))

        # 02: Approved users list matches AD group (emit once per run)
        if not self._om02_emitted:
            row = self._om02_compare_once()
            if row:
                rows.append(row)
                self._om02_emitted = True

        return rows

    # ------------- OM-02 compare -------------
    def _om02_compare_once(self):
        paths = [Path("approved_users.txt"), Path("screenshots/approved_users.txt")]
        ap = next((p for p in paths if p.exists()), None)

        paths = [Path("ad_group.txt"), Path("screenshots/ad_group.txt")]
        ag = next((p for p in paths if p.exists()), None)

        if not ap or not ag:
            return self._row(
                "ML1-OM-02", "Approved users match AD group", "ML1",
                "INSUFFICIENT", "Medium",
                "Need approved_users.txt and ad_group.txt to compare membership.",
                []
            )

        aproved_text = ap.read_text(errors="ignore")
        adgroup_text = ag.read_text(errors="ignore")

        capture = r"[a-z0-9._-]+@[a-z0-9.-]+|[a-z0-9._-]+"
        set_approved = set(re.findall(capture, aproved_text, flags=re.I))
        set_adgroup  = set(re.findall(capture, adgroup_text, flags=re.I))

        missing_in_ad = sorted(set_approved - set_adgroup)
        extra_in_ad   = sorted(set_adgroup - set_approved)

        if not missing_in_ad and not extra_in_ad:
            return self._row(
                "ML1-OM-02", "Approved users match AD group", "ML1",
                "PASS", "Medium",
                "Approved users list equals AD group membership.",
                [f"Count={len(set_approved)}"]
            )

        return self._row(
            "ML1-OM-02", "Approved users match AD group", "ML1",
            "FAIL", "Medium",
            "Mismatch between approved list and AD group.",
            [f"MissingInAD={missing_in_ad or 'None'}", f"ExtraInAD={extra_in_ad or 'None'}"]
        )

    # ------------- CSV row factory -------------
    @staticmethod
    def _row(test_id, sub, level, pf, prio, rec, evidence: List[str]):
        return {
            "test_id": test_id,
            "sub_strategy": sub,
            "detected_level": level,
            "pass_fail": pf,
            "priority": prio,
            "recommendation": rec,
            "evidence": evidence or [],
        }

# factory used by strategies loader
def get_strategy():
    return MacroStrategy()
