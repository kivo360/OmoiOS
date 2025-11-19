"""Auth system foundation: organizations, roles, sessions, api keys

Revision ID: 030_auth_system_foundation
Revises: 7b9a14289450
Create Date: 2025-11-19 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid import uuid4

# Import migration utilities
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from migration_utils import (
    safe_create_table,
    safe_add_column,
    safe_create_index,
    safe_create_foreign_key,
    safe_drop_table,
    safe_drop_column,
    safe_drop_index,
    safe_drop_constraint,
    table_exists,
    column_exists,
    print_migration_summary,
)

# revision identifiers
revision = '030_auth_system_foundation'
down_revision = '7b9a14289450'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create auth system foundation tables."""
    
    print("\n🔄 Starting auth system foundation migration...")
    print_migration_summary()
    
    # 1. Modify users table - Add new auth fields
    print("\n📝 Adding new fields to users table...")
    safe_add_column('users', sa.Column('hashed_password', sa.String(255), nullable=True))
    safe_add_column('users', sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False))
    safe_add_column('users', sa.Column('is_super_admin', sa.Boolean(), server_default='false', nullable=False))
    safe_add_column('users', sa.Column('department', sa.String(100), nullable=True))
    safe_add_column('users', sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    safe_add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    
    # Migrate existing data
    if column_exists('users', 'email_confirmed_at') and column_exists('users', 'is_verified'):
        print("📊 Migrating existing user data...")
        op.execute("UPDATE users SET is_verified = (email_confirmed_at IS NOT NULL) WHERE is_verified = false")
    
    # Add indexes
    print("\n🔍 Adding indexes to users table...")
    safe_create_index('idx_users_department', 'users', ['department'])
    safe_create_index('idx_users_is_super_admin', 'users', ['is_super_admin'],
                     postgresql_where=sa.text('is_super_admin = true'))
    
    # 2. Create organizations table
    print("\n🏢 Creating organizations table...")
    safe_create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('billing_email', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('org_attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('max_concurrent_agents', sa.Integer(), server_default='5', nullable=False),
        sa.Column('max_agent_runtime_hours', sa.Float(), server_default='100.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name='fk_organizations_owner'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_organizations_slug'),
        sa.CheckConstraint("slug ~ '^[a-z0-9-]+$'", name='check_slug_format'),
        comment='Organizations for multi-tenant resource isolation'
    )
    
    # Add indexes
    print("\n🔍 Adding indexes to organizations table...")
    safe_create_index('idx_organizations_owner', 'organizations', ['owner_id'])
    safe_create_index('idx_organizations_slug', 'organizations', ['slug'], unique=True)
    
    # 3. Create roles table
    print("\n👥 Creating roles table...")
    safe_create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_system', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('inherits_from', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], 
                                name='fk_roles_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inherits_from'], ['roles.id'], 
                                name='fk_roles_parent', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='Roles for RBAC permission management'
    )
    
    safe_create_index('idx_org_role_name', 'roles', ['organization_id', 'name'], unique=True)
    safe_create_index('idx_roles_inherits', 'roles', ['inherits_from'])
    
    # 4. Create organization_memberships table
    # Note: agent_id uses VARCHAR to match existing agents table
    print("\n🤝 Creating organization_memberships table...")
    safe_create_table(
        'organization_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_id', sa.String(), nullable=True),  # VARCHAR to match agents.id
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint(
            '(user_id IS NOT NULL AND agent_id IS NULL) OR (user_id IS NULL AND agent_id IS NOT NULL)',
            name='check_user_or_agent'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], 
                                name='fk_org_memberships_user', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], 
                                name='fk_org_memberships_agent', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_org_memberships_org', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'],
                                name='fk_org_memberships_role'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'],
                                name='fk_org_memberships_inviter'),
        sa.PrimaryKeyConstraint('id'),
        comment='Organization membership for users and agents'
    )
    
    safe_create_index('idx_org_memberships_user', 'organization_memberships', ['user_id'])
    safe_create_index('idx_org_memberships_agent', 'organization_memberships', ['agent_id'])
    safe_create_index('idx_org_memberships_org', 'organization_memberships', ['organization_id'])
    safe_create_index('idx_user_org', 'organization_memberships', ['user_id', 'organization_id'],
                     unique=True, postgresql_where=sa.text('user_id IS NOT NULL'))
    safe_create_index('idx_agent_org', 'organization_memberships', ['agent_id', 'organization_id'],
                     unique=True, postgresql_where=sa.text('agent_id IS NOT NULL'))
    
    # 5. Create sessions table
    print("\n🔐 Creating sessions table...")
    safe_create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], 
                                name='fk_sessions_user', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_sessions_token_hash'),
        comment='User sessions for web/mobile clients'
    )
    
    safe_create_index('idx_sessions_user', 'sessions', ['user_id'])
    safe_create_index('idx_sessions_token_hash', 'sessions', ['token_hash'], unique=True)
    safe_create_index('idx_sessions_expires', 'sessions', ['expires_at'])
    
    # 6. Create api_keys table
    # Note: agent_id uses VARCHAR to match existing agents table
    print("\n🔑 Creating api_keys table...")
    safe_create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_id', sa.String(), nullable=True),  # VARCHAR to match agents.id
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(16), nullable=False),
        sa.Column('hashed_key', sa.String(255), nullable=False),
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint(
            '(user_id IS NOT NULL AND agent_id IS NULL) OR (user_id IS NULL AND agent_id IS NOT NULL)',
            name='check_key_user_or_agent'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], 
                                name='fk_api_keys_user', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], 
                                name='fk_api_keys_agent', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_api_keys_org', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hashed_key', name='uq_api_keys_hashed_key'),
        comment='API keys for programmatic access'
    )
    
    safe_create_index('idx_api_keys_user', 'api_keys', ['user_id'],
                     postgresql_where=sa.text('user_id IS NOT NULL'))
    safe_create_index('idx_api_keys_agent', 'api_keys', ['agent_id'],
                     postgresql_where=sa.text('agent_id IS NOT NULL'))
    safe_create_index('idx_api_keys_prefix', 'api_keys', ['key_prefix'])
    safe_create_index('idx_api_keys_hash', 'api_keys', ['hashed_key'], unique=True)
    safe_create_index('idx_api_keys_active', 'api_keys', ['is_active'],
                     postgresql_where=sa.text('is_active = true'))
    
    # 7. Seed system roles
    if table_exists('roles'):
        print("\n🌱 Seeding system roles...")
        op.execute("""
            INSERT INTO roles (id, organization_id, name, description, permissions, is_system, inherits_from, created_at)
            VALUES 
                (gen_random_uuid(), NULL, 'owner', 'Organization owner with full control',
                 '["org:*", "project:*", "document:*", "ticket:*", "task:*", "agent:*"]'::jsonb,
                 true, NULL, NOW()),
                (gen_random_uuid(), NULL, 'admin', 'Administrator with management permissions',
                 '["org:read", "org:write", "org:members:*", "project:*", "document:*", "ticket:*", "task:*", "agent:read"]'::jsonb,
                 true, NULL, NOW()),
                (gen_random_uuid(), NULL, 'member', 'Standard organization member',
                 '["org:read", "project:read", "project:write", "document:read", "document:write", "ticket:read", "ticket:write", "task:read", "task:write", "agent:read"]'::jsonb,
                 true, NULL, NOW()),
                (gen_random_uuid(), NULL, 'viewer', 'Read-only access',
                 '["org:read", "project:read", "document:read", "ticket:read", "task:read", "agent:read"]'::jsonb,
                 true, NULL, NOW()),
                (gen_random_uuid(), NULL, 'agent_executor', 'Role for AI agents',
                 '["project:read", "document:read", "document:write", "ticket:read", "ticket:write", "task:read", "task:write", "task:complete:execute", "project:git:write"]'::jsonb,
                 true, NULL, NOW())
            ON CONFLICT DO NOTHING
        """)
        print("✓ Seeded 5 system roles")
    
    # 8. Add organization_id to projects table
    print("\n📁 Adding organization fields to projects table...")
    safe_add_column('projects',
                   sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
    safe_add_column('projects',
                   sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    
    safe_create_foreign_key('fk_projects_organization', 'projects', 'organizations',
                           ['organization_id'], ['id'], ondelete='CASCADE')
    safe_create_foreign_key('fk_projects_creator', 'projects', 'users',
                           ['created_by'], ['id'])
    
    safe_create_index('idx_projects_organization', 'projects', ['organization_id'])
    safe_create_index('idx_projects_creator', 'projects', ['created_by'])
    
    print("\n✅ Auth system foundation migration completed!")
    print_migration_summary()


def downgrade() -> None:
    """Rollback auth system foundation."""
    
    print("\n🔄 Rolling back auth system foundation migration...")
    
    # Drop project foreign keys and columns
    print("\n📁 Removing organization fields from projects table...")
    safe_drop_constraint('fk_projects_organization', 'projects', type_='foreignkey')
    safe_drop_constraint('fk_projects_creator', 'projects', type_='foreignkey')
    safe_drop_index('idx_projects_organization', 'projects')
    safe_drop_index('idx_projects_creator', 'projects')
    safe_drop_column('projects', 'organization_id')
    safe_drop_column('projects', 'created_by')
    
    # Drop tables in reverse order
    print("\n🗑️  Dropping auth tables...")
    safe_drop_table('api_keys')
    safe_drop_table('sessions')
    safe_drop_table('organization_memberships')
    safe_drop_table('roles')
    safe_drop_table('organizations')
    
    # Revert user changes
    print("\n📝 Reverting users table changes...")
    safe_drop_index('idx_users_is_super_admin', 'users')
    safe_drop_index('idx_users_department', 'users')
    safe_drop_column('users', 'last_login_at')
    safe_drop_column('users', 'attributes')
    safe_drop_column('users', 'department')
    safe_drop_column('users', 'is_super_admin')
    safe_drop_column('users', 'is_verified')
    safe_drop_column('users', 'hashed_password')
    
    print("\n✅ Rollback completed!")
    print_migration_summary()

