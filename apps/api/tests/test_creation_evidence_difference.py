"""Evidence instability is located by category and name-only path, never by value."""

from copy import deepcopy
from typing import Any

import pytest
from test_creation_api import Provider
from test_safe_edit import M0

from forge_api.cad_create.evidence import CreationEvidence, difference


def evidence(provider: Provider) -> CreationEvidence:
    from test_safe_edit import bodies, config

    return CreationEvidence.project(
        provider.marker,
        deepcopy(provider.data),
        config(provider.marker),
        {**bodies(provider.marker), "bodies": []},
    )


def pair() -> tuple[CreationEvidence, CreationEvidence, Provider]:
    p = Provider()
    return evidence(p), evidence(p), p


def test_identical_evidence_has_no_difference() -> None:
    a, b, _ = pair()
    assert a.digest == b.digest and difference(a, b) == ("none", ())


def test_a_moved_revision_is_reported_as_the_marker_only() -> None:
    a, _, p = pair()
    p.marker = "e" * 24
    p.data["sourceMicroversion"] = p.marker
    assert difference(a, evidence(p)) == ("marker", ())


@pytest.mark.parametrize(
    ("edit", "category", "path"),
    [
        (
            lambda p: p.data.update(extraTopLevel=1),
            "inventory",
            ("extraTopLevel", "<present>"),
        ),
        (
            lambda p: p.data.update(libraryVersion=p.data["libraryVersion"] + 1),
            "inventory",
            ("libraryVersion",),
        ),
        (
            lambda p: p.data.update(serializationVersion="other"),
            "inventory",
            ("serializationVersion",),
        ),
        (
            lambda p: p.data.update(**{"bad key!": 1}),
            "inventory",
            ("<key>", "<present>"),
        ),
    ],
)
def test_content_differences_name_the_path_without_values(
    edit: Any, category: str, path: tuple[str, ...]
) -> None:
    a, _, p = pair()
    edit(p)
    got = difference(a, evidence(p))
    assert got == (category, path)
    assert "other" not in repr(got)


def test_list_positions_are_collapsed_and_lengths_reported() -> None:
    a, _, p = pair()
    a2 = CreationEvidence(
        a.marker,
        {**a.inventory, "extras": [1, {"secretName": "v"}]},
        a.configuration,
        a.bodies,
    )
    b2 = CreationEvidence(
        a.marker,
        {**a.inventory, "extras": [1, {"secretName": "w"}]},
        a.configuration,
        a.bodies,
    )
    c2 = CreationEvidence(
        a.marker, {**a.inventory, "extras": [1]}, a.configuration, a.bodies
    )
    assert difference(a2, b2) == ("inventory", ("extras", "[]", "secretName"))
    assert difference(a2, c2) == ("inventory", ("extras", "[]", "<length>"))
    shown = repr(difference(a2, b2))
    assert "'v'" not in shown and "'w'" not in shown


def test_configuration_and_body_differences_are_categorized() -> None:
    a, _, _ = pair()
    config = {**a.configuration, "configurationMarker": 1}
    bodies = {**a.bodies, "bodies": [{"type": "SOLID", "id": "x"}]}
    assert (
        difference(a, CreationEvidence(a.marker, a.inventory, config, a.bodies))[0]
        == "configuration"
    )
    assert (
        difference(a, CreationEvidence(a.marker, a.inventory, a.configuration, bodies))[
            0
        ]
        == "bodies"
    )


def test_unused_marker_constant_is_a_real_marker() -> None:
    assert len(M0) == 24
