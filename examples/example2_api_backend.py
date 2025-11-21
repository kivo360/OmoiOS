"""Example: FastAPI backend for running ticket agents.

This example demonstrates a simple FastAPI endpoint that accepts ticket requests
and runs OpenHands agents in isolated workspaces.

Usage:
    # Set environment variables
    export LLM_API_KEY=your-api-key
    export LLM_MODEL=openhands/claude-sonnet-4-5-20250929  # optional

    # Run the API server
    uv run uvicorn examples.example2_api_backend:app --host 0.0.0.0 --port 18001 --reload

    # Test the endpoint
    curl -X POST http://localhost:18001/api/tickets/run \\
        -H "Content-Type: application/json" \\
        -d '{
            "ticket_id": "T-123",
            "title": "Add /health endpoint",
            "description": "Add a /health endpoint that returns JSON {status, version}",
            "workspace_dir": "/tmp/workspace-t123"
        }'
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from openhands.sdk import Agent, Conversation, LLM, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

from omoi_os.config import load_llm_settings

app = FastAPI(
    title="Ticket Agent API Example",
    description="Simple API for running OpenHands agents on tickets",
    version="0.1.0",
)


# Request/Response Models
class RunTicketRequest(BaseModel):
    """Request model for running a ticket agent."""
    
    ticket_id: str = Field(..., description="Unique identifier for the ticket")
    title: str = Field(..., description="Ticket title")
    description: str = Field(..., description="Detailed ticket description")
    workspace_dir: str = Field(
        ...,
        description="Directory path for the isolated workspace (will be created if needed)"
    )


class RunTicketResponse(BaseModel):
    """Response model for ticket execution."""
    
    ticket_id: str = Field(..., description="Ticket ID that was executed")
    status: str = Field(..., description="Execution status (e.g., 'completed', 'failed')")
    summary: str = Field(..., description="Final summary message from the agent")


def build_llm() -> LLM:
    """Build LLM instance using project configuration."""
    llm_settings = load_llm_settings()
    
    if not llm_settings.api_key:
        raise RuntimeError(
            "LLM_API_KEY must be set in environment or config. "
            "Set LLM_API_KEY in your environment or config/base.yaml"
        )
    
    return LLM(
        usage_id="ticket-agent",
        model=llm_settings.model,
        base_url=llm_settings.base_url,
        api_key=llm_settings.api_key,
    )


def build_agent(llm: LLM) -> Agent:
    """Build agent with file editor and terminal tools."""
    tools = [
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
    ]
    return Agent(llm=llm, tools=tools)


def run_agent_for_ticket_sync(req: RunTicketRequest) -> RunTicketResponse:
    """Run agent for a single ticket synchronously.
    
    Args:
        req: Ticket request with ID, title, description, and workspace directory
        
    Returns:
        Response with ticket ID, execution status, and summary
        
    Raises:
        RuntimeError: If LLM configuration is missing
        ValueError: If workspace directory cannot be created
    """
    llm = build_llm()
    agent = build_agent(llm)
    
    # Ensure workspace directory exists
    workspace_path = Path(req.workspace_dir)
    try:
        workspace_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"Failed to create workspace directory: {e}")
    
    conversation = Conversation(
        agent=agent,
        workspace=str(workspace_path.absolute()),
    )
    
    goal_prompt = f"""
You are working on ticket {req.ticket_id}: {req.title}

Ticket description:
{req.description}

Instructions:
- Work directly in this repository.
- Use terminal + file editor tools to complete the work.
- When done, summarize what you changed (files, behavior, tests).
"""
    
    conversation.send_message(goal_prompt)
    conversation.run()
    
    state = conversation.state
    last_msg = state.messages[-1] if state.messages else None
    last_text = getattr(last_msg, "content", "") if last_msg else ""
    
    return RunTicketResponse(
        ticket_id=req.ticket_id,
        status=state.execution_status.value if hasattr(state.execution_status, 'value') else str(state.execution_status),
        summary=last_text,
    )


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "Ticket Agent API Example",
        "version": "0.1.0",
        "endpoints": {
            "run_ticket": "/api/tickets/run",
            "docs": "/docs",
            "health": "/health",
        }
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/tickets/run", response_model=RunTicketResponse)
def run_ticket(req: RunTicketRequest):
    """Run an agent for a single ticket.
    
    This endpoint accepts a ticket request and runs an OpenHands agent
    in an isolated workspace to complete the ticket.
    
    Args:
        req: Ticket request with ID, title, description, and workspace directory
        
    Returns:
        Response with execution status and summary
        
    Raises:
        HTTPException: If execution fails or configuration is invalid
    """
    try:
        result = run_agent_for_ticket_sync(req)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    # Run on port 18001 to avoid conflict with main API (18000)
    uvicorn.run(app, host="0.0.0.0", port=18001)

