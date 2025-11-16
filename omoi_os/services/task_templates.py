"""Phase-specific task templates for automatic task generation."""

from omoi_os.models.phases import Phase


PHASE_TASK_TEMPLATES = {
    Phase.REQUIREMENTS: [
        {
            "task_type": "analyze_requirements",
            "description_template": "Analyze and clarify requirements for: {ticket_title}",
            "priority": "HIGH",
            "capabilities": ["analysis"],
        },
        {
            "task_type": "create_requirements_doc",
            "description_template": "Create requirements document for: {ticket_title}",
            "priority": "MEDIUM",
            "capabilities": ["documentation"],
        },
    ],
    Phase.DESIGN: [
        {
            "task_type": "design_architecture",
            "description_template": "Design architecture for: {ticket_title}",
            "priority": "HIGH",
            "capabilities": ["design"],
        },
        {
            "task_type": "create_design_doc",
            "description_template": "Create design document for: {ticket_title}",
            "priority": "MEDIUM",
            "capabilities": ["documentation"],
        },
    ],
    Phase.IMPLEMENTATION: [
        {
            "task_type": "implement_feature",
            "description_template": "Implement feature: {ticket_title}",
            "priority": "HIGH",
            "capabilities": ["implementation"],
        },
        {
            "task_type": "write_unit_tests",
            "description_template": "Write unit tests for: {ticket_title}",
            "priority": "HIGH",
            "capabilities": ["testing", "implementation"],
        },
    ],
    Phase.TESTING: [
        {
            "task_type": "write_tests",
            "description_template": "Write tests for: {ticket_title}",
            "priority": "HIGH",
            "capabilities": ["testing"],
        },
        {
            "task_type": "run_tests",
            "description_template": "Run test suite for: {ticket_title}",
            "priority": "MEDIUM",
            "capabilities": ["testing"],
        },
        {
            "task_type": "validate_coverage",
            "description_template": "Validate test coverage for: {ticket_title}",
            "priority": "MEDIUM",
            "capabilities": ["testing"],
        },
    ],
    Phase.DEPLOYMENT: [
        {
            "task_type": "deploy_feature",
            "description_template": "Deploy feature: {ticket_title}",
            "priority": "CRITICAL",
            "capabilities": ["deployment"],
        },
        {
            "task_type": "verify_deployment",
            "description_template": "Verify deployment for: {ticket_title}",
            "priority": "HIGH",
            "capabilities": ["deployment", "testing"],
        },
    ],
}


def get_templates_for_phase(phase_id: str) -> list[dict]:
    """
    Get task templates for a specific phase.
    
    Args:
        phase_id: Phase identifier (e.g., "PHASE_REQUIREMENTS")
        
    Returns:
        List of task template dictionaries
    """
    # Handle both Phase enum and string values
    phase_key = Phase(phase_id) if phase_id in [p.value for p in Phase] else phase_id
    return PHASE_TASK_TEMPLATES.get(phase_key, [])
