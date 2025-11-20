#!/usr/bin/env python3
"""
Automatically organize documentation using AI.

Uses instructor + async OpenAI to:
- Analyze document content and purpose
- Suggest proper categorization
- Rename to follow conventions
- Move to correct location
- Update cross-references
- Generate missing metadata
"""

import asyncio
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Dict, Literal
from datetime import date

try:
    import instructor
    from openai import AsyncOpenAI
    from pydantic import BaseModel, Field
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   uv add instructor openai pydantic")
    sys.exit(1)


class Colors:
    """ANSI color codes."""
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    MAGENTA = "\033[0;35m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"


class DocumentAnalysis(BaseModel):
    """AI analysis of a document."""
    
    document_type: Literal[
        "requirements",
        "design",
        "architecture",
        "implementation",
        "guide",
        "summary",
        "chat_log",
        "other"
    ] = Field(description="Primary document type based on content")
    
    category: str = Field(
        description="Subcategory (e.g., 'workflows', 'services', 'frontend', 'monitoring')"
    )
    
    suggested_filename: str = Field(
        description="Suggested filename in snake_case (without .md extension)"
    )
    
    purpose: str = Field(
        description="One-sentence purpose of the document"
    )
    
    status: Literal["Draft", "Review", "Approved", "Active", "Implemented", "Archived"] = Field(
        description="Current status of the document"
    )
    
    is_orphaned: bool = Field(
        description="True if document is in wrong location or poorly named"
    )
    
    should_archive: bool = Field(
        description="True if document is outdated and should be archived"
    )
    
    related_docs: List[str] = Field(
        default_factory=list,
        description="List of related document paths that should be cross-referenced"
    )
    
    missing_metadata: List[str] = Field(
        default_factory=list,
        description="List of missing metadata fields (Created, Status, Purpose)"
    )
    
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the analysis (0-1)"
    )
    
    reasoning: str = Field(
        description="Brief explanation of the categorization decision"
    )


class DocumentOrganizer:
    """AI-powered document organizer using instructor + OpenAI."""
    
    def __init__(self, api_key: Optional[str] = None, dry_run: bool = True):
        """Initialize organizer.
        
        Args:
            api_key: OpenAI API key (or from OPENAI_API_KEY env var)
            dry_run: If True, only show changes without applying them
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        self.dry_run = dry_run
        self.client = instructor.from_openai(AsyncOpenAI(api_key=self.api_key))
        self.docs_dir = Path("docs")
        
        # Track changes
        self.changes: List[Dict[str, any]] = []
    
    async def analyze_document(self, file_path: Path) -> Optional[DocumentAnalysis]:
        """Analyze a single document using AI."""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Truncate very long documents
            if len(content) > 8000:
                content = content[:8000] + "\n\n... (truncated)"
            
            prompt = f"""Analyze this documentation file and suggest proper organization.

Current filename: {file_path.name}
Current location: {file_path.parent}

Document content:
{content}

Based on the content, determine:
1. What type of document is this (requirements, design, implementation log, etc.)?
2. What category/domain does it belong to?
3. What should it be named (following snake_case convention)?
4. What is its current status?
5. Is it in the wrong location or poorly named?
6. Should it be archived (outdated/completed phase work)?
7. What related documents should be cross-referenced?

Follow these standards:
- Requirements: What to build (REQ-* codes)
- Design: How to build (technical specs)
- Architecture: Why decisions made (ADRs)
- Implementation: Build status/completion logs
- Guide: How-to documentation
- Summary: High-level overviews (can be UPPERCASE)

Categories:
- workflows, services, frontend, monitoring, memory, agents, auth, integration, testing, configuration

