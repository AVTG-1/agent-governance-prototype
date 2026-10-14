import pytest

from app.core.policies import baseline_policy
from app.core.world import World


@pytest.fixture
def world():
    """A world after Acts 1–2: agents discovered, recon wrapped, baseline policy adopted."""
    w = World()
    w.discover()
    w.assign_owners()
    w.registry.wrap("recon-agent")
    w.policy.adopt(baseline_policy(w.policy.current), "baseline")
    return w
