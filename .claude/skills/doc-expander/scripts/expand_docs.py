#!/usr/bin/env python3
"""
Documentation Expander Script

Generates research questions for expanding documentation and provides
a structured workflow for using DeepWiki and Context7 MCP servers.

This script is meant to be used as a reference and helper for Claude
when expanding documentation. It generates questions and research plans
that Claude then executes using the MCP tools.

Usage:
    python expand_docs.py docs/api.md --library fastapi
    python expand_docs.py --new --library pydantic --output docs/pydantic.md
    python expand_docs.py docs/readme.md --questions-only
"""

import argparse
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ResearchPlan:
    """A structured research plan for documentation expansion."""
    library: str
    repo: Optional[str] = None
    doc_type: str = "library"
    existing_sections: list[str] = field(default_factory=list)
    questions: dict[str, list[str]] = field(default_factory=dict)
    context7_queries: list[dict] = field(default_factory=list)
    deepwiki_queries: list[dict] = field(default_factory=list)


def extract_sections(content: str) -> list[str]:
    """Extract section headers from markdown content."""
    sections = []
    for line in content.split('\n'):
        if line.startswith('#'):
            # Remove # symbols and clean up
            header = line.lstrip('#').strip()
            sections.append(header)
    return sections


def identify_doc_type(content: str, library: str) -> str:
    """Identify the type of documentation based on content."""
    content_lower = content.lower()

    if 'endpoint' in content_lower or 'api' in content_lower and 'rest' in content_lower:
        return 'api'
    elif 'cli' in content_lower or 'command' in content_lower:
        return 'tool'
    elif 'framework' in content_lower or 'router' in content_lower:
        return 'framework'
    else:
        return 'library'


def generate_questions(doc_type: str, library: str, existing_sections: list[str]) -> dict[str, list[str]]:
    """Generate research questions based on doc type and gaps."""

    questions = {
        "foundation": [],
        "architecture": [],
        "usage": [],
        "integration": [],
        "advanced": [],
    }

    # Check for common missing sections
    section_names_lower = [s.lower() for s in existing_sections]

    # Foundation questions
    if not any('overview' in s or 'introduction' in s or 'about' in s for s in section_names_lower):
        questions["foundation"].extend([
            f"What is {library} and what problem does it solve?",
            f"What are the core concepts and terminology in {library}?",
            f"What are the key features and capabilities of {library}?",
        ])

    # Architecture questions
    if not any('architecture' in s or 'design' in s or 'structure' in s for s in section_names_lower):
        questions["architecture"].extend([
            f"What is the high-level architecture of {library}?",
            f"What are the main components/modules in {library}?",
            f"How do the components in {library} interact with each other?",
        ])

    # Usage questions
    if not any('install' in s or 'setup' in s or 'getting started' in s for s in section_names_lower):
        questions["usage"].extend([
            f"How do I install {library}?",
            f"What are the system requirements for {library}?",
            f"What is a basic usage example for {library}?",
        ])

    if not any('example' in s or 'tutorial' in s for s in section_names_lower):
        questions["usage"].extend([
            f"What are common use cases for {library}?",
            f"Can you show practical examples of using {library}?",
        ])

    # Integration questions
    if not any('integration' in s or 'plugin' in s for s in section_names_lower):
        questions["integration"].extend([
            f"What are the dependencies of {library}?",
            f"How does {library} integrate with other tools/frameworks?",
            f"Are there official plugins or extensions for {library}?",
        ])

    # Advanced questions
    if not any('advanced' in s or 'performance' in s or 'security' in s for s in section_names_lower):
        questions["advanced"].extend([
            f"What are performance considerations for {library}?",
            f"What security best practices apply to {library}?",
            f"How do I debug issues with {library}?",
        ])

    if not any('troubleshoot' in s or 'faq' in s or 'common issues' in s for s in section_names_lower):
        questions["advanced"].extend([
            f"What are common issues when using {library} and how to fix them?",
            f"What error messages might I encounter with {library}?",
        ])

    # Add doc-type specific questions
    if doc_type == 'api':
        questions["usage"].extend([
            f"What authentication methods does {library} support?",
            f"What are the rate limits for {library}?",
            f"How do I handle pagination in {library}?",
        ])
    elif doc_type == 'framework':
        questions["architecture"].extend([
            f"How does routing work in {library}?",
            f"How do I handle middleware in {library}?",
        ])
        questions["usage"].extend([
            f"How do I deploy a {library} application?",
        ])
    elif doc_type == 'tool':
        questions["usage"].extend([
            f"What commands are available in {library}?",
            f"How do I configure {library}?",
        ])

    # Remove empty categories
    return {k: v for k, v in questions.items() if v}


def generate_context7_queries(library: str, questions: dict[str, list[str]]) -> list[dict]:
    """Generate Context7 MCP queries from questions."""
    queries = []

    # First, resolve library ID
    queries.append({
        "tool": "resolve-library-id",
        "params": {"libraryName": library},
        "purpose": "Get Context7-compatible library ID",
    })

    # Map question categories to topics
    topic_map = {
        "foundation": ["overview", "introduction"],
        "architecture": ["architecture", "design"],
        "usage": ["getting started", "installation", "examples"],
        "integration": ["integration", "plugins"],
        "advanced": ["performance", "security", "troubleshooting"],
    }

    for category, topics in topic_map.items():
        if category in questions:
            for topic in topics:
                queries.append({
                    "tool": "get-library-docs",
                    "params": {
                        "context7CompatibleLibraryID": f"{{resolved_id}}",
                        "topic": topic,
                        "mode": "code" if category in ["usage", "integration"] else "info",
                    },
                    "purpose": f"Research {topic} for {category} questions",
                })

    return queries


