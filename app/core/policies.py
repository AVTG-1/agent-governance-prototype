"""Policy as readable data: capabilities, rules (id + version), grants, delegation, envelopes.

Nothing in this file decides anything; policy_engine.py does. A PolicySet is changed only by
`PolicySet.with_changes()` (which returns a copy) and the owner-approval step that swaps it in.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

# --- Capabilities ------------------------------------------------------------------------

@dataclass(frozen=True)
class Capability:
    system: str
    op: str            # read | write | egress | control
    meaning: str


CAPABILITIES: dict[str, Capability] = {
    "trade.read": Capability("trade", "read", "Read trades"),
    "settlement.read": Capability("settlement", "read", "Read settlement status"),
    "settlement.update": Capability("settlement", "write", "Update settlement status"),
    "ssi.amend": Capability("settlement", "write", "Amend settlement instructions (always maker-checker)"),
    "client.read_masked": Capability("client", "read", "Read client record, PII masked"),
    "client.read_pii": Capability("client", "read", "Read tax ID, email, date of birth"),
    "refdata.read": Capability("refdata", "read", "Read reference data"),
    "ledger.read_quarter_end": Capability("ledger", "read", "Read quarter-end ledger balances (rare but required)"),
    "recon.update": Capability("recon", "write", "Update a break in the agent's own reconciliation system"),
    "fx.read": Capability("fx", "read", "Read FX positions"),
    "fileshare.export": Capability("fileshare", "write", "Export to the shared file drive"),
    "external.post": Capability("external", "egress", "Send data outside the firm (never with restricted data)"),
    # Control-plane capabilities. No agent may ever hold these (R-SELF-01).
    "policy.update": Capability("policy", "control", "Change policy or grants"),
    "policy.approve": Capability("policy", "control", "Approve a policy change"),
}
CONTROL_PLANE = frozenset(c for c, cap in CAPABILITIES.items() if cap.op == "control")
CLIENT_DATA = frozenset({"client.read_masked", "client.read_pii"})
PII_FIELDS = frozenset({"tax_id", "email", "dob"})
RESTRICTED = "restricted-pii"

# What each kind of task legitimately needs. Used for the delegation intersection (R-DLG-02).
TASK_NEEDS: dict[str, frozenset[str]] = {
    "reconciliation": frozenset({"trade.read", "settlement.read", "client.read_masked", "refdata.read",
                                 "recon.update", "ledger.read_quarter_end"}),
    "quarter-end close": frozenset({"ledger.read_quarter_end", "trade.read"}),
    "ssi_verification": frozenset({"settlement.read", "client.read_pii", "ssi.amend", "trade.read"}),
    "settlement": frozenset({"trade.read", "settlement.read", "settlement.update", "ssi.amend", "client.read_masked"}),
    "enrichment": frozenset({"trade.read", "refdata.read", "settlement.read"}),
    "kyc_refresh": frozenset({"client.read_masked", "refdata.read"}),
}

# --- Rules -------------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    id: str
    version: int
    summary: str
    hard: bool = False     # hard rules have no override of any kind

    @property
    def ref(self) -> str:
        return f"{self.id}@v{self.version}"


RULES: dict[str, Rule] = {r.id: r for r in [
    Rule("R-DEF-00", 1, "Default deny: anything not explicitly allowed is refused."),
    Rule("R-ID-01", 1, "Caller must be a registered agent with a live, audience-bound credential.", hard=True),
    Rule("R-SELF-01", 1, "No agent may change policy or its own grants.", hard=True),
    Rule("R-VOL-01", 1, "Volume above 10x baseline in 60 s quarantines the agent."),
    Rule("R-CNT-01", 1, "A contained session may only do what its containment allows."),
    Rule("R-EGR-01", 2, "Restricted data never leaves the firm. No override exists.", hard=True),
    Rule("R-DLG-02", 1, "Delegated calls get caller ∩ callee ∩ task ∩ policy; depth ≤ 2."),
    Rule("R-PII-01", 3, "Restricted PII needs a purpose-bound grant; never on untrusted content."),
    Rule("R-JIT-01", 1, "Just-in-time access only within a live, matching envelope."),
    Rule("R-SSI-01", 1, "SSI amendments are held for a second person (maker-checker)."),
    Rule("R-GRANT-01", 2, "Allowed: the capability is a standing grant and nothing else denies it."),
]}

# --- Grants, delegation, envelopes ---------------------------------------------------------

RARE_BUT_REQUIRED = "rare-but-required"


@dataclass(frozen=True)
class Grant:
    capability: str
    fields: frozenset[str] | None = None      # allowed fields; None = any non-restricted field
    purpose: str | None = None                # purpose-bound grant (needed for PII)
    tags: tuple[str, ...] = ()                # e.g. ("rare-but-required", "quarter-end close")
    conditions: tuple[tuple[str, object], ...] = ()   # narrowing conditions added by approved diffs

    @property
    def protected_reason(self) -> str | None:
        if RARE_BUT_REQUIRED in self.tags:
            why = [t for t in self.tags if t != RARE_BUT_REQUIRED]
            return f"required at {why[0]}" if why else "rare but required"
        return None


@dataclass
class AgentPolicy:
    agent: str
    version: int
    grants: dict[str, Grant]
    # caller -> callee -> capabilities the caller may NOT delegate to that callee
    delegate_to: dict[str, frozenset[str]] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.agent}-policy@v{self.version}"


@dataclass(frozen=True)
class EnvelopeDef:
    id: str
    agent: str
    capability: str
    system: str
    fields: frozenset[str]
    max_rows: int
    ttl_s: int
    op: str = "read"
    purpose: str = "reconciliation"


@dataclass
class PolicySet:
    agents: dict[str, AgentPolicy]
    envelopes: dict[str, EnvelopeDef]
    envelope_human_days: dict[str, int] = field(default_factory=dict)   # envelope -> days a person must approve

    def grants_of(self, agent: str) -> dict[str, Grant]:
        p = self.agents.get(agent)
        return p.grants if p else {}

    def capabilities_of(self, agent: str) -> frozenset[str]:
        return frozenset(self.grants_of(agent))

    def version_label(self, agent: str = "recon-agent") -> str:
        return self.agents[agent].label

    def with_changes(self, changes: list[dict], bump: bool = True) -> "PolicySet":
        """Return a copy with verified, normalised narrowing changes applied (see verifier.py)."""
        new = copy.deepcopy(self)
        touched: set[str] = set()
        for ch in changes:
            kind, agent = ch["kind"], ch["agent"]
            ap = new.agents[agent]
            touched.add(agent)
            if kind == "remove_grant":
                ap.grants.pop(ch["capability"], None)
            elif kind == "restrict_delegation":
                callees = list(ap.delegate_to) if ch["callee"] == "*" else [ch["callee"]]
                for callee in callees:
                    if callee not in ap.delegate_to:
                        continue
                    if ch["capabilities"] is None:
                        del ap.delegate_to[callee]
                    else:
                        ap.delegate_to[callee] = ap.delegate_to[callee] | frozenset(ch["capabilities"])
            elif kind == "require_human_for_envelope":
                new.envelope_human_days[ch["envelope"]] = int(ch["days"])
            elif kind == "add_condition":
                g = ap.grants[ch["capability"]]
                ap.grants[ch["capability"]] = Grant(g.capability, g.fields, g.purpose, g.tags,
                                                    g.conditions + ((ch["condition"], ch["value"]),))
            else:
                raise ValueError(f"not a narrowing change: {kind}")
        if bump:
            for agent in touched:
                new.agents[agent].version += 1
        return new


# --- The Kaiyo Securities policy, as it stands at each point of the story ------------------

MASKED_PROFILE = frozenset({"client_id", "name", "country", "client_type"})
QUARTER_END = (RARE_BUT_REQUIRED, "quarter-end close")

ENVELOPES = {
    "env-recon-cm-01": EnvelopeDef(
        id="env-recon-cm-01", agent="recon-agent", capability="client.read_masked", system="client",
        fields=frozenset({"client_id", "legal_entity_id", "country"}), max_rows=1, ttl_s=120,
    ),
}


def _g(cap: str, **kw) -> tuple[str, Grant]:
    return cap, Grant(cap, **kw)


def initial_policy() -> PolicySet:
    """recon-agent-policy@v3: what the shared account could do, as first observed (before baselining)."""
    recon = AgentPolicy("recon-agent", 3, dict([
        _g("trade.read"), _g("settlement.read"), _g("client.read_masked", fields=MASKED_PROFILE),
        _g("recon.update"),
        # legacy grants, unused in 90 days
        _g("settlement.update"), _g("fx.read"), _g("fileshare.export"),
    ]), delegate_to={"settlement-agent": frozenset()})
    settlement = AgentPolicy("settlement-agent", 2, dict([
        _g("trade.read"), _g("settlement.read"), _g("settlement.update"), _g("ssi.amend"),
        _g("client.read_masked", fields=MASKED_PROFILE),
        _g("client.read_pii", purpose="ssi_verification", fields=frozenset({"client_id", "tax_id", "email", "dob", "name"})),
    ]))
    enrichment = AgentPolicy("enrichment-agent", 1, dict([_g("trade.read"), _g("refdata.read"), _g("settlement.read")]))
    kyc = AgentPolicy("kyc-agent", 1, dict([_g("client.read_masked", fields=MASKED_PROFILE), _g("refdata.read")]))
    investigator = AgentPolicy("investigator", 1, {})   # advises only: no capabilities on any system
    return PolicySet(
        agents={p.agent: p for p in (recon, settlement, enrichment, kyc, investigator)},
        envelopes=dict(ENVELOPES),
    )


def baseline_policy(policy: PolicySet | None = None) -> PolicySet:
    """recon-agent-policy@v4: the shadow week added one missing permission and one protected rare flow."""
    p = copy.deepcopy(policy or initial_policy())
    recon = p.agents["recon-agent"]
    recon.grants["refdata.read"] = Grant("refdata.read")
    recon.grants["ledger.read_quarter_end"] = Grant("ledger.read_quarter_end", tags=QUARTER_END)
    recon.version = 4
    return p


class PolicyStore:
    """Holds the live policy. Only `adopt` (baselining, Act 2) and `approve` (owner, Act 5) change it."""

    def __init__(self, policy: PolicySet) -> None:
        self.current = policy
        self.history: list[dict] = [{"label": policy.version_label(), "note": "initial, as observed"}]

    def adopt(self, policy: PolicySet, note: str) -> None:
        self.current = policy
        self.history.append({"label": policy.version_label(), "note": note})

    def approve(self, candidate: PolicySet, owner: str, how: str) -> tuple[str, str]:
        """The approval step: a named person (or the demo's labelled auto-approval) swaps the policy in."""
        if not owner:
            raise PermissionError("a policy change needs an owner's approval")
        before = self.current.version_label()
        self.current = candidate
        after = candidate.version_label()
        self.history.append({"label": after, "note": f"approved by {owner} ({how})"})
        return before, after
