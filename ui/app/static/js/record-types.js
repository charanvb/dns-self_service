// Shared between request_new.html (wizard) and request_detail.html (view) so
// record-type field labels stay in sync in exactly one place.
const FIELD_DEFS = {
  A: [{ name: "ipv4", label: "IPv4 Address", placeholder: "10.10.10.10" }],
  AAAA: [{ name: "ipv6", label: "IPv6 Address", placeholder: "2001:db8::1" }],
  CNAME: [{ name: "target", label: "Target (FQDN)", placeholder: "backend.example.com" }],
  TXT: [{ name: "text", label: "TXT Value", placeholder: '"v=spf1 include:example.com -all"', textarea: true }],
  MX: [
    { name: "priority", label: "Priority", placeholder: "10" },
    { name: "target", label: "Mail Server (FQDN)", placeholder: "mail.example.com" },
  ],
};
const RECORD_TYPES = Object.keys(FIELD_DEFS);

function fieldLabel(recordType, fieldName) {
  const def = (FIELD_DEFS[recordType] || []).find((f) => f.name === fieldName);
  return def ? def.label : fieldName;
}
