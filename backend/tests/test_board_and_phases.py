"""Tests for board service and phase loader."""

import pytest
from pathlib import Path

from omoi_os.models.ticket import Ticket
from omoi_os.models.board_column import BoardColumn
from omoi_os.models.phase import PhaseModel
from omoi_os.services.board import BoardService
from omoi_os.services.phase_loader import PhaseLoader, WorkflowConfig


@pytest.fixture
def test_ticket(db_service):
    """Create a test ticket."""
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Board Ticket",
            description="Test ticket for board operations",
            phase_id="PHASE_IMPLEMENTATION",
            priority="MEDIUM",
            status="open",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)
        return ticket


@pytest.fixture
def board_service():
    """Fixture for board service."""
    return BoardService(event_bus=None)


def test_load_yaml_workflow_config():
    """Test loading workflow configuration from YAML."""
    loader = PhaseLoader()
    config_file = "software_development.yaml"
    
    # This should load the example YAML file
    config = loader.load_workflow_config(config_file)
    
    assert isinstance(config, WorkflowConfig)
    assert config.name == "Software Development"
    assert config.has_result is True
    assert len(config.phases) > 0
    assert len(config.board_columns) > 0


def test_load_phases_from_yaml_to_db(db_service):
    """Test loading phases from YAML into database."""
    loader = PhaseLoader()
    
    with db_service.get_session() as session:
        phases = loader.load_phases_to_db(
            session=session,
            config_file="software_development.yaml",
            overwrite=True  # Overwrite default phases
        )
        session.commit()
        
        assert len(phases) > 0
        # Check enhanced fields are populated
        impl_phase = session.get(PhaseModel, "PHASE_IMPLEMENTATION")
        assert impl_phase is not None
        assert impl_phase.done_definitions is not None
        assert len(impl_phase.done_definitions) > 0
        assert impl_phase.phase_prompt is not None
        assert "SOFTWARE ENGINEER" in impl_phase.phase_prompt


def test_load_board_columns_from_yaml(db_service):
    """Test loading board columns from YAML."""
    loader = PhaseLoader()
    
    with db_service.get_session() as session:
        columns = loader.load_board_columns_to_db(
            session=session,
            config_file="software_development.yaml",
            overwrite=True
        )
        session.commit()
        
        assert len(columns) > 0
        # Check building column
        building = session.get(BoardColumn, "building")
        assert building is not None
        assert building.wip_limit == 10
        assert building.auto_transition_to == "testing"


def test_board_view(db_service, board_service, test_ticket):
    """Test getting board view with tickets."""
    with db_service.get_session() as session:
        # Load board columns first
        loader = PhaseLoader()
        loader.load_board_columns_to_db(
            session=session,
            config_file="software_development.yaml",
            overwrite=True
        )
        session.commit()
        
        # Get board view
        board = board_service.get_board_view(session=session)
        
        assert "columns" in board
        assert len(board["columns"]) > 0
        
        # Should have building column with our test ticket
        building_col = next(
            (c for c in board["columns"] if c["id"] == "building"), None
        )
        assert building_col is not None
        assert building_col["current_count"] >= 1  # Our test ticket


def test_move_ticket_to_column(db_service, board_service, test_ticket):
    """Test moving ticket between board columns."""
    with db_service.get_session() as session:
        # Load board columns
        loader = PhaseLoader()
        loader.load_board_columns_to_db(
            session=session,
            config_file="software_development.yaml",
            overwrite=True
        )
        session.commit()
        
        # Move ticket to testing column
        updated_ticket = board_service.move_ticket_to_column(
            session=session,
            ticket_id=test_ticket.id,
            target_column_id="testing",
            force=False
        )
        session.commit()
        
        assert updated_ticket.phase_id == "PHASE_TESTING"


def test_wip_limit_enforcement(db_service, board_service):
    """Test that WIP limits are enforced."""
    with db_service.get_session() as session:
        # Load board with WIP limits
        loader = PhaseLoader()
        loader.load_board_columns_to_db(
            session=session,
            config_file="software_development.yaml",
            overwrite=True
        )
        session.commit()
        
        # Create tickets up to WIP limit for building column (limit=10)
        tickets = []
        for i in range(12):  # Exceed limit
            ticket = Ticket(
                title=f"Ticket {i}",
                description=f"Test ticket {i}",
                phase_id="PHASE_IMPLEMENTATION",
                priority="MEDIUM",
                status="open",
            )
            session.add(ticket)
            tickets.append(ticket)
        session.commit()
        
        # Check WIP violations
        violations = board_service.check_wip_limits(session=session)
        
        # Should have violation for building column
        assert len(violations) > 0
        building_violation = next(
            (v for v in violations if v["column_id"] == "building"), None
        )
        assert building_violation is not None
        assert building_violation["current_count"] > building_violation["wip_limit"]


def test_column_stats(db_service, board_service, test_ticket):
    """Test getting column statistics."""
    with db_service.get_session() as session:
        # Load board
        loader = PhaseLoader()
        loader.load_board_columns_to_db(
            session=session,
            config_file="software_development.yaml",
            overwrite=True
        )
        session.commit()
        
        # Get stats
        stats = board_service.get_column_stats(session=session)
        
        assert len(stats) > 0
        # Each stat should have expected fields
        for stat in stats:
            assert "column_id" in stat
            assert "ticket_count" in stat
            assert "wip_limit" in stat
            assert "wip_exceeded" in stat


def test_phase_done_criteria_validation(db_service):
    """Test phase done criteria validation."""
    loader = PhaseLoader()
    
    with db_service.get_session() as session:
        # Load phases with done definitions
        loader.load_phases_to_db(
            session=session,
            config_file="software_development.yaml",
            overwrite=True
        )
        session.commit()
        
        # Get implementation phase
        phase = session.get(PhaseModel, "PHASE_IMPLEMENTATION")
        assert phase is not None
        
        # Test partial completion
        completed = [
            "Component code files created in src/",
            "Minimum 3 test cases written",
        ]
        all_met, missing = phase.is_done_criteria_met(completed)
        
        assert all_met is False
        assert len(missing) > 0
        assert "Tests passing locally" in missing
        
        # Test full completion
        all_completed = phase.done_definitions[:]
        all_met, missing = phase.is_done_criteria_met(all_completed)
        
        assert all_met is True
        assert len(missing) == 0


def test_export_phases_to_yaml(db_service, tmp_path):
    """Test exporting phases back to YAML."""
    loader = PhaseLoader()
    
    with db_service.get_session() as session:
        # Load phases
        loader.load_complete_workflow(
            session=session,
            config_file="software_development.yaml",
            overwrite=True
        )
        session.commit()
        
        # Export to temp file
        output_file = tmp_path / "exported_workflow.yaml"
        PhaseLoader.export_phases_to_yaml(session=session, output_file=output_file)
        
        assert output_file.exists()
        
        # Verify can be loaded back
        loader2 = PhaseLoader(config_dir=tmp_path)
        config = loader2.load_workflow_config("exported_workflow.yaml")
        
        assert config.name == "Exported Workflow"
        assert len(config.phases) > 0
        assert len(config.board_columns) > 0

