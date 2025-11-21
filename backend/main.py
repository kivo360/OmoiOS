from openhands.sdk import LLM

import os

from openhands.sdk import (
    Agent,
    Conversation,
    Tool,
    Event,
    LLMConvertibleEvent,
    AgentContext,
)
from openhands.sdk import LLMRegistry, Message, TextContent
from openhands.sdk.context import KeywordTrigger, Skill
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool
from rich.console import Console
from rich.traceback import install
from openhands.sdk.security.confirmation_policy import AlwaysConfirm, NeverConfirm
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.tools.preset.default import get_default_agent
from openhands.sdk.conversation.state import (
    ConversationExecutionStatus,
    ConversationState,
)

from grep_tool import register_grep_toolset
from omoi_os.config import get_app_settings, load_llm_settings

install()

console = Console()


async def main():
    app_settings = get_app_settings()
    demo_settings = app_settings.demo
    example = demo_settings.sdk_example.lower()
    settings = load_llm_settings()
    persistence_dir = demo_settings.persistence_dir or ".conversations"
    if not os.path.isabs(persistence_dir):
        persistence_dir = os.path.join(os.getcwd(), persistence_dir)
    os.makedirs(persistence_dir, exist_ok=True)
    llm = LLM(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
    )
    console.print(
        f"LLM configured: model={llm.model} base_url={getattr(llm, 'base_url', None)}"
    )

    llm_messages: list[str] = []

    def conversation_callback(event: Event):
        if isinstance(event, LLMConvertibleEvent):
            llm_messages.append(str(event.to_llm_message()))

    # Select and run one SDK example at a time
    if example == "hello_world":
        await run_hello_world(llm, conversation_callback, persistence_dir)
    elif example == "custom_tools":
        await run_custom_tools(llm, conversation_callback, persistence_dir)
    elif example == "activate_skill":
        await run_activate_skill(llm, conversation_callback, persistence_dir)
    elif example == "confirmation_mode":
        await run_confirmation_mode(
            llm,
            conversation_callback,
            persistence_dir,
            add_security_analyzer=demo_settings.add_security_analyzer,
            approve_all_actions=demo_settings.confirm_all,
        )
    elif example == "llm_registry":
        await run_llm_registry(llm, conversation_callback, persistence_dir)
    elif example == "interactive_terminal_reasoning":
        await run_interactive_terminal_with_reasoning(
            llm, conversation_callback, persistence_dir
        )
    elif example == "mcp_integration":
        await run_mcp_integration(llm, conversation_callback, persistence_dir)
    else:
        raise ValueError(f"Unknown SDK_EXAMPLE={example}")

    print("=" * 100)
    print("Conversation finished. Got the following LLM messages:")
    for i, message in enumerate(llm_messages):
        print(f"Message {i}: {message[:200]}")
    if hasattr(llm, "metrics") and hasattr(llm.metrics, "accumulated_cost"):
        print(f"EXAMPLE_COST: {llm.metrics.accumulated_cost}")
    print("All done!")


async def run_hello_world(llm: LLM, on_event, persistence_dir: str):
    agent = Agent(
        llm=llm,
        tools=[
            Tool(name="terminal"),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
        ],
    )
    cwd = os.getcwd()
    conversation = Conversation(
        agent=agent,
        callbacks=[on_event],
        workspace=cwd,
        persistence_dir=persistence_dir,
    )
    conversation.send_message("Write 3 facts about the current project into FACTS.txt.")
    conversation.run()


