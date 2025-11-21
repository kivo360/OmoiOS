"""Workspace isolation system: agent workspaces, commits, and merge conflict tracking.

Revision ID: 031_workspace_isolation_system
Revises: 030_auth_system_foundation
Create Date: 2025-01-XX 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Import migration utilities
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from migration_utils import (
    safe_create_table,
    safe_create_index,
    safe_create_foreign_key,
    safe_drop_table,
    safe_drop_index,
    safe_drop_constraint,
    print_migration_summary,
)

# revision identifiers
revision = "031_workspace_isolation_system"
down_revision = "030_auth_system_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create workspace isolation system tables."""

    print("\n🔄 Starting workspace isolation system migration...")
    print_migration_summary()

    # 1. Create agent_workspaces table
    print("\n📁 Creating agent_workspaces table...")
    safe_create_table(
        "agent_workspaces",
        sa.Column(
            "agent_id",
            sa.String(),
            primary_key=True,
            comment="Agent identifier (foreign key to agents table)",
        ),
        sa.Column(
            "working_directory",
            sa.String(1000),
            nullable=False,
            comment="Absolute path to workspace directory",
        ),
        sa.Column(
            "branch_name",
            sa.String(255),
            nullable=False,
            comment="Git branch name for this workspace (e.g., workspace-agent-123)",
        ),
        sa.Column(
            "parent_commit",
            sa.String(40),
            nullable=True,
            comment="Parent commit SHA for workspace inheritance",
        ),
        sa.Column(
            "parent_agent_id",
            sa.String(),
            nullable=True,
            comment="Parent agent ID for workspace inheritance",
        ),
        sa.Column(
            "repo_url",
            sa.String(500),
            nullable=True,
            comment="Repository URL that was cloned into this workspace",
        ),
        sa.Column(
            "base_branch",
            sa.String(255),
            nullable=False,
            server_default="main",
            comment="Base branch that workspace was created from",
        ),
        sa.Column(
            "workspace_type",
            sa.String(50),
            nullable=False,
            server_default="local",
            comment="Workspace type: local, docker, kubernetes, remote",
        ),
        sa.Column(
            "workspace_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Workspace-specific configuration (e.g., Docker port, image)",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether workspace is currently active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("agent_id"),
        comment="Tracks workspace paths, Git branches, and parent-child relationships",
    )

    # Add foreign keys
    print("\n🔗 Adding foreign keys to agent_workspaces table...")
    safe_create_foreign_key(
        "fk_agent_workspaces_agent",
        "agent_workspaces",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    safe_create_foreign_key(
        "fk_agent_workspaces_parent",
        "agent_workspaces",
        "agents",
        ["parent_agent_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add indexes
    print("\n🔍 Adding indexes to agent_workspaces table...")
    safe_create_index(
        "idx_agent_workspaces_branch", "agent_workspaces", ["branch_name"]
    )
    safe_create_index(
        "idx_agent_workspaces_parent", "agent_workspaces", ["parent_agent_id"]
    )
    safe_create_index("idx_agent_workspaces_active", "agent_workspaces", ["is_active"])

    # 2. Create workspace_commits table
    print("\n📝 Creating workspace_commits table...")
    safe_create_table(
        "workspace_commits",
        sa.Column(
            "id",
            sa.String(),
            primary_key=True,
            comment="Unique commit record identifier",
        ),
        sa.Column(
            "agent_id",
            sa.String(),
            nullable=False,
            comment="Agent identifier",
        ),
        sa.Column(
            "commit_sha",
            sa.String(40),
            nullable=False,
            comment="Git commit SHA",
        ),
        sa.Column(
            "files_changed",
            sa.Integer(),
            nullable=False,
            comment="Number of files changed in this commit",
        ),
        sa.Column(
            "message",
            sa.Text(),
            nullable=False,
            comment="Git commit message",
        ),
        sa.Column(
            "iteration",
            sa.Integer(),
            nullable=True,
            comment="Iteration number for validation checkpoints",
        ),
        sa.Column(
            "commit_type",
            sa.String(50),
            nullable=False,
            server_default="validation",
            comment="Commit type: validation, checkpoint, merge, manual",
        ),
        sa.Column(
            "commit_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional commit metadata (stats, diff summary, etc.)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Stores checkpoint commits for validation, debugging, and auditing",
    )

    # Add foreign key
    print("\n🔗 Adding foreign key to workspace_commits table...")
    safe_create_foreign_key(
        "fk_workspace_commits_agent",
        "workspace_commits",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add indexes
    print("\n🔍 Adding indexes to workspace_commits table...")
    safe_create_index("idx_workspace_commits_agent", "workspace_commits", ["agent_id"])
    safe_create_index("idx_workspace_commits_sha", "workspace_commits", ["commit_sha"])
    safe_create_index(
        "idx_workspace_commits_iteration", "workspace_commits", ["iteration"]
    )
    safe_create_index(
        "idx_workspace_commits_type", "workspace_commits", ["commit_type"]
    )
    safe_create_index(
        "idx_workspace_commits_created", "workspace_commits", ["created_at"]
    )

    # 3. Create merge_conflict_resolutions table
    print("\n🔀 Creating merge_conflict_resolutions table...")
    safe_create_table(
        "merge_conflict_resolutions",
        sa.Column(
            "id",
            sa.String(),
            primary_key=True,
            comment="Unique merge resolution record identifier",
        ),
        sa.Column(
            "agent_id",
            sa.String(),
            nullable=False,
            comment="Agent identifier",
        ),
        sa.Column(
            "merge_commit_sha",
            sa.String(40),
            nullable=False,
            comment="Git commit SHA of the merge",
        ),
        sa.Column(
            "target_branch",
            sa.String(255),
            nullable=False,
            comment="Target branch that was merged into",
        ),
        sa.Column(
            "source_branch",
            sa.String(255),
            nullable=False,
            comment="Source workspace branch that was merged",
        ),
        sa.Column(
            "conflicts_resolved",
            postgresql.ARRAY(sa.String(1000)),
            nullable=False,
            server_default="{}",
            comment="List of file paths that had conflicts resolved",
        ),
        sa.Column(
            "resolution_strategy",
            sa.String(100),
            nullable=False,
            server_default="newest_file_wins",
            comment="Strategy used for conflict resolution",
        ),
        sa.Column(
            "total_conflicts",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Total number of conflicts resolved",
        ),
        sa.Column(
            "merge_extra_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional merge metadata (stats, timing, etc.)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Logs automatic conflict resolutions and merge metadata",
    )

    # Add foreign key
    print("\n🔗 Adding foreign key to merge_conflict_resolutions table...")
    safe_create_foreign_key(
        "fk_merge_conflicts_agent",
        "merge_conflict_resolutions",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add indexes
    print("\n🔍 Adding indexes to merge_conflict_resolutions table...")
    safe_create_index(
        "idx_merge_conflicts_agent", "merge_conflict_resolutions", ["agent_id"]
    )
    safe_create_index(
        "idx_merge_conflicts_commit", "merge_conflict_resolutions", ["merge_commit_sha"]
    )
    safe_create_index(
        "idx_merge_conflicts_created", "merge_conflict_resolutions", ["created_at"]
    )

    print("\n✅ Workspace isolation system migration completed!")
    print_migration_summary()


def downgrade() -> None:
    """Rollback workspace isolation system."""

    print("\n🔄 Rolling back workspace isolation system migration...")

    # Drop indexes and foreign keys first, then tables
    print("\n🔍 Dropping indexes from merge_conflict_resolutions table...")
    safe_drop_index("idx_merge_conflicts_created", "merge_conflict_resolutions")
    safe_drop_index("idx_merge_conflicts_commit", "merge_conflict_resolutions")
    safe_drop_index("idx_merge_conflicts_agent", "merge_conflict_resolutions")
    safe_drop_constraint(
        "fk_merge_conflicts_agent", "merge_conflict_resolutions", type_="foreignkey"
    )

    print("\n🔀 Dropping merge_conflict_resolutions table...")
    safe_drop_table("merge_conflict_resolutions")

    print("\n🔍 Dropping indexes from workspace_commits table...")
    safe_drop_index("idx_workspace_commits_created", "workspace_commits")
    safe_drop_index("idx_workspace_commits_type", "workspace_commits")
    safe_drop_index("idx_workspace_commits_iteration", "workspace_commits")
    safe_drop_index("idx_workspace_commits_sha", "workspace_commits")
    safe_drop_index("idx_workspace_commits_agent", "workspace_commits")
    safe_drop_constraint(
        "fk_workspace_commits_agent", "workspace_commits", type_="foreignkey"
    )

    print("\n📝 Dropping workspace_commits table...")
    safe_drop_table("workspace_commits")

    print("\n🔍 Dropping indexes from agent_workspaces table...")
    safe_drop_index("idx_agent_workspaces_active", "agent_workspaces")
    safe_drop_index("idx_agent_workspaces_parent", "agent_workspaces")
    safe_drop_index("idx_agent_workspaces_branch", "agent_workspaces")
    safe_drop_constraint(
        "fk_agent_workspaces_parent", "agent_workspaces", type_="foreignkey"
    )
    safe_drop_constraint(
        "fk_agent_workspaces_agent", "agent_workspaces", type_="foreignkey"
    )

    print("\n📁 Dropping agent_workspaces table...")
    safe_drop_table("agent_workspaces")

    print("\n✅ Rollback completed!")
    print_migration_summary()
