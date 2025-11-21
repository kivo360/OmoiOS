#!/usr/bin/env python3
"""Split the two largest files further."""

from pathlib import Path

def split_collaboration():
    """Split 08_collaboration.md into smaller files."""
    base_path = Path("docs/page_flows")
    source_file = base_path / "08_collaboration.md"
    
    content = source_file.read_text()
    lines = content.split('\n')
    
    # Find flow boundaries
    flows = {
        "08a_comments_collaboration.md": ("### Flow 16:", "### Flow 17:"),
        "08b_ticket_operations.md": ("### Flow 17:", "### Flow 22:"),
        "08c_github_integration.md": ("### Flow 22:", "### Flow 25:"),
    }
    
    for filename, (start_marker, end_marker) in flows.items():
        start_idx = None
        end_idx = None
        
        for i, line in enumerate(lines):
            if start_marker in line:
                start_idx = i
            if end_marker in line and start_idx is not None:
                end_idx = i
                break
        
        if start_idx is None:
            continue
        
        if end_idx is None:
            end_idx = len(lines)
        
        section_lines = lines[start_idx:end_idx]
        section_content = '\n'.join(section_lines)
        
        header = f"""# {filename.replace('.md', '').replace('_', ' ').replace('08a ', '').replace('08b ', '').replace('08c ', '').title()}

**Part of**: [Page Flow Documentation](./README.md)

---
"""
        footer = """

---

**Next**: See [README.md](./README.md) for complete documentation index.
"""
        
        full_content = header + section_content + footer
        (base_path / filename).write_text(full_content)
        print(f"Created {filename} ({end_idx - start_idx} lines)")
    
    # Remove original file
    source_file.unlink()
    print("Removed original 08_collaboration.md")

def split_diagnostic():
    """Split 09_diagnostic.md into smaller files."""
    base_path = Path("docs/page_flows")
    source_file = base_path / "09_diagnostic.md"
    
    content = source_file.read_text()
    lines = content.split('\n')
    
    # Find flow boundaries
    flows = {
        "09a_diagnostic_reasoning.md": ("### Flow 25:", "### Flow 26:"),
        "09b_phase_overview_graph.md": ("### Flow 26:", "### Flow 28:"),
        "09c_phase_configuration.md": ("### Flow 28:", "## Related Documents"),
    }
    
    for filename, (start_marker, end_marker) in flows.items():
        start_idx = None
        end_idx = None
        
        for i, line in enumerate(lines):
            if start_marker in line:
                start_idx = i
            if end_marker in line and start_idx is not None:
                end_idx = i
                break
        
        if start_idx is None:
            continue
        
        if end_idx is None:
            end_idx = len(lines)
        
        section_lines = lines[start_idx:end_idx]
        section_content = '\n'.join(section_lines)
        
        header = f"""# {filename.replace('.md', '').replace('_', ' ').replace('09a ', '').replace('09b ', '').replace('09c ', '').title()}

**Part of**: [Page Flow Documentation](./README.md)

---
"""
        footer = """

---

**Next**: See [README.md](./README.md) for complete documentation index.
"""
        
        full_content = header + section_content + footer
        (base_path / filename).write_text(full_content)
        print(f"Created {filename} ({end_idx - start_idx} lines)")
    
    # Remove original file
    source_file.unlink()
    print("Removed original 09_diagnostic.md")

if __name__ == "__main__":
    print("Splitting 08_collaboration.md...")
    split_collaboration()
    print("\nSplitting 09_diagnostic.md...")
    split_diagnostic()
    print("\nDone!")

