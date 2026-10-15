"""Discovery, registry and credentials.  (SPIFFE/SPIRE and a secrets broker in production.)

Discovery correlates estate signals (vault entries, gateway logs, database sessions, cloud
roles, config scans) into one registry entry per agent, and flags what needs fixing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

NAMES = {
    "recon-agent": "Reconciliation agent",
    "settlement-agent": "Settlement agent",
    "enrichment-agent": "Trade enrichment agent",
    "kyc-agent": "KYC refresh agent",
    "investigator": "AI investigator",
}
# Most sensitive system first: an unowned agent is assigned to the owner of the most sensitive system it touches.
SENSITIVITY = ["client", "settlement", "ledger", "recon", "trade", "refdata"]


@dataclass
class Credential:
    kind: str                  # shared | db-login | cloud-role | static-key | brokered | token | federated | proxied | none
    principal: str
    audience: list[str] = field(default_factory=lambda: ["*"])
    ttl_s: int | None = None
    expired: bool = False

    @property
    def label(self) -> str:
        return {
            "shared": f"Shared service account {self.principal}",
            "db-login": f"Direct database login {self.principal.removeprefix('db:')}",
            "cloud-role": f"Cloud IAM role {self.principal}",
            "static-key": "Static API key in a config file",
            "per-agent": "Per-agent credential",
            "brokered": f"Own identity, {self.ttl_s // 60}-minute brokered credential" if self.ttl_s else "Own identity",
            "token": f"Short-lived token from the broker ({self.ttl_s // 60} min)" if self.ttl_s else "Short-lived token",
            "federated": "Federated agent identity",
            "proxied": f"Database login behind the data proxy",
            "none": "No system credential",
        }[self.kind]


@dataclass
class AgentIdentity:
    id: str
    name: str
    owner: str | None
    credential: Credential
    systems: list[str]
    flags: list[str] = field(default_factory=list)
    extra_logins: list[str] = field(default_factory=list)
    owner_source: str = "discovered"
    status: str = "discovered"          # discovered | wrapped | governable | advisory
    attribution: str = "agent"          # agent | workload | none
    purpose: str = "routine"

    def row(self) -> dict:
        return {
            "id": self.id, "name": self.name, "owner": self.owner, "owner_source": self.owner_source,
            "credential": self.credential.label, "credential_kind": self.credential.kind,
            "systems": self.systems, "flags": self.flags, "status": self.status,
            "attribution": self.attribution,
        }


ONBOARDING = {   # connection style before -> what changes (wording from the deck), never the agent's code
    "shared": {"kind": "brokered", "ttl_s": 600, "retires": True, "attaches": ["credential", "path"],
               "swap": "One identity per agent; the shared account is retired",
               "path": "Calls go through the agent gateway", "data": "Unchanged",
               "attribution": "agent", "attribution_text": "Per agent"},
    "static-key": {"kind": "token", "ttl_s": 900, "retires": True, "attaches": ["credential", "path"],
                   "swap": "Key swapped for a short-lived token from the broker",
                   "path": "Calls go through the agent gateway", "data": "Unchanged",
                   "attribution": "agent", "attribution_text": "Per agent"},
    "cloud-role": {"kind": "federated", "ttl_s": None, "retires": False, "attaches": ["credential", "path"],
                   "swap": "Role federated to a registered agent identity",
                   "path": "Egress limited to the agent gateway", "data": "Unchanged",
                   "attribution": "workload", "attribution_text": "Per workload (agents sharing a runtime look like one)"},
    "db-login": {"kind": "proxied", "ttl_s": None, "retires": False, "attaches": ["path", "data"],
                 "swap": "Credential unchanged",
                 "path": "Connection moved behind a data proxy",
                 "data": "Row and column rules applied at the proxy",
                 "attribution": "db-login", "attribution_text": "Per database login"},
}

PURPOSES = {"recon-agent": "reconciliation", "settlement-agent": "settlement",
            "enrichment-agent": "enrichment", "kyc-agent": "kyc_refresh"}


def discover(signals: dict) -> list[AgentIdentity]:
    """Correlate raw estate signals into agents. Deterministic; no AI involved."""
    vault = {v["principal"]: v for v in signals["vault_entries"]}
    roles = {r["role"]: r for r in signals["cloud_roles"]}
    configs = {c["principal"]: c for c in signals["config_files"]}
    agents = []
    for log in signals["gateway_logs"]:
        workload = log["user_agent"].split("/")[0]
        principal = log["principal"]
        flags, owner, kind = [], None, "per-agent"
        if principal in vault:
            owner = vault[principal]["owner"]
            kind = {"shared service account": "shared", "database login": "db-login"}.get(vault[principal]["kind"], "per-agent")
        elif principal in roles:
            owner, kind = roles[principal]["owner"], "cloud-role"
        elif principal in configs:
            owner, kind = configs[principal]["owner"], "static-key"
            flags.append("static API key in a config file")
        sessions = [s for s in signals["db_sessions"] if s["login"] == principal]
        humans = [s for s in sessions if s["interactive"]]
        attribution = "agent"
        if humans:
            flags.append("shared with a person: actions not attributable")
            attribution = "none"
        extra = sorted({s["login"] for s in signals["db_sessions"]
                        if s["program"] == workload and s["login"] != principal})
        systems = list(log["systems"])
        if extra:
            flags.append(f"direct database login {extra[0]}")
        if kind == "db-login":
            flags.append("direct database login: no gateway in the path")
        if owner is None:
            flags.insert(0, "no owner")
        agents.append(AgentIdentity(
            id=workload, name=NAMES.get(workload, workload), owner=owner,
            credential=Credential(kind, principal), systems=systems, flags=flags, extra_logins=extra,
            attribution=attribution, purpose=PURPOSES.get(workload, "routine"),
            status="discovered",
        ))
    return agents


def assign_owner(agent: AgentIdentity, system_owners: dict[str, str]) -> str:
    """Rule: an unowned agent belongs to the owner of the most sensitive system it touches."""
    for system in SENSITIVITY:
        if system in agent.systems:
            agent.owner = system_owners[system]
            agent.owner_source = "assigned"
            agent.flags = [f for f in agent.flags if f != "no owner"] + ["owner assigned"]
            return agent.owner
    raise ValueError(f"cannot assign an owner to {agent.id}")


class Registry:
    def __init__(self) -> None:
        self.agents: dict[str, AgentIdentity] = {}

    def add(self, agent: AgentIdentity) -> None:
        self.agents[agent.id] = agent

    def get(self, agent_id: str) -> AgentIdentity | None:
        return self.agents.get(agent_id)

    def add_investigator(self) -> None:
        self.add(AgentIdentity("investigator", NAMES["investigator"], "Governance", Credential("none", "—", []),
                               [], status="advisory", attribution="agent", purpose="investigation"))

    def onboard(self, agent_id: str) -> dict:
        """Mediate, don't modify: swap what surrounds the agent (credential, path, data), never its code.
        The wording per connection style is the deck's ("Agents we can't see inside")."""
        a = self.agents[agent_id]
        before = a.credential
        spec = ONBOARDING[before.kind]
        principal = f"spiffe://kaiyo.example/agent/{agent_id}" if spec["kind"] != "proxied" else before.principal
        a.credential = Credential(spec["kind"], principal, ["*"], spec["ttl_s"])
        a.status = "onboarded"
        a.attribution = spec["attribution"]
        a.flags = [f for f in a.flags if not f.startswith(("shared with a person", "direct database login", "static API key"))]
        retired = [before.principal.removeprefix("apikey:").removeprefix("db:")] + a.extra_logins if spec["retires"] else []
        return {"agent": agent_id, "before": before.label, "after": a.credential.label, "swap": spec["swap"],
                "path": spec["path"], "data": spec["data"], "attribution": spec["attribution_text"],
                "attaches": spec["attaches"], "retired": retired, "code": "unchanged"}

    def with_owner_and_identity(self) -> tuple[int, int]:
        agents = [a for a in self.agents.values() if a.id != "investigator"]
        return sum(1 for a in agents if a.owner and a.credential.kind != "shared"), len(agents)
