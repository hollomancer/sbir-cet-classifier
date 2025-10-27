import pytest

from sbir_cet_classifier.common.classification_config import (
    load_classification_rules,
    get_cet_keywords_map,
    get_agency_priors,
    get_branch_priors,
    get_context_rules,
)


def test_load_classification_rules_default_path():
    """Basic loading sanity check for the classification rules loader."""
    rules = load_classification_rules()
    assert rules is not None
    # key structures should be present
    assert hasattr(rules, "agency_priors")
    assert hasattr(rules, "branch_priors")
    assert hasattr(rules, "cet_keywords")
    assert hasattr(rules, "context_rules")


def test_agency_priors_contains_dod_hypersonics():
    """Ensure Department of Defense priors include hypersonics with expected boost."""
    priors = get_agency_priors()
    assert isinstance(priors, dict)
    dod = priors.get("Department of Defense")
    assert dod is not None, "Expected 'Department of Defense' in agency_priors"
    assert isinstance(dod, dict)
    # Value from config should be an integer boost (15)
    assert dod.get("hypersonics") == 15


def test_branch_priors_contains_airforce_hypersonics():
    """Ensure branch priors include Air Force hypersonics boost."""
    branch = get_branch_priors()
    assert isinstance(branch, dict)
    air = branch.get("Air Force")
    assert air is not None, "Expected 'Air Force' in branch_priors"
    assert isinstance(air, dict)
    assert air.get("hypersonics") == 20


def test_cet_keywords_map_contains_quantum():
    """CET keyword map should include core quantum computing phrases."""
    cet_map = get_cet_keywords_map()
    assert isinstance(cet_map, dict)
    assert "quantum_computing" in cet_map
    quantum = cet_map["quantum_computing"]
    # The core bucket should contain the phrase 'quantum computing'
    assert any("quantum computing" in s for s in quantum.core)


def test_context_rules_medical_devices_structure():
    """Context rules should include medical_devices rules with expected keywords and boost."""
    ctx = get_context_rules()
    assert isinstance(ctx, dict)
    assert "medical_devices" in ctx
    rules = ctx["medical_devices"]
    assert isinstance(rules, list)
    # Look for a rule that requires ['ai', 'diagnostic'] (order may vary in normalization)
    found = False
    for rule in rules:
        # rule may be a dict-like object (pydantic model) or plain dict
        req = getattr(rule, "required_keywords", None) or rule.get("required_keywords", None)
        boost = getattr(rule, "boost", None) or rule.get("boost", None)
        if not req:
            continue
        req_lower = [str(x).lower() for x in req]
        if "ai" in req_lower and "diagnostic" in req_lower:
            assert int(boost) == 20
            found = True
            break
    assert found, "Expected a context rule for medical_devices that includes ['ai', 'diagnostic'] with boost 20"
