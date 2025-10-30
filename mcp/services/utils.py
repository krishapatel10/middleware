from typing import Optional, Any

def _normalize(value: any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        up = s.upper()
        if up in {"N/A", "NA", "NONE", "NULL", ""}:
            return None
        # numeric-like string -> number
        if s.replace(".", "", 1).lstrip("-").isdigit():
            return float(s) if "." in s else int(s)
        return s
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(x) for x in value]
    return value