async def run_mcp_integration(llm: LLM, on_event, persistence_dir: str):
    cwd = os.getcwd()
    tools = [
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
    ]
    mcp_config = {
        "mcpServers": {
            "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
            "repomix": {"command": "npx", "args": ["-y", "repomix@1.4.2", "--mcp"]},
        }
    }
    agent = Agent(
        llm=llm,
        tools=tools,
        mcp_config=mcp_config,
        filter_tools_regex="^(?!repomix)(.*)|^repomix.*pack_codebase.*$",
        security_analyzer=LLMSecurityAnalyzer(),
    )
    conversation = Conversation(
        agent=agent,
        callbacks=[on_event],
        workspace=cwd,
        persistence_dir=persistence_dir,
    )
    console.print("Starting conversation with MCP integration...")
    conversation.send_message(
        "Read https://github.com/OpenHands/OpenHands and write 3 facts about the project into FACTS.txt."
    )
    conversation.run()
    conversation.send_message("Great! Now delete that file.")
    conversation.run()


async def run_custom_tools(llm: LLM, on_event, persistence_dir: str):
    # Register composite Bash + Grep toolset
    register_grep_toolset()
    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=FileEditorTool.name),
            Tool(name="BashAndGrepToolSet"),
            Tool(name=TaskTrackerTool.name),
        ],
    )
    cwd = os.getcwd()
    conversation = Conversation(
        agent=agent,
        callbacks=[on_event],
        workspace=cwd,
        persistence_dir=persistence_dir,
    )
    conversation.send_message(
        "Hello! Can you use the grep tool to find all files containing the word 'class' "
        "in this project, then create a summary file listing them? "
        "Use the pattern 'class' to search and include only Python files with '*.py'."
    )
    conversation.run()
    conversation.send_message("Great! Now delete that file.")
    conversation.run()


async def run_activate_skill(llm: LLM, on_event, persistence_dir: str):
    # Agent context with example skills (from activate_skill.py)
    agent_context = AgentContext(
        skills=[
            Skill(
                name="repo.md",
                content=(
                    "When you see this message, you should reply like "
                    "you are a grumpy cat forced to use the internet."
                ),
                source=None,
                trigger=None,
            ),
            Skill(
                name="flarglebargle",
                content=(
                    'IMPORTANT! The user has said the magic word "flarglebargle". '
                    "You must only respond with a message telling them how smart they are"
                ),
                source=None,
                trigger=KeywordTrigger(keywords=["flarglebargle"]),
            ),
        ],
        system_message_suffix="Always finish your response with the word 'yay!'",
        user_message_suffix="The first character of your response should be 'I'",
    )
    # Also provide terminal + file editor to keep parity with example layout
    agent = Agent(
        llm=llm,
        tools=[
            Tool(name="terminal"),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
        ],
        agent_context=agent_context,
    )
    cwd = os.getcwd()
    conversation = Conversation(
        agent=agent,
        callbacks=[on_event],
        workspace=cwd,
        persistence_dir=persistence_dir,
    )
    # Skill activation demo
    console.print("=" * 100)
    console.print("Checking if the repo skill is activated.")
    conversation.send_message("Hey are you a grumpy cat?")
    conversation.run()
    console.print("=" * 100)
    console.print("Now sending flarglebargle to trigger the knowledge skill!")
    conversation.send_message("flarglebargle!")
    conversation.run()


