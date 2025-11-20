#!/usr/bin/env python3
"""
Batch document organization with progress tracking.

Uses instructor + async OpenAI with batching for faster processing.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict
from datetime import date

try:
    import instructor
    from openai import AsyncOpenAI
    from pydantic import BaseModel, Field
    from tqdm.asyncio import tqdm
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   uv add instructor openai pydantic tqdm")
    sys.exit(1)

from organize_docs import DocumentAnalysis, DocumentOrganizer, Colors


class BatchDocumentOrganizer(DocumentOrganizer):
    """Batch organizer with progress tracking and concurrent processing."""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        dry_run: bool = True,
        max_concurrent: int = 5,
    ):
        """Initialize batch organizer.

        Args:
            api_key: API key (Fireworks or OpenAI)
            base_url: Base URL for API
            model: Model to use
            dry_run: If True, only show changes
            max_concurrent: Maximum concurrent API calls
        """
        super().__init__(api_key, base_url, model, dry_run)
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def analyze_document_with_semaphore(self, file_path: Path) -> tuple[Path, DocumentAnalysis]:
        """Analyze document with concurrency control."""
        async with self.semaphore:
            analysis = await self.analyze_document(file_path)
            return (file_path, analysis)
    
    async def organize_all_batch(
        self,
        pattern: str = "*.md",
        skip_dirs: List[str] = None,
        show_progress: bool = True
    ) -> Dict[str, any]:
        """Organize all documents in batch with progress bar."""
        skip_dirs = skip_dirs or ["archive", "external", ".git"]
        
        # Find all files
        files = []
        for file_path in self.docs_dir.rglob(pattern):
            if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                continue
            if file_path.name == "README.md":
                continue
            files.append(file_path)
        
        print(f"{Colors.BLUE}🔍 Found {len(files)} documents to analyze{Colors.NC}")
        print(f"{Colors.BLUE}🚀 Using {self.max_concurrent} concurrent workers{Colors.NC}\n")
        
        # Analyze all documents concurrently with progress bar
        if show_progress:
            tasks = [self.analyze_document_with_semaphore(f) for f in files]
            results = await tqdm.gather(*tasks, desc="Analyzing documents")
        else:
            results = await asyncio.gather(
                *[self.analyze_document_with_semaphore(f) for f in files]
            )
        
        # Process results
        changes = []
        for file_path, analysis in results:
            if analysis:
                new_path = self.calculate_new_path(analysis, file_path)
                
                change = {
                    "file": file_path,
                    "analysis": analysis,
                    "current_path": file_path,
                    "new_path": new_path,
                    "needs_move": new_path != file_path,
                    "needs_metadata": len(analysis.missing_metadata) > 0,
                    "should_archive": analysis.should_archive,
                    "actions": [],
                }
                
                # Build action list
                if change["should_archive"]:
                    archive_path = self.docs_dir / "archive" / file_path.name
                    change["new_path"] = archive_path
                    change["actions"].append(f"Archive to {archive_path.relative_to(self.docs_dir)}")
                
                if change["needs_move"] and not change["should_archive"]:
                    change["actions"].append(f"Move to {new_path.relative_to(self.docs_dir)}")
                
                if change["needs_metadata"]:
                    change["actions"].append(f"Add metadata: {', '.join(analysis.missing_metadata)}")
                
                if not change["actions"]:
                    change["actions"].append("No changes needed")
                
                changes.append(change)
        
        self.changes = changes
        return self.generate_summary()
    
    def print_detailed_report(self):
        """Print detailed change report."""
        print(f"\n{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}📋 Detailed Change Report{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}\n")
        
        # Group by action type
        moves = [c for c in self.changes if c["needs_move"] and not c["should_archive"]]
        metadata = [c for c in self.changes if c["needs_metadata"]]
        archives = [c for c in self.changes if c["should_archive"]]
        no_change = [c for c in self.changes if c["actions"] == ["No changes needed"]]
        
        if moves:
            print(f"{Colors.YELLOW}📦 Files to Move ({len(moves)}):{Colors.NC}\n")
            for change in moves:
                current = change["current_path"].relative_to(self.docs_dir)
                new = change["new_path"].relative_to(self.docs_dir)
                print(f"  {current}")
                print(f"    → {new}")
                print(f"    Type: {change['analysis'].document_type} | Category: {change['analysis'].category}")
                print(f"    Confidence: {change['analysis'].confidence:.0%}")
                print(f"    Reason: {change['analysis'].reasoning}")
                print()
        
        if metadata:
            print(f"{Colors.CYAN}📝 Files Needing Metadata ({len(metadata)}):{Colors.NC}\n")
            for change in metadata:
                file = change["file"].name
                missing = ', '.join(change['analysis'].missing_metadata)
                print(f"  {file}: {missing}")
            print()
        
        if archives:
            print(f"{Colors.MAGENTA}📁 Files to Archive ({len(archives)}):{Colors.NC}\n")
            for change in archives:
                file = change["file"].name
                print(f"  {file}")
                print(f"    Reason: {change['analysis'].reasoning}")
            print()
        
        if no_change:
            print(f"{Colors.GREEN}✅ Already Organized ({len(no_change)}):{Colors.NC}\n")
            for change in no_change[:5]:  # Show first 5
                print(f"  {change['file'].name}")
            if len(no_change) > 5:
                print(f"  ... and {len(no_change) - 5} more")
            print()


async def main():
    """Main entry point for batch organizer."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Batch organize documentation with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run)"
    )
    
    parser.add_argument(
        "--pattern",
        default="*.md",
        help="File pattern to match"
    )
    
    parser.add_argument(
        "--concurrent",
        type=int,
        default=5,
        help="Maximum concurrent API calls (default: 5)"
    )
    
    parser.add_argument(
        "--export",
        type=Path,
        help="Export reorganization plan to markdown file"
    )
    
    parser.add_argument(
        "--detailed", action="store_true", help="Show detailed report with all changes"
    )

    parser.add_argument(
        "--api-key",
        help="API key (or use FIREWORKS_API_KEY/OPENAI_API_KEY env var)",
    )

    parser.add_argument(
        "--base-url",
        help="API base URL (default: Fireworks AI)",
    )

    parser.add_argument(
        "--model",
        default="accounts/fireworks/models/gpt-oss-120b",
        help="Model to use (default: Fireworks gpt-oss-120b)",
    )

    args = parser.parse_args()

    # Create batch organizer
    organizer = BatchDocumentOrganizer(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        dry_run=not args.apply,
        max_concurrent=args.concurrent,
    )
    
    try:
        # Run batch organization
        await organizer.organize_all_batch(
            pattern=args.pattern,
            show_progress=True
        )
        
        # Print reports
        if args.detailed:
            organizer.print_detailed_report()
        
        organizer.print_summary()
        
        # Export if requested
        if args.export:
            organizer.export_reorganization_plan(args.export)
        
        # Apply if requested
        if args.apply:
            print(f"\n{Colors.YELLOW}⚠️  This will reorganize {len(organizer.changes)} documents{Colors.NC}")
            confirm = input(f"{Colors.YELLOW}Continue? (y/N): {Colors.NC}")
            if confirm.lower() == 'y':
                await organizer.apply_all_changes()
                print(f"\n{Colors.GREEN}✅ Organization complete!{Colors.NC}")
            else:
                print(f"{Colors.YELLOW}Cancelled{Colors.NC}")
        
        return 0
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Cancelled by user{Colors.NC}")
        return 130
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {e}{Colors.NC}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

