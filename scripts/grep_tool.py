import os
import shlex
from collections.abc import Sequence
from typing import Optional

from pydantic import Field

from openhands.sdk import ImageContent, TextContent
from openhands.sdk import Action, Observation
from openhands.sdk.tool import ToolDefinition, ToolExecutor, register_tool
from openhands.tools.terminal import BashExecutor, ExecuteBashAction, TerminalTool


class GrepAction(Action):
    pattern: str = Field(description="Regex to search for")
    path: str = Field(
        default=".", description="Directory to search (absolute or relative)"
    )
    include: Optional[str] = Field(
        default=None, description="Optional glob to filter files (e.g. '*.py')"
    )


class GrepObservation(Observation):
    matches: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    count: int = 0

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        if not self.count:
            return [TextContent(text="No matches found.")]
        files_list = "\n".join(f"- {f}" for f in self.files[:20])
        sample = "\n".join(self.matches[:10])
        more = "\n..." if self.count > 10 else ""
        ret = (
            f"Found {self.count} matching lines.\n"
            f"Files:\n{files_list}\n"
            f"Sample:\n{sample}{more}"
        )
        return [TextContent(text=ret)]


class GrepExecutor(ToolExecutor[GrepAction, GrepObservation]):
    def __init__(self, bash: BashExecutor):
        self.bash: BashExecutor = bash

    def __call__(self, action: GrepAction, conversation=None) -> GrepObservation:  # noqa: ARG002
        root = os.path.abspath(action.path)
        pat = shlex.quote(action.pattern)
        root_q = shlex.quote(root)
        if action.include:
            inc = shlex.quote(action.include)
            cmd = f"grep -rHnE --include {inc} {pat} {root_q} 2>/dev/null | head -100"
        else:
            cmd = f"grep -rHnE {pat} {root_q} 2>/dev/null | head -100"
        result = self.bash(ExecuteBashAction(command=cmd))
        matches: list[str] = []
        files: set[str] = set()
        output_text = result.text
        if output_text.strip():
            for line in output_text.strip().splitlines():
                matches.append(line)
                file_path = line.split(":", 1)[0]
                if file_path:
                    files.add(os.path.abspath(file_path))
        return GrepObservation(matches=matches, files=sorted(files), count=len(matches))


_GREP_DESCRIPTION = """Fast content search tool.

* Searches file contents using regular expressions
* Supports full regex syntax (eg. "log.*Error", "function\\s+\\w+", etc.)
* Filter files by pattern with the include parameter (eg. "*.js", "*.{ts,tsx}")
* Returns matching file paths sorted by modification time.
* Only the first 100 results are returned.
* Use this tool when you need to find files containing specific patterns
"""


class GrepTool(ToolDefinition[GrepAction, GrepObservation]):
    """A custom grep tool that searches file contents using regular expressions."""

    @classmethod
    def create(
        cls, conv_state, bash_executor: BashExecutor | None = None
    ) -> Sequence[ToolDefinition]:
        if bash_executor is None:
            bash_executor = BashExecutor(working_dir=conv_state.workspace.working_dir)
        grep_executor = GrepExecutor(bash_executor)
        return [
            cls(
                description=_GREP_DESCRIPTION,
                action_type=GrepAction,
                observation_type=GrepObservation,
                executor=grep_executor,
            )
        ]


def register_grep_toolset():
    """
    Registers a composite tool factory "BashAndGrepToolSet" that provides:
      - TerminalTool backed by a shared BashExecutor
      - GrepTool using the same BashExecutor
    """

    def _make_bash_and_grep_tools(conv_state) -> list[ToolDefinition]:
        bash_executor = BashExecutor(working_dir=conv_state.workspace.working_dir)
        bash_tool = TerminalTool.create(conv_state, executor=bash_executor)[0]
        grep_tool = GrepTool.create(conv_state, bash_executor=bash_executor)[0]
        return [bash_tool, grep_tool]

    register_tool("BashAndGrepToolSet", _make_bash_and_grep_tools)
