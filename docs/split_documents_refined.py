#!/usr/bin/env python3
"""
Refined script to split large documentation files into focused sections.
"""

import re
from pathlib import Path

def find_section_boundaries(content, start_marker, end_marker=None):
    """Find line numbers for section boundaries."""
    lines = content.split('\n')
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if start_marker in line:
            start_idx = i
        if end_marker and end_marker in line and start_idx is not None:
            end_idx = i
            break
    
    if end_idx is None:
        end_idx = len(lines)
    
    return start_idx, end_idx, lines

def split_user_journey():
    """Split user_journey.md into focused sections."""
    base_path = Path("docs")
    source_file = base_path / "user_journey.md"
    output_dir = base_path / "user_journey"
    output_dir.mkdir(exist_ok=True)
    
    content = source_file.read_text()
    lines = content.split('\n')
    
    # Define sections with better boundaries
    sections = {
        "00_overview.md": {
            "start": "## Overview",
            "end": "## Complete User Journey"
        },
        "01_onboarding.md": {
            "start": "### Phase 1: Onboarding & First Project Setup",
            "end": "### Phase 2: Feature Request & Planning"
        },
        "02_feature_planning.md": {
            "start": "### Phase 2: Feature Request & Planning",
            "end": "### Phase 3: Autonomous Execution & Monitoring"
        },
        "03_execution_monitoring.md": {
            "start": "### Phase 3: Autonomous Execution & Monitoring",
            "end": "### Phase 4: Approval Gates & Phase Transitions"
        },
        "04_approvals_completion.md": {
            "start": "### Phase 4: Approval Gates & Phase Transitions",
            "end": "### Phase 5: Ongoing Monitoring & Optimization"
        },
        "05_optimization.md": {
            "start": "### Phase 5: Ongoing Monitoring & Optimization",
            "end": "## Key User Interactions"
        },
        "06_key_interactions.md": {
            "start": "## Key User Interactions",
            "end": "## Phase System Overview"
        },
        "07_phase_system.md": {
            "start": "## Phase System Overview",
            "end": "## User Personas & Use Cases"
        },
        "08_user_personas.md": {
            "start": "## User Personas & Use Cases",
            "end": "## Visual Design Principles"
        },
        "09_design_principles.md": {
            "start": "## Visual Design Principles",
            "end": "## Additional Flows & Edge Cases"
        },
        "10_additional_flows.md": {
            "start": "## Additional Flows & Edge Cases",
            "end": "## Related Documents"
        }
    }
    
    for filename, markers in sections.items():
        start_idx, end_idx, _ = find_section_boundaries(
            content, markers["start"], markers.get("end")
        )
        
        if start_idx is None:
            print(f"Warning: Could not find start marker '{markers['start']}' for {filename}")
            continue
        
        section_lines = lines[start_idx:end_idx]
        section_content = '\n'.join(section_lines)
        
        # Clean up the content - remove duplicate headers
        if filename == "00_overview.md":
            # Add Key User Interactions to overview
            key_interactions_start, key_interactions_end, _ = find_section_boundaries(
                content, "## Key User Interactions", "## Phase System Overview"
            )
            if key_interactions_start:
                key_interactions = '\n'.join(lines[key_interactions_start:key_interactions_end])
                section_content = section_content + "\n\n" + key_interactions
        
        # Add proper header
        title = filename.replace('.md', '').replace('_', ' ').replace('00 ', '').replace('0', '').title()
        header = f"""# {title}

**Part of**: [User Journey Documentation](./README.md)

---
"""
        footer = """

---

**Next**: See [README.md](./README.md) for complete documentation index.
"""
        
        full_content = header + section_content + footer
        (output_dir / filename).write_text(full_content)
        print(f"Created {filename} ({end_idx - start_idx} lines)")

def split_page_flow():
    """Split page_flow.md into focused sections."""
    base_path = Path("docs")
    source_file = base_path / "page_flow.md"
    output_dir = base_path / "page_flows"
    output_dir.mkdir(exist_ok=True)
    
    content = source_file.read_text()
    lines = content.split('\n')
    
    # Define sections
    sections = {
        "00_index.md": {
            "start": "## Navigation Summary",
            "end": "### Flow 25:"
        },
        "01_authentication.md": {
            "start": "### Flow 1: Registration & First Login",
            "end": "### Flow 2:"
        },
        "02_projects_specs.md": {
            "start": "### Flow 2: Project Selection & Creation",
            "end": "### Flow 4:"
        },
        "03_agents_workspaces.md": {
            "start": "### Flow 4: Agent Management & Spawning",
            "end": "### Flow 5:"
        },
        "04_kanban_tickets.md": {
            "start": "### Flow 5: Kanban Board & Ticket Management",
            "end": "### Flow 6:"
        },
        "05_organizations_api.md": {
            "start": "### Flow 6: Organization Management & Multi-Tenancy",
            "end": "### Flow 9:"
        },
        "06_visualizations.md": {
            "start": "### Flow 9: Dependency Graph View",
            "end": "### Flow 13:"
        },
        "07_phases.md": {
            "start": "### Flow 13: Phase Management & Configuration",
            "end": "### Flow 16:"
        },
        "08_collaboration.md": {
            "start": "### Flow 16: Comments & Collaboration",
            "end": "### Flow 25:"
        },
        "09_diagnostic.md": {
            "start": "### Flow 25: Diagnostic Reasoning View",
            "end": "## Related Documents"
        }
    }
    
    for filename, markers in sections.items():
        start_idx, end_idx, _ = find_section_boundaries(
            content, markers["start"], markers.get("end")
        )
        
        if start_idx is None:
            print(f"Warning: Could not find start marker '{markers['start']}' for {filename}")
            continue
        
        section_lines = lines[start_idx:end_idx]
        section_content = '\n'.join(section_lines)
        
        # Add proper header
        title = filename.replace('.md', '').replace('_', ' ').replace('00 ', '').replace('0', '').title()
        header = f"""# {title}

**Part of**: [Page Flow Documentation](./README.md)

---
"""
        footer = """

---

**Next**: See [README.md](./README.md) for complete documentation index.
"""
        
        full_content = header + section_content + footer
        (output_dir / filename).write_text(full_content)
        print(f"Created {filename} ({end_idx - start_idx} lines)")

if __name__ == "__main__":
    print("Splitting user_journey.md...")
    split_user_journey()
    print("\nSplitting page_flow.md...")
    split_page_flow()
    print("\nDone!")