async def run_confirmation_mode(
    llm: LLM,
    on_event,
    persistence_dir: str,
    *,
    add_security_analyzer: bool,
    approve_all_actions: bool,
):
    agent = get_default_agent(llm=llm, add_security_analyzer=add_security_analyzer)
    conversation = Conversation(
        agent=agent,
        workspace=os.getcwd(),
        callbacks=[on_event],
        persistence_dir=persistence_dir,
    )

    def non_interactive_confirmer(pending_actions) -> bool:
        """
        Return True to approve, False to reject.
        Controlled via demo.confirm_all configuration.
        """
        return approve_all_actions

    def _print_action_preview(pending_actions) -> None:
        print(
            f"\n🔍 Agent created {len(pending_actions)} action(s) awaiting confirmation:"
        )
        for i, action in enumerate(pending_actions, start=1):
            snippet = str(action.action)[:100].replace("\n", " ")
            print(f"  {i}. {action.tool_name}: {snippet}...")

    def run_until_finished(conv: Conversation) -> None:
        while conv.state.execution_status != ConversationExecutionStatus.FINISHED:
            if (
                conv.state.execution_status
                == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
            ):
                pending = ConversationState.get_unmatched_actions(conv.state.events)
                if not pending:
                    raise RuntimeError(
                        "Agent is waiting for confirmation but no pending actions were found."
                    )
                _print_action_preview(pending)
                if not non_interactive_confirmer(pending):
                    conv.reject_pending_actions("Rejected by CONFIRM_ALL policy")
                    continue
            print("▶️  Running conversation.run()…")
            conv.run()

    # 1) Confirmation mode ON
    conversation.set_confirmation_policy(AlwaysConfirm())
    print("\n1) Command that will likely create actions…")
    conversation.send_message(
        "Please list the files in the current directory using ls -la"
    )
    run_until_finished(conversation)

    # 2) A command the user may choose to reject/approve
    print("\n2) Command the user may choose to reject…")
    conversation.send_message("Please create a file called 'dangerous_file.txt'")
    run_until_finished(conversation)

    # 3) Simple greeting (no actions expected)
    print("\n3) Simple greeting (no actions expected)…")
    conversation.send_message("Just say hello to me")
    run_until_finished(conversation)

    # 4) Disable confirmation mode and run commands directly
    print("\n4) Disable confirmation mode and run a command…")
    conversation.set_confirmation_policy(NeverConfirm())
    conversation.send_message("Please echo 'Hello from confirmation mode example!'")
    conversation.run()
    conversation.send_message(
        "Please delete any file that was created during this conversation."
    )
    conversation.run()

    print("\n=== Example Complete ===")
    print("Key points:")
    print(
        "- conversation.run() creates actions; confirmation mode sets WAITING_FOR_CONFIRMATION"
    )
    print(
        "- Rejection uses conversation.reject_pending_actions() and the loop continues"
    )
    print("- Simple responses work normally without actions")
    print("- Confirmation policy toggled with conversation.set_confirmation_policy()")


async def run_llm_registry(llm: LLM, on_event, persistence_dir: str):
    # Add the provided LLM to a registry and retrieve it by usage id
    llm_registry = LLMRegistry()
    llm_registry.add(llm)
    # Determine usage id used for retrieval; fall back to 'default'
    usage_id = getattr(llm, "usage_id", "default")
    reg_llm = llm_registry.get(usage_id)

    # Minimal toolset for echo demo
    agent = Agent(llm=reg_llm, tools=[Tool(name=TerminalTool.name)])
    conversation = Conversation(
        agent=agent,
        callbacks=[on_event],
        workspace=os.getcwd(),
        persistence_dir=persistence_dir,
    )

    # Quick conversation
    conversation.send_message("Please echo 'Hello!'")
    conversation.run()

    # Show registry details and direct completion
    print("=" * 100)
    print(f"LLM Registry usage IDs: {llm_registry.list_usage_ids()}")
    same_llm = llm_registry.get(usage_id)
    print(f"Same LLM instance: {reg_llm is same_llm}")

    resp = reg_llm.completion(
        messages=[
            Message(role="user", content=[TextContent(text="Say hello in one word.")])
        ]
    )
    msg = resp.message
    texts = [c.text for c in msg.content if isinstance(c, TextContent)]
    print(f"Direct completion response: {texts[0] if texts else str(msg)}")


async def run_interactive_terminal_with_reasoning(
    llm: LLM, on_event, persistence_dir: str
):
    agent = Agent(
        llm=llm,
        tools=[
            Tool(
                name=TerminalTool.name,
                params={"no_change_timeout_seconds": 3},
            )
        ],
    )
    conversation = Conversation(
        agent=agent,
        callbacks=[on_event],
        workspace=os.getcwd(),
        persistence_dir=persistence_dir,
    )
    conversation.send_message(
        "Enter python interactive mode by directly running `python3`, then tell me "
        "the current time, and exit python interactive mode."
    )
    conversation.run()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
