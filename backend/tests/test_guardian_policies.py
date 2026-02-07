"""Tests for guardian policy loading and evaluation."""

from pathlib import Path

import yaml

from omoi_os.models.guardian_action import AuthorityLevel

# Get the path to policy files
POLICY_DIR = Path(__file__).parent.parent / "omoi_os" / "config" / "guardian_policies"


def test_policy_directory_exists():
    """Test that the guardian_policies directory exists."""
    assert POLICY_DIR.exists(), f"Policy directory not found: {POLICY_DIR}"
    assert POLICY_DIR.is_dir(), f"Policy path is not a directory: {POLICY_DIR}"


def test_emergency_policy_exists():
    """Test that emergency.yaml policy exists."""
    policy_file = POLICY_DIR / "emergency.yaml"
    assert policy_file.exists(), f"Emergency policy not found: {policy_file}"


def test_resource_reallocation_policy_exists():
    """Test that resource_reallocation.yaml policy exists."""
    policy_file = POLICY_DIR / "resource_reallocation.yaml"
    assert (
        policy_file.exists()
    ), f"Resource reallocation policy not found: {policy_file}"


def test_priority_override_policy_exists():
    """Test that priority_override.yaml policy exists."""
    policy_file = POLICY_DIR / "priority_override.yaml"
    assert policy_file.exists(), f"Priority override policy not found: {policy_file}"


def test_emergency_policy_valid_yaml():
    """Test that emergency policy is valid YAML and has required fields."""
    policy_file = POLICY_DIR / "emergency.yaml"

    with open(policy_file, "r") as f:
        policy_data = yaml.safe_load(f)

    assert policy_data is not None
    assert "policy" in policy_data

    policy = policy_data["policy"]
    assert "name" in policy
    assert "version" in policy
    assert "description" in policy
    assert "min_authority" in policy
    assert "triggers" in policy
    assert "actions" in policy
    assert "rollback" in policy

    # Verify authority level
    assert policy["min_authority"] == 4  # GUARDIAN level

    # Verify triggers is a list
    assert isinstance(policy["triggers"], list)
    assert len(policy["triggers"]) > 0

    # Verify each trigger has required fields
    for trigger in policy["triggers"]:
        assert "type" in trigger
        assert "condition" in trigger
        assert "description" in trigger


def test_resource_reallocation_policy_valid_yaml():
    """Test that resource reallocation policy is valid YAML with proper structure."""
    policy_file = POLICY_DIR / "resource_reallocation.yaml"

    with open(policy_file, "r") as f:
        policy_data = yaml.safe_load(f)

    assert policy_data is not None
    policy = policy_data["policy"]

    # Verify core fields
    assert policy["name"] == "resource_reallocation"
    assert policy["min_authority"] == AuthorityLevel.GUARDIAN

    # Verify rules section exists
    assert "rules" in policy
    assert isinstance(policy["rules"], list)

    # Verify at least one rule with proper structure
    for rule in policy["rules"]:
        assert "name" in rule
        assert "source_criteria" in rule
        assert "target_criteria" in rule


def test_priority_override_policy_valid_yaml():
    """Test that priority override policy is valid YAML with escalation rules."""
    policy_file = POLICY_DIR / "priority_override.yaml"

    with open(policy_file, "r") as f:
        policy_data = yaml.safe_load(f)

    assert policy_data is not None
    policy = policy_data["policy"]

    # Verify core fields
    assert policy["name"] == "priority_override"
    assert policy["min_authority"] == 4

    # Verify rules section for escalation
    assert "rules" in policy
    rules = policy["rules"]
    assert len(rules) >= 2  # Should have escalate_to_critical and escalate_to_high

    # Verify escalation rule structure
    for rule in rules:
        assert "name" in rule
        assert "when" in rule
        assert "new_priority" in rule
        assert rule["new_priority"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def test_all_policies_have_rollback_config():
    """Test that all policies have rollback configuration."""
    policy_files = [
        "emergency.yaml",
        "resource_reallocation.yaml",
        "priority_override.yaml",
    ]

    for policy_filename in policy_files:
        policy_file = POLICY_DIR / policy_filename

        with open(policy_file, "r") as f:
            policy_data = yaml.safe_load(f)

        policy = policy_data["policy"]
        assert "rollback" in policy, f"Policy {policy_filename} missing rollback config"

        rollback = policy["rollback"]
        assert "enabled" in rollback
        assert isinstance(rollback["enabled"], bool)


def test_policy_authority_levels_consistent():
    """Test that all policies use consistent authority levels (GUARDIAN = 4)."""
    policy_files = [
        "emergency.yaml",
        "resource_reallocation.yaml",
        "priority_override.yaml",
    ]

    for policy_filename in policy_files:
        policy_file = POLICY_DIR / policy_filename

        with open(policy_file, "r") as f:
            policy_data = yaml.safe_load(f)

        policy = policy_data["policy"]
        min_authority = policy["min_authority"]

        # All guardian policies should require GUARDIAN level (4) or higher
        assert (
            min_authority >= AuthorityLevel.GUARDIAN
        ), f"Policy {policy_filename} has insufficient authority level: {min_authority}"


# -------------------------------------------------------------------------
# Policy Evaluation Logic Tests (Mock implementation)
# -------------------------------------------------------------------------


class PolicyEvaluator:
    """Simple policy evaluator for testing purposes.

    This is a minimal implementation to demonstrate how policies
    would be evaluated in practice. The real implementation would
    be more sophisticated.
    """

    def __init__(self, policy_path: Path):
        with open(policy_path, "r") as f:
            policy_data = yaml.safe_load(f)
        self.policy = policy_data["policy"]

    def check_authority(self, current_authority: AuthorityLevel) -> bool:
        """Check if current authority meets minimum requirement."""
        return current_authority >= self.policy["min_authority"]

    def get_triggers(self):
        """Get all policy triggers."""
        return self.policy.get("triggers", [])

    def should_rollback(self) -> bool:
        """Check if policy has rollback enabled."""
        return self.policy.get("rollback", {}).get("enabled", False)


def test_policy_evaluator_authority_check():
    """Test policy evaluator authority checking."""
    policy_file = POLICY_DIR / "emergency.yaml"
    evaluator = PolicyEvaluator(policy_file)

    # GUARDIAN level should pass
    assert evaluator.check_authority(AuthorityLevel.GUARDIAN) is True

    # SYSTEM level should pass (higher than GUARDIAN)
    assert evaluator.check_authority(AuthorityLevel.SYSTEM) is True

    # WORKER level should fail
    assert evaluator.check_authority(AuthorityLevel.WORKER) is False

    # WATCHDOG level should fail
    assert evaluator.check_authority(AuthorityLevel.WATCHDOG) is False


def test_policy_evaluator_triggers():
    """Test policy evaluator trigger retrieval."""
    policy_file = POLICY_DIR / "emergency.yaml"
    evaluator = PolicyEvaluator(policy_file)

    triggers = evaluator.get_triggers()
    assert len(triggers) > 0

    # Check that triggers have expected types
    trigger_types = [t["type"] for t in triggers]
    assert "task_timeout" in trigger_types
    assert "agent_failure" in trigger_types


def test_policy_evaluator_rollback_enabled():
    """Test policy evaluator rollback checking."""
    # All our policies have rollback enabled
    for policy_filename in [
        "emergency.yaml",
        "resource_reallocation.yaml",
        "priority_override.yaml",
    ]:
        policy_file = POLICY_DIR / policy_filename
        evaluator = PolicyEvaluator(policy_file)

        assert (
            evaluator.should_rollback() is True
        ), f"Policy {policy_filename} should have rollback enabled"
