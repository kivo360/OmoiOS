#!/usr/bin/env python3
"""
Script to split large documentation files into focused sections.
"""

import re
from pathlib import Path

def split_user_journey():
    """Split user_journey.md into focused sections."""
    base_path = Path("docs")
    source_file = base_path / "user_journey.md"
    output_dir = base_path / "user_journey"
    output_dir.mkdir(exist_ok=True)
    
    content = source_file.read_text()
    
    # Split into sections based on headers
    sections = {
        "00_overview.md": (0, 82),  # Overview through "Complete User Journey" header
        "01_onboarding.md": (82, 195),  # Phase 1
        "02_feature_planning.md": (195, 314),  # Phase 2
        "03_execution_monitoring.md": (314, 684),  # Phase 3
        "04_approvals_completion.md": (684, 801),  # Phase 4
        "05_optimization.md": (801, 982),  # Phase 5
        "06_phase_system.md": (1018, 1123),  # Phase System Overview
        "07_user_personas.md": (1123, 1185),  # User Personas
        "08_additional_flows.md": (1229, 1850),  # Additional Flows
        "09_design_principles.md": (1185, 1229),  # Design Principles & Success Metrics
    }
    
    lines = content.split('\n')
    
    for filename, (start, end) in sections.items():
        section_content = '\n'.join(lines[start:end])
        
        # Add header with navigation
        header = f"""# {filename.replace('.md', '').replace('_', ' ').title()}

**Part of**: [User Journey Documentation](./README.md)

---
"""
        footer = """

---

**Next**: See [README.md](./README.md) for complete documentation index.
"""
        
        full_content = header + section_content + footer
        (output_dir / filename).write_text(full_content)
        print(f"Created {filename} ({end - start} lines)")

def split_page_flow():
    """Split page_flow.md into focused sections."""
    base_path = Path("docs")
    source_file = base_path / "page_flow.md"
    output_dir = base_path / "page_flows"
    output_dir.mkdir(exist_ok=True)
    
    content = source_file.read_text()
    lines = content.split('\n')
    
    # Find flow boundaries
    flow_starts = {}
    current_flow = None
    
    for i, line in enumerate(lines):
        if line.startswith("### Flow "):
            match = re.match(r"### Flow (\d+):", line)
            if match:
                flow_num = int(match.group(1))
                flow_starts[flow_num] = i
        elif line.startswith("## Navigation Summary"):
            flow_starts["navigation"] = i
            break
    
    # Define groupings
    groupings = {
        "00_index.md": ("## Navigation Summary", None),
        "01_authentication.md": ("### Flow 1:", "### Flow 2:"),
        "02_projects_specs.md": ("### Flow 2:", "### Flow 4:"),
        "03_agents_workspaces.md": ("### Flow 4:", "### Flow 5:"),
        "04_kanban_tickets.md": ("### Flow 5:", "### Flow 6:"),
        "05_organizations_api.md": ("### Flow 6:", "### Flow 9:"),
        "06_visualizations.md": ("### Flow 9:", "### Flow 13:"),
        "07_phases.md": ("### Flow 13:", "### Flow 16:"),
        "08_collaboration.md": ("### Flow 16:", "### Flow 25:"),
        "09_diagnostic.md": ("### Flow 25:", "## Related Documents"),
    }
    
    for filename, (start_marker, end_marker) in groupings.items():
        start_idx = None
        end_idx = None
        
        for i, line in enumerate(lines):
            if start_marker in line:
                start_idx = i
            if end_marker and end_marker in line and start_idx is not None:
                end_idx = i
                break
        
        if start_idx is None:
            print(f"Warning: Could not find start marker for {filename}")
            continue
        
        if end_idx is None:
            end_idx = len(lines)
        
        section_content = '\n'.join(lines[start_idx:end_idx])
        
        # Add header
        header = f"""# {filename.replace('.md', '').replace('_', ' ').title()}

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