Naming:
- snake_case only (except SUMMARY files can be UPPERCASE)
- Descriptive, not cryptic
- No version numbers (use git history)
"""
            
            analysis = await self.client.chat.completions.create(
                model="gpt-4o",
                response_model=DocumentAnalysis,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing and organizing technical documentation. You understand software architecture, requirements, and design patterns."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
            )
            
            return analysis
        
        except Exception as e:
            print(f"{Colors.RED}❌ Error analyzing {file_path.name}: {e}{Colors.NC}")
            return None
    
    def calculate_new_path(self, analysis: DocumentAnalysis, current_path: Path) -> Path:
        """Calculate new path based on analysis."""
        # Determine base directory
        type_dir_map = {
            "requirements": "requirements",
            "design": "design",
            "architecture": "architecture",
            "implementation": "implementation",
            "guide": "design",  # Guides go in design
            "summary": "",  # Summaries in root
            "chat_log": "archive/chat_logs",
            "other": "archive/uncategorized",
        }
        
        base_dir = type_dir_map.get(analysis.document_type, "archive/uncategorized")
        
        # Add category subdirectory (except for summaries and root items)
        if base_dir and analysis.category and analysis.category != "general":
            full_dir = self.docs_dir / base_dir / analysis.category
        elif base_dir:
            full_dir = self.docs_dir / base_dir
        else:
            full_dir = self.docs_dir
        
        # Calculate filename
        filename = f"{analysis.suggested_filename}.md"
        
        return full_dir / filename
    
    def generate_metadata(
        self,
        analysis: DocumentAnalysis,
        current_content: str
    ) -> str:
        """Generate or update metadata header."""
        lines = current_content.split('\n')
        
        # Check if metadata exists
        has_created = any('**Created**:' in line for line in lines[:10])
        has_status = any('**Status**:' in line for line in lines[:10])
        has_purpose = any('**Purpose**:' in line for line in lines[:10])
        
        # If all metadata exists, return as-is
        if has_created and has_status and has_purpose:
            return current_content
        
        # Find the H1 title
        h1_line = next((i for i, line in enumerate(lines) if line.startswith('# ')), None)
        
        if h1_line is None:
            return current_content  # Can't add metadata without title
        
        # Build metadata block
        metadata_lines = []
        
        if not has_created:
            metadata_lines.append(f"**Created**: {date.today().isoformat()}")
        
        if not has_status:
            metadata_lines.append(f"**Status**: {analysis.status}")
        
        if not has_purpose:
            metadata_lines.append(f"**Purpose**: {analysis.purpose}")
        
        if analysis.related_docs:
            metadata_lines.append(f"**Related**: {', '.join(analysis.related_docs)}")
        
        # Insert metadata after title
        new_lines = (
            lines[:h1_line + 1] +
            [""] +
            metadata_lines +
            ["", "---", ""] +
            lines[h1_line + 1:]
        )
        
        return '\n'.join(new_lines)
    
    async def organize_document(self, file_path: Path) -> Dict[str, any]:
        """Organize a single document."""
        print(f"{Colors.CYAN}📄 Analyzing: {file_path.name}{Colors.NC}")
        
        analysis = await self.analyze_document(file_path)
        
        if not analysis:
            return {"file": file_path, "status": "error", "message": "Analysis failed"}
        
        new_path = self.calculate_new_path(analysis, file_path)
        
        # Determine action needed
        needs_move = new_path != file_path
        needs_metadata = len(analysis.missing_metadata) > 0
        should_archive = analysis.should_archive
        
        change = {
            "file": file_path,
            "analysis": analysis,
            "current_path": file_path,
            "new_path": new_path,
            "needs_move": needs_move,
            "needs_metadata": needs_metadata,
            "should_archive": should_archive,
            "actions": [],
        }
        
        # Build action list
        if should_archive:
            archive_path = self.docs_dir / "archive" / file_path.name
            change["new_path"] = archive_path
            change["actions"].append(f"Archive to {archive_path.relative_to(self.docs_dir)}")
        
        if needs_move and not should_archive:
            change["actions"].append(f"Move to {new_path.relative_to(self.docs_dir)}")
        
        if needs_metadata:
            change["actions"].append(f"Add metadata: {', '.join(analysis.missing_metadata)}")
        
        if not change["actions"]:
            change["actions"].append("No changes needed")
        
        # Print analysis
        print(f"  Type: {Colors.BLUE}{analysis.document_type}{Colors.NC}")
        print(f"  Category: {analysis.category}")
        print(f"  Confidence: {analysis.confidence:.0%}")
        print(f"  Status: {analysis.status}")
        
        if analysis.is_orphaned or should_archive:
            color = Colors.YELLOW if analysis.is_orphaned else Colors.MAGENTA
            status = "Orphaned" if analysis.is_orphaned else "Should Archive"
            print(f"  {color}⚠️  {status}{Colors.NC}")
        
        print(f"  Actions: {', '.join(change['actions'])}")
        print(f"  Reasoning: {analysis.reasoning}")
        print()
        
        return change
    
    async def apply_changes(self, change: Dict[str, any]) -> bool:
        """Apply organizational changes to a document."""
        if self.dry_run:
            return True
        
        try:
            file_path = change["file"]
            new_path = change["new_path"]
            analysis = change["analysis"]
            
            # Read current content
            content = file_path.read_text(encoding="utf-8")
            
            # Update metadata if needed
            if change["needs_metadata"]:
                content = self.generate_metadata(analysis, content)
            
            # Create target directory
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to new location
            new_path.write_text(content, encoding="utf-8")
            
            # Remove old file if moved
            if change["needs_move"] and file_path != new_path:
                file_path.unlink()
                print(f"{Colors.GREEN}✅ Moved: {file_path.name} → {new_path.relative_to(self.docs_dir)}{Colors.NC}")
            
            return True
        
        except Exception as e:
            print(f"{Colors.RED}❌ Error applying changes to {change['file'].name}: {e}{Colors.NC}")
            return False
    
    async def organize_all(
        self,
        pattern: str = "*.md",
        skip_dirs: List[str] = None
    ) -> Dict[str, any]:
        """Organize all matching documents."""
        skip_dirs = skip_dirs or ["archive", "external", ".git"]
        
        # Find all markdown files
        files = []
        for file_path in self.docs_dir.rglob(pattern):
            # Skip certain directories
            if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                continue
            
            # Skip README files
            if file_path.name == "README.md":
                continue
            
            files.append(file_path)
        
        print(f"{Colors.BLUE}🔍 Found {len(files)} documents to analyze{Colors.NC}\n")
        
        # Analyze all documents
        changes = []
        for file_path in files:
            change = await self.organize_document(file_path)
            changes.append(change)
        
        self.changes = changes
        
        # Generate summary
        summary = self.generate_summary()
        
        return summary
    
    def generate_summary(self) -> Dict[str, any]:
        """Generate summary of all changes."""
        total = len(self.changes)
        needs_move = sum(1 for c in self.changes if c["needs_move"])
        needs_metadata = sum(1 for c in self.changes if c["needs_metadata"])
        should_archive = sum(1 for c in self.changes if c["should_archive"])
        no_changes = sum(1 for c in self.changes if c["actions"] == ["No changes needed"])
        
        # Group by type
        by_type = {}
        for change in self.changes:
            doc_type = change["analysis"].document_type
            by_type[doc_type] = by_type.get(doc_type, 0) + 1
        
        return {
            "total": total,
            "needs_move": needs_move,
            "needs_metadata": needs_metadata,
            "should_archive": should_archive,
            "no_changes": no_changes,
            "by_type": by_type,
        }
    
    def print_summary(self):
        """Print organization summary."""
        summary = self.generate_summary()
        
        print(f"\n{Colors.BLUE}{'=' * 60}{Colors.NC}")
        print(f"{Colors.BLUE}📊 Organization Summary{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 60}{Colors.NC}\n")
        
        print(f"Total documents analyzed: {summary['total']}")
        print(f"  {Colors.YELLOW}📦 Need to move: {summary['needs_move']}{Colors.NC}")
        print(f"  {Colors.CYAN}📝 Need metadata: {summary['needs_metadata']}{Colors.NC}")
        print(f"  {Colors.MAGENTA}📁 Should archive: {summary['should_archive']}{Colors.NC}")
        print(f"  {Colors.GREEN}✅ Already organized: {summary['no_changes']}{Colors.NC}")
        
        print(f"\n{Colors.BLUE}Document Types:{Colors.NC}")
        for doc_type, count in sorted(summary['by_type'].items()):
            print(f"  {doc_type}: {count}")
        
        if self.dry_run:
            print(f"\n{Colors.YELLOW}🔍 DRY RUN - No changes applied{Colors.NC}")
            print(f"Run with --apply to make changes")
        else:
            print(f"\n{Colors.GREEN}✅ Changes applied{Colors.NC}")
    
    def export_reorganization_plan(self, output_file: Path):
        """Export detailed reorganization plan as markdown."""
        lines = [
            "# Document Reorganization Plan",
            "",
            f"**Generated**: {date.today().isoformat()}",
            f"**Total Documents**: {len(self.changes)}",
            "",
            "---",
            "",
        ]
        
        # Group by action type
        moves = [c for c in self.changes if c["needs_move"]]
        metadata_updates = [c for c in self.changes if c["needs_metadata"]]
        archives = [c for c in self.changes if c["should_archive"]]
        
        if moves:
            lines.append("## Files to Move")
            lines.append("")
            for change in moves:
                current = change["current_path"].relative_to(self.docs_dir)
                new = change["new_path"].relative_to(self.docs_dir)
                lines.append(f"- `{current}` → `{new}`")
                lines.append(f"  - Reason: {change['analysis'].reasoning}")
                lines.append("")
        
        if metadata_updates:
            lines.append("## Files Needing Metadata")
            lines.append("")
            for change in metadata_updates:
                file = change["file"].name
                missing = ', '.join(change['analysis'].missing_metadata)
                lines.append(f"- `{file}`: Missing {missing}")
                lines.append("")
        
        if archives:
            lines.append("## Files to Archive")
            lines.append("")
            for change in archives:
                file = change["file"].name
                lines.append(f"- `{file}`")
                lines.append(f"  - Reason: {change['analysis'].reasoning}")
                lines.append("")
        
        output_file.write_text('\n'.join(lines), encoding="utf-8")
        print(f"{Colors.GREEN}✅ Exported plan to {output_file}{Colors.NC}")
    
    async def apply_all_changes(self):
        """Apply all analyzed changes."""
        if self.dry_run:
            print(f"{Colors.YELLOW}Dry run mode - no changes will be applied{Colors.NC}")
            return
        
        print(f"{Colors.BLUE}📦 Applying changes...{Colors.NC}\n")
        
        success_count = 0
        for change in self.changes:
            if change["actions"] != ["No changes needed"]:
                if await self.apply_changes(change):
                    success_count += 1
        
        print(f"\n{Colors.GREEN}✅ Applied {success_count}/{len(self.changes)} changes{Colors.NC}")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Organize documentation using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (show changes without applying)
  python scripts/organize_docs.py

  # Apply changes
  python scripts/organize_docs.py --apply

  # Analyze specific pattern
  python scripts/organize_docs.py --pattern "PHASE*.md"

  # Export reorganization plan
  python scripts/organize_docs.py --export reorganization_plan.md

  # Skip certain directories
  python scripts/organize_docs.py --skip design frontend
        """
    )
    
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run)"
    )
    
    parser.add_argument(
        "--pattern",
        default="*.md",
        help="File pattern to match (default: *.md)"
    )
    
    parser.add_argument(
        "--skip",
        nargs="*",
        default=["archive"],
        help="Directories to skip (default: archive)"
    )
    
    parser.add_argument(
        "--export",
        type=Path,
        help="Export reorganization plan to file"
    )
    
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (or use OPENAI_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    # Create organizer
    organizer = DocumentOrganizer(
        api_key=args.api_key,
        dry_run=not args.apply
    )
    
    # Run organization
    try:
        await organizer.organize_all(
            pattern=args.pattern,
            skip_dirs=args.skip
        )
        
        # Print summary
        organizer.print_summary()
        
        # Export plan if requested
        if args.export:
            organizer.export_reorganization_plan(args.export)
        
        # Apply changes if requested
        if args.apply:
            confirm = input(f"\n{Colors.YELLOW}Apply all changes? (y/N): {Colors.NC}")
            if confirm.lower() == 'y':
                await organizer.apply_all_changes()
            else:
                print(f"{Colors.YELLOW}Cancelled{Colors.NC}")
        
        return 0
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Cancelled by user{Colors.NC}")
        return 130
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {e}{Colors.NC}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