def generate_deepwiki_queries(repo: str, questions: dict[str, list[str]]) -> list[dict]:
    """Generate DeepWiki MCP queries from questions."""
    queries = []

    if not repo:
        return queries

    # Get wiki structure first
    queries.append({
        "tool": "read_wiki_structure",
        "params": {"repoName": repo},
        "purpose": "Understand available documentation topics",
    })

    # Generate questions for each category
    for category, q_list in questions.items():
        for question in q_list[:2]:  # Limit to avoid too many queries
            queries.append({
                "tool": "ask_question",
                "params": {
                    "repoName": repo,
                    "question": question,
                },
                "purpose": f"Research: {question[:50]}...",
            })

    return queries


def create_research_plan(
    library: str,
    repo: Optional[str] = None,
    existing_content: Optional[str] = None,
) -> ResearchPlan:
    """Create a complete research plan for documentation expansion."""

    existing_sections = []
    doc_type = "library"

    if existing_content:
        existing_sections = extract_sections(existing_content)
        doc_type = identify_doc_type(existing_content, library)

    questions = generate_questions(doc_type, library, existing_sections)
    context7_queries = generate_context7_queries(library, questions)
    deepwiki_queries = generate_deepwiki_queries(repo or "", questions)

    return ResearchPlan(
        library=library,
        repo=repo,
        doc_type=doc_type,
        existing_sections=existing_sections,
        questions=questions,
        context7_queries=context7_queries,
        deepwiki_queries=deepwiki_queries,
    )


def format_research_plan(plan: ResearchPlan) -> str:
    """Format research plan as markdown for Claude to execute."""

    output = []
    output.append(f"# Research Plan for {plan.library}")
    output.append("")
    output.append(f"**Documentation Type:** {plan.doc_type}")
    if plan.repo:
        output.append(f"**GitHub Repository:** {plan.repo}")
    output.append("")

    if plan.existing_sections:
        output.append("## Existing Sections")
        for section in plan.existing_sections:
            output.append(f"- {section}")
        output.append("")

    output.append("## Research Questions")
    for category, questions in plan.questions.items():
        output.append(f"\n### {category.title()}")
        for q in questions:
            output.append(f"- {q}")
    output.append("")

    output.append("## Context7 Queries")
    output.append("Execute these MCP calls to gather documentation:")
    output.append("")
    for i, query in enumerate(plan.context7_queries, 1):
        output.append(f"### Query {i}: {query['purpose']}")
        output.append("```python")
        output.append(f"mcp__context7-mcp__{query['tool']}(")
        for key, value in query['params'].items():
            output.append(f"    {key}={repr(value)},")
        output.append(")")
        output.append("```")
        output.append("")

    if plan.deepwiki_queries:
        output.append("## DeepWiki Queries")
        output.append("Execute these MCP calls for implementation details:")
        output.append("")
        for i, query in enumerate(plan.deepwiki_queries, 1):
            output.append(f"### Query {i}: {query['purpose']}")
            output.append("```python")
            output.append(f"mcp__deepwiki-mcp__{query['tool']}(")
            for key, value in query['params'].items():
                output.append(f"    {key}={repr(value)},")
            output.append(")")
            output.append("```")
            output.append("")

    output.append("## Output Template")
    output.append("")
    output.append("Synthesize findings into this structure:")
    output.append("")
    output.append("```markdown")
    output.append(f"# {plan.library} Documentation")
    output.append("")
    output.append("## Overview")
    output.append("[From Context7 info mode]")
    output.append("")
    output.append("## Installation")
    output.append("[From Context7 code mode]")
    output.append("")
    output.append("## Quick Start")
    output.append("[Synthesized from both sources]")
    output.append("")
    output.append("## Core Concepts")
    output.append("[From both sources]")
    output.append("")
    output.append("## API Reference")
    output.append("[From Context7 code mode]")
    output.append("")
    output.append("## Examples")
    output.append("[From DeepWiki + Context7]")
    output.append("")
    output.append("## Troubleshooting")
    output.append("[From both sources]")
    output.append("```")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Generate research plans for documentation expansion"
    )
    parser.add_argument(
        "doc_path",
        type=Path,
        nargs="?",
        help="Path to existing documentation to expand"
    )
    parser.add_argument(
        "--library",
        "-l",
        required=True,
        help="Library/package name to research"
    )
    parser.add_argument(
        "--repo",
        "-r",
        help="GitHub repository (owner/repo format)"
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help="Create new documentation (no existing file)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output path for research plan"
    )
    parser.add_argument(
        "--questions-only",
        action="store_true",
        help="Only generate questions, no MCP queries"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of markdown"
    )

    args = parser.parse_args()

    existing_content = None
    if args.doc_path and args.doc_path.exists():
        existing_content = args.doc_path.read_text()
    elif args.doc_path and not args.new:
        print(f"Warning: File not found: {args.doc_path}")

    plan = create_research_plan(
        library=args.library,
        repo=args.repo,
        existing_content=existing_content,
    )

    if args.json:
        output = json.dumps({
            "library": plan.library,
            "repo": plan.repo,
            "doc_type": plan.doc_type,
            "existing_sections": plan.existing_sections,
            "questions": plan.questions,
            "context7_queries": plan.context7_queries if not args.questions_only else [],
            "deepwiki_queries": plan.deepwiki_queries if not args.questions_only else [],
        }, indent=2)
    else:
        if args.questions_only:
            plan.context7_queries = []
            plan.deepwiki_queries = []
        output = format_research_plan(plan)

    if args.output:
        args.output.write_text(output)
        print(f"Research plan written to: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
