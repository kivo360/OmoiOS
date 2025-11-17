"""Phase configuration loader from YAML files."""

from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from omoi_os.models.phase import PhaseModel
from omoi_os.models.board_column import BoardColumn


class PhaseOutput(BaseModel):
    """Expected output configuration."""

    type: str = Field(..., description="Output type: file, test, documentation, task")
    pattern: str = Field(..., description="Pattern to match (glob, regex, etc.)")
    required: bool = Field(True, description="Whether this output is required")
    validation_rule: Optional[str] = Field(
        None, description="Optional validation rule/script"
    )


class PhaseDefinition(BaseModel):
    """Phase configuration from YAML."""

    id: str = Field(..., description="Phase ID (e.g., PHASE_IMPLEMENTATION)")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Phase description")
    sequence_order: int = Field(..., description="Order in sequence (0-based)")
    allowed_transitions: List[str] = Field(
        default_factory=list, description="Allowed phase transitions"
    )
    is_terminal: bool = Field(False, description="Whether this is terminal phase")
    done_definitions: List[str] = Field(
        default_factory=list, description="Completion criteria"
    )
    expected_outputs: List[PhaseOutput] = Field(
        default_factory=list, description="Expected artifacts"
    )
    phase_prompt: Optional[str] = Field(None, description="Phase-level system prompt")
    next_steps_guide: List[str] = Field(
        default_factory=list, description="What happens next"
    )
    configuration: Dict[str, Any] = Field(
        default_factory=dict, description="Additional config"
    )

    @field_validator("id")
    @classmethod
    def validate_phase_id(cls, v: str) -> str:
        """Ensure phase ID starts with PHASE_."""
        if not v.startswith("PHASE_"):
            raise ValueError(f"Phase ID must start with PHASE_, got: {v}")
        return v


class BoardColumnDefinition(BaseModel):
    """Board column configuration from YAML."""

    id: str = Field(..., description="Column ID (e.g., analyzing)")
    name: str = Field(..., description="Display name with emoji")
    description: Optional[str] = Field(None, description="Column description")
    sequence_order: int = Field(..., description="Left-to-right order")
    phase_mapping: List[str] = Field(..., description="Phases that map to this column")
    wip_limit: Optional[int] = Field(None, description="WIP limit (null=unlimited)")
    is_terminal: bool = Field(False, description="End column?")
    auto_transition_to: Optional[str] = Field(
        None, description="Auto-transition target column"
    )
    color_theme: Optional[str] = Field(None, description="Color theme")


class WorkflowConfig(BaseModel):
    """Complete workflow configuration."""

    name: str = Field(..., description="Workflow name")
    has_result: bool = Field(True, description="Whether workflow produces result")
    result_criteria: Optional[str] = Field(None, description="Completion criteria")
    on_result_found: str = Field("stop_all", description="Action on completion")
    phases: List[PhaseDefinition] = Field(..., description="Phase definitions")
    board_columns: List[BoardColumnDefinition] = Field(
        default_factory=list, description="Kanban columns"
    )


