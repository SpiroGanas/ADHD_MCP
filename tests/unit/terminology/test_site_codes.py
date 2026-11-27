"""Per-site mapping of local codes to the concepts the tools use."""

from pathlib import Path

import pytest

from adhd_mcp.fhir.codes import Coding
from adhd_mcp.terminology import UnverifiedContentError
from adhd_mcp.terminology.site_codes import SITE_CONCEPTS, load_site_codes, load_site_codes_file

LOCAL = "urn:adhd-mcp:synthetic-local-code"


def test_synthetic_site_maps_every_concept() -> None:
    site = load_site_codes("synthetic")
    assert set(site.concepts) == set(SITE_CONCEPTS)


@pytest.mark.parametrize(
    ("concept", "code"),
    [
        ("psychiatric_inpatient_encounter", "psychiatric-inpatient"),
        ("psychiatric_residential_encounter", "psychiatric-residential"),
        ("high_risk_flag", "high-risk-for-suicide"),
        ("adhd_evaluation_request", "adhd-evaluation-referral"),
    ],
)
def test_synthetic_codes_match_their_concept(concept: str, code: str) -> None:
    site = load_site_codes("synthetic")
    assert site.matches(concept, (Coding(system=LOCAL, code=code),))
    assert not site.matches(concept, (Coding(system=LOCAL, code="something-else"),))


def test_questionnaire_mapping_finds_items_by_instrument() -> None:
    site = load_site_codes("synthetic")
    mapping = site.questionnaire("urn:adhd-mcp:synthetic-questionnaire:phq-9")
    assert mapping is not None
    assert mapping.instrument == "phq9"
    assert mapping.total == "total"
    assert mapping.items["9"] == "9"
    assert site.questionnaire("urn:unknown") is None


def test_versioned_questionnaire_url_matches_its_canonical() -> None:
    site = load_site_codes("synthetic")
    mapping = site.questionnaire("urn:adhd-mcp:synthetic-questionnaire:phq-9|1.0")
    assert mapping is not None


def test_unknown_concept_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "x.toml"
    path.write_text(
        'id = "x"\nversion = "1"\ntitle = "t"\n'
        '[concepts.no_such_concept]\ntitle = "t"\nentries = []\n'
    )
    with pytest.raises(ValueError, match="no_such_concept"):
        load_site_codes_file(path, strict=False)


def test_strict_loading_refuses_unverified_entries(tmp_path: Path) -> None:
    path = tmp_path / "x.toml"
    path.write_text(
        'id = "x"\nversion = "1"\ntitle = "t"\n'
        '[concepts.high_risk_flag]\ntitle = "t"\n'
        "[[concepts.high_risk_flag.entries]]\n"
        'system = "urn:x"\nmatch = "exact"\ncode = "a"\nverified = false\n'
    )
    with pytest.raises(UnverifiedContentError):
        load_site_codes_file(path, strict=True)
    assert load_site_codes_file(path, strict=False).matches(
        "high_risk_flag", (Coding(system="urn:x", code="a"),)
    )


def test_a_concept_a_site_does_not_map_matches_nothing(tmp_path: Path) -> None:
    path = tmp_path / "x.toml"
    path.write_text('id = "x"\nversion = "1"\ntitle = "t"\n')
    site = load_site_codes_file(path, strict=True)
    assert not site.maps("high_risk_flag")
    assert not site.matches("high_risk_flag", (Coding(system=LOCAL, code="high-risk-for-suicide"),))


def test_unknown_site_is_a_lookup_error() -> None:
    with pytest.raises(LookupError):
        load_site_codes("nowhere")
