# strategies/macro_strategy.py
import re
from pathlib import Path

class MacroStrategy:
    name = "Configure Microsoft Office Macro Settings"

    def description(self):
        return "Detects whether Microsoft Office macro settings are properly enforced."

    def emit_hits(self, text):
        t = self._norm(text)
        rows = []
        rows.append(self._om01(t))
        rows.append(self._om02())
        rows.append(self._om03(t))
        rows.append(self._om04(t))
        rows.append(self._om05(t))
        rows.append(self._om06(t))
        rows.append(self._om07(t))
        return rows

    def match(self, _text):
        return []

    # ------------------- RULES -------------------

    def _om01(self, t):
        vbaw = self._int_after("vbawarnings", t)
        pass_hit = (vbaw == 3) or ("disable all macros without notification" in t)
        return self._row(
            "ML1-OM-01",
            "Disable macros for unapproved users",
            "ML1",
            "PASS" if pass_hit else "FAIL",
            "High",
            "Set 'Disable all macros without notification' (VBAWarnings=3).",
            [f"VBAWarnings={vbaw}"] if vbaw is not None else []
        )

    def _om02(self):
        ap = Path("approved_users.txt")
        ag = Path("ad_group.txt")
        if not ap.exists() or not ag.exists():
            return self._row(
                "ML1-OM-02",
                "Approved list matches AD group",
                "ML1",
                "INSUFFICIENT",
                "Medium",
                "Provide approved_users.txt and ad_group.txt.",
                []
            )
        s1 = set(re.findall(r"[a-z0-9._-]+", ap.read_text().lower()))
        s2 = set(re.findall(r"[a-z0-9._-]+", ag.read_text().lower()))
        return self._row(
            "ML1-OM-02",
            "Approved list matches AD group",
            "ML1",
            "PASS" if s1 == s2 else "FAIL",
            "Medium",
            "Compare approved_users.txt with ad_group.txt.",
            [f"MissingInAD={sorted(s1 - s2)}", f"ExtraInAD={sorted(s2 - s1)}"]
        )

    def _om03(self, t):
        pass_hit = "macros from the internet have been disabled" in t or "mark of the web" in t
        return self._row(
            "ML1-OM-03",
            "Block macros in Internet-sourced files",
            "ML1",
            "PASS" if pass_hit else "FAIL",
            "High",
            "Ensure macros from Internet (MoTW) are blocked.",
            ["MoTW detected"] if pass_hit else []
        )

    def _om04(self, t):
        val = self._int_after("blockcontentexecutionfrominternet", t)
        return self._row(
            "ML1-OM-04",
            "Enforce GPO to block Internet macros",
            "ML1",
            "PASS" if val == 1 else "FAIL",
            "High",
            "Set BlockContentExecutionFromInternet=1 in registry/GPO.",
            [f"blockcontentexecutionfrominternet={val}"] if val is not None else []
        )

    def _om05(self, t):
        mrs = self._int_after("macroruntimescope", t)
        pass_hit = mrs in (1, 2) or "runtime scan scope" in t
        return self._row(
            "ML1-OM-05",
            "Enable Macro Runtime Scanning",
            "ML1",
            "PASS" if pass_hit else "FAIL",
            "Medium",
            "Enable Macro Runtime Scan Scope (1 or 2).",
            [f"macroruntimescope={mrs}"] if mrs is not None else []
        )

    def _om06(self, t):
        pass_hit = any(k in t for k in ["eicar", "threat found", "quarantined", "virus detected"])
        return self._row(
            "ML1-OM-06",
            "AV detects malicious macro payload",
            "ML1",
            "PASS" if pass_hit else "FAIL",
            "High",
            "Validate endpoint AV detects malicious macros.",
            ["Threat keyword present"] if pass_hit else []
        )

    def _om07(self, t):
        pass_hit = any(k in t for k in [
            "managed by your organization",
            "trust center settings are disabled",
            "prevent user changes"
        ])
        return self._row(
            "ML1-OM-07",
            "Prevent user changes to macro settings",
            "ML1",
            "PASS" if pass_hit else "FAIL",
            "Medium",
            "Enforce GPO to lock macro settings.",
            ["User change blocked"] if pass_hit else []
        )

    # ------------------- HELPERS -------------------

    def _norm(self, s):
        return re.sub(r"\s+", " ", (s or "").lower()).strip()

    def _int_after(self, token, text):
        """Finds integer values after a registry key name (like vbawarnings=3)."""
        pattern = r"%s\s*[:=]?\s*((?:0x)?[0-9a-f]+)" % re.escape(token.lower())
        m = re.search(pattern, text, flags=re.I)
        if not m:
            return None
        try:
            return int(m.group(1), 0)
        except Exception:
            return None

    def _row(self, test_id, sub, level, pf, prio, rec, evidence):
        return {
            "test_id": test_id,
            "sub_strategy": sub,
            "detected_level": level,
            "pass_fail": pf,
            "priority": prio,
            "recommendation": rec,
            "evidence": evidence,
        }

def get_strategy():
    return MacroStrategy()