class PhaseLoader:
    """
    Service for loading phase definitions from YAML configuration files.

    Supports Hephaestus-style workflow configurations with done definitions,
    expected outputs, phase prompts, and board columns.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize phase loader.

        Args:
            config_dir: Directory containing YAML phase configs.
                       Defaults to omoi_os/config/workflows/
        """
        if config_dir is None:
            self.config_dir = Path(__file__).parent.parent / "config" / "workflows"
        else:
            self.config_dir = Path(config_dir)

    def load_workflow_config(self, config_file: str) -> WorkflowConfig:
        """
        Load workflow configuration from YAML file.

        Args:
            config_file: YAML file name (e.g., "software_dev.yaml")

        Returns:
            Parsed workflow configuration.
        """
        config_path = self.config_dir / config_file

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        return WorkflowConfig(**data)

    def load_phases_to_db(
        self, session: Session, config_file: str, overwrite: bool = False
    ) -> List[PhaseModel]:
        """
        Load phases from YAML config into database.

        Args:
            session: Database session.
            config_file: YAML configuration file.
            overwrite: Whether to overwrite existing phases.

        Returns:
            List of created/updated phase records.
        """
        config = self.load_workflow_config(config_file)

        created_phases = []

        for phase_def in config.phases:
            # Check if phase exists
            existing = session.get(PhaseModel, phase_def.id)

            if existing and not overwrite:
                # Skip existing phases unless overwrite=True
                created_phases.append(existing)
                continue

            if existing and overwrite:
                # Update existing phase
                phase = existing
            else:
                # Create new phase
                phase = PhaseModel(id=phase_def.id)
                session.add(phase)

            # Update fields
            phase.name = phase_def.name
            phase.description = phase_def.description
            phase.sequence_order = phase_def.sequence_order
            phase.allowed_transitions = phase_def.allowed_transitions
            phase.is_terminal = phase_def.is_terminal
            phase.done_definitions = phase_def.done_definitions
            phase.expected_outputs = [
                output.model_dump() for output in phase_def.expected_outputs
            ]
            phase.phase_prompt = phase_def.phase_prompt
            phase.next_steps_guide = phase_def.next_steps_guide
            phase.configuration = phase_def.configuration

            session.flush()
            created_phases.append(phase)

        return created_phases

    def load_board_columns_to_db(
        self, session: Session, config_file: str, overwrite: bool = False
    ) -> List[BoardColumn]:
        """
        Load board columns from YAML config into database.

        Args:
            session: Database session.
            config_file: YAML configuration file.
            overwrite: Whether to overwrite existing columns.

        Returns:
            List of created/updated board column records.
        """
        config = self.load_workflow_config(config_file)

        created_columns = []

        for col_def in config.board_columns:
            # Check if column exists
            existing = session.get(BoardColumn, col_def.id)

            if existing and not overwrite:
                created_columns.append(existing)
                continue

            if existing and overwrite:
                column = existing
            else:
                column = BoardColumn(id=col_def.id)
                session.add(column)

            # Update fields
            column.name = col_def.name
            column.description = col_def.description
            column.sequence_order = col_def.sequence_order
            column.phase_mapping = col_def.phase_mapping
            column.wip_limit = col_def.wip_limit
            column.is_terminal = col_def.is_terminal
            column.auto_transition_to = col_def.auto_transition_to
            column.color_theme = col_def.color_theme

            session.flush()
            created_columns.append(column)

        return created_columns

    def load_complete_workflow(
        self, session: Session, config_file: str, overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Load complete workflow (phases + board columns) from YAML.

        Args:
            session: Database session.
            config_file: YAML configuration file.
            overwrite: Whether to overwrite existing data.

        Returns:
            Dictionary with loaded phases and columns.
        """
        phases = self.load_phases_to_db(session, config_file, overwrite)
        columns = self.load_board_columns_to_db(session, config_file, overwrite)

        return {
            "phases_loaded": len(phases),
            "columns_loaded": len(columns),
            "phases": [p.to_dict() for p in phases],
            "columns": [c.to_dict() for c in columns],
        }

    @staticmethod
    def export_phases_to_yaml(session: Session, output_file: Path) -> None:
        """
        Export current phase configuration to YAML file.

        Args:
            session: Database session.
            output_file: Output YAML file path.
        """
        from sqlalchemy import select

        # Get all phases
        phases = (
            session.execute(select(PhaseModel).order_by(PhaseModel.sequence_order))
            .scalars()
            .all()
        )

        # Get all board columns
        columns = (
            session.execute(select(BoardColumn).order_by(BoardColumn.sequence_order))
            .scalars()
            .all()
        )

        # Build config structure
        config = {
            "name": "Exported Workflow",
            "has_result": True,
            "result_criteria": "All phases complete",
            "on_result_found": "stop_all",
            "phases": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "sequence_order": p.sequence_order,
                    "allowed_transitions": p.allowed_transitions or [],
                    "is_terminal": p.is_terminal,
                    "done_definitions": p.done_definitions or [],
                    "expected_outputs": p.expected_outputs or [],
                    "phase_prompt": p.phase_prompt,
                    "next_steps_guide": p.next_steps_guide or [],
                    "configuration": p.configuration or {},
                }
                for p in phases
            ],
            "board_columns": [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "sequence_order": c.sequence_order,
                    "phase_mapping": c.phase_mapping,
                    "wip_limit": c.wip_limit,
                    "is_terminal": c.is_terminal,
                    "auto_transition_to": c.auto_transition_to,
                    "color_theme": c.color_theme,
                }
                for c in columns
            ],
        }

        # Write to file
        with open(output_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
