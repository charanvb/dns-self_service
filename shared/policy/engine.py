from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from shared.models.policies import DnsPolicy, PolicyRule
from shared.models.zones import DnsZone


@dataclass
class PolicyResult:
    allowed: bool = True
    requires_approval: bool = False
    reasons: list[str] = field(default_factory=list)
    matched_policies: list[str] = field(default_factory=list)

    def merge(self, other: "PolicyResult") -> None:
        if not other.allowed:
            self.allowed = False
        if other.requires_approval:
            self.requires_approval = True
        for reason in other.reasons:
            if reason not in self.reasons:
                self.reasons.append(reason)
        for policy in other.matched_policies:
            if policy not in self.matched_policies:
                self.matched_policies.append(policy)


class PolicyEngine:
    """Centralized, DB-driven policy evaluation — business rules live in
    dns_policies/policy_rules, manageable by CLOUDOPS_ADMIN, instead of being
    scattered as hard-coded checks across endpoints."""

    def __init__(self, session: Session):
        self.session = session

    def _active_rules(self) -> list[PolicyRule]:
        return (
            self.session.query(PolicyRule)
            .join(DnsPolicy)
            .filter(DnsPolicy.is_active.is_(True), PolicyRule.is_active.is_(True))
            .all()
        )

    def evaluate_item(self, zone: DnsZone, action: str, record_type: str, fqdn: str) -> PolicyResult:
        result = PolicyResult()

        if zone.requires_approval:
            result.requires_approval = True
            result.matched_policies.append("zone_requires_approval")
            result.reasons.append(f"Zone '{zone.zone_name}' requires Zone Admin approval for all requests.")

        for rule in self._active_rules():
            if rule.rule_type == "restricted_record_type":
                types = set(rule.config.get("record_types", []))
                if record_type in types:
                    policy_name = rule.policy.name
                    if rule.config.get("action", "REQUIRE_APPROVAL") == "REJECT":
                        result.allowed = False
                        result.reasons.append(
                            f"Record type {record_type} is restricted by policy '{policy_name}'."
                        )
                    else:
                        result.requires_approval = True
                        result.reasons.append(
                            f"Record type {record_type} requires approval per policy '{policy_name}'."
                        )
                    result.matched_policies.append(policy_name)

        return result

    def evaluate_request(self, zone: DnsZone, items) -> PolicyResult:
        """Aggregates per-item results across the whole request — if ANY item
        is disallowed, the whole request is rejected; if ANY item requires
        approval, the whole request needs approval."""
        aggregate = PolicyResult()
        for item in items:
            aggregate.merge(self.evaluate_item(zone, item.action, item.record_type, item.fqdn))
        return aggregate
