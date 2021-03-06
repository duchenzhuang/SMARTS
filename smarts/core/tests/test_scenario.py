import itertools
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from smarts.core.scenario import Scenario
from smarts.sstudio import gen_social_agent_missions, gen_missions
from smarts.sstudio.sumo2mesh import generate_glb_from_sumo_network
from smarts.sstudio.types import Mission, Route, SocialAgentActor

AGENT_ID = "Agent-007"


@pytest.fixture
def scenario_parent_path():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def scenario_root(scenario_parent_path):
    # TODO: We may want to consider referencing to concrete scenarios in our tests
    #       rather than generating them. The benefit of generting however is that
    #       we can change the test criteria and scenario code in unison.
    scenario = Path(scenario_parent_path) / "cycles"
    scenario.mkdir()

    shutil.copyfile(
        Path(__file__).parent / "maps/6lane.net.xml", scenario / "map.net.xml"
    )
    generate_glb_from_sumo_network(
        str(scenario / "map.net.xml"), str(scenario / "map.glb")
    )

    actors = [
        SocialAgentActor(
            name=f"non-interactive-agent-{speed}-v0",
            agent_locator="zoo.policies:non-interactive-agent-v0",
            policy_kwargs={"speed": speed},
        )
        for speed in [10, 30, 80]
    ]

    for name, (edge_start, edge_end) in [
        ("group-1", ("edge-north-NS", "edge-south-NS")),
        ("group-2", ("edge-west-WE", "edge-east-WE")),
        ("group-3", ("edge-east-EW", "edge-west-EW")),
        ("group-4", ("edge-south-SN", "edge-north-SN")),
    ]:
        route = Route(begin=("edge-north-NS", 1, 0), end=("edge-south-NS", 1, "max"))
        missions = [Mission(route=route)] * 2  # double up
        gen_social_agent_missions(
            scenario, social_agent_actor=actors, name=name, missions=missions,
        )

    gen_missions(
        scenario,
        missions=[
            Mission(Route(begin=("edge-west-WE", 0, 0), end=("edge-east-WE", 0, "max")))
        ],
    )

    return scenario


def temp_scenario_variations_of_social_agents(scenario_root):
    iterator = Scenario.variations_for_all_scenario_roots(
        [str(scenario_root)], [AGENT_ID]
    )
    scenarios = list(iterator)

    assert len(scenarios) == 6, "3 social agents x 2 missions each "
    for s in scenarios:
        assert len(s.social_agents) == 4, "4 social agents"
        assert len(s.missions) == 5, "4 missions for social agents + 1 for ego"

    # Ensure correct social agents are being spawned
    all_social_agent_ids = set()
    for s in scenarios:
        all_social_agent_ids |= set(s.social_agents.keys())

    groups = ["group-1", "group-2", "group-3", "group-4"]
    speeds = [10, 30, 80]
    expected_social_agent_ids = {
        f"social-agent-{group}-non-interactive-agent-{speed}-v0"
        for group, speed in itertools.product(groups, speeds)
    }

    assert (
        len(all_social_agent_ids - expected_social_agent_ids) == 0
    ), "All the correct social agent IDs were used"
