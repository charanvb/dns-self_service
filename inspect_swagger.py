import json

path = "swagger_JSON_for_micetro_QA.json"
out_path = "swagger_extract2.txt"

with open(path, "r", encoding="utf-8") as f:
    raw = f.read()

try:
    spec = json.loads(raw)
except Exception as e:
    spec = {}
    raw_json_error = str(e)
else:
    raw_json_error = None

lines = []

def get_path(d, keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None, False
    return cur, True

def add_section(title, keys):
    lines.append(f"=== {title} ===")
    if raw_json_error:
        lines.append(f"NOT FOUND: {title} (JSON parse error: {raw_json_error})")
        return
    val, found = get_path(spec, keys)
    if not found:
        lines.append(f"NOT FOUND: {'.'.join(keys)}")
    else:
        lines.append(json.dumps(val, indent=2))
    lines.append("")

sections = [
    ("components.schemas.GetDNSZonesResponse", ["components","schemas","GetDNSZonesResponse"]),
    ("components.schemas.GetDNSRecordsResponse", ["components","schemas","GetDNSRecordsResponse"]),
    ("components.parameters.filterParam", ["components","parameters","filterParam"]),
    ("components.parameters.offsetParam", ["components","parameters","offsetParam"]),
    ("components.parameters.limitParam", ["components","parameters","limitParam"]),
    ("components.parameters.sortByParam", ["components","parameters","sortByParam"]),
    ("components.parameters.sortOrderParam", ["components","parameters","sortOrderParam"]),
    ("components.parameters.objTypeParam", ["components","parameters","objTypeParam"]),
    ("components.schemas.ObjRef", ["components","schemas","ObjRef"]),
    ("components.schemas.DNSRecordType", ["components","schemas","DNSRecordType"]),
    ("components.schemas.DNSZoneType", ["components","schemas","DNSZoneType"]),
    ("components.schemas.AddDNSRecord", ["components","schemas","AddDNSRecord"]),
    ("components.schemas.AddDNSRecords", ["components","schemas","AddDNSRecords"]),
    ("components.schemas.AddDNSZone", ["components","schemas","AddDNSZone"]),
    ("components.schemas.SetProperties", ["components","schemas","SetProperties"]),
]

for title, keys in sections:
    add_section(title, keys)
    if title in ("components.schemas.DNSRecordType", "components.schemas.DNSZoneType"):
        val, found = get_path(spec, keys)
        if found and isinstance(val, dict) and "enum" in val:
            lines.append(f"--- {title} full enum values ---")
            lines.append(json.dumps(val["enum"], indent=2))
            lines.append("")

# Auth mechanism investigation
lines.append("=== auth mechanism investigation ===")

if not raw_json_error:
    sec_schemes, found = get_path(spec, ["components","securitySchemes"])
    if found:
        lines.append("components.securitySchemes:")
        lines.append(json.dumps(sec_schemes, indent=2))
    else:
        lines.append("NOT FOUND: components.securitySchemes")
else:
    lines.append(f"NOT FOUND: components.securitySchemes (JSON parse error: {raw_json_error})")

lines.append("")

for term in ["basic", "Authorization", "securitySchemes"]:
    lower_raw = raw.lower()
    lower_term = term.lower()
    count = lower_raw.count(lower_term)
    lines.append(f"Occurrences of '{term}' (case-insensitive): {count}")

lines.append("")
lines.append("--- Context snippets around 'basic' (case-insensitive) ---")

lower_raw = raw.lower()
term = "basic"
start = 0
occurrence_idx = 0
while True:
    idx = lower_raw.find(term, start)
    if idx == -1:
        break
    occurrence_idx += 1
    ctx_start = max(0, idx - 250)
    ctx_end = min(len(raw), idx + 250)
    snippet = raw[ctx_start:ctx_end]
    lines.append(f"[Occurrence {occurrence_idx} at index {idx}]:")
    lines.append(snippet)
    lines.append("")
    start = idx + len(term)

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("DONE")
