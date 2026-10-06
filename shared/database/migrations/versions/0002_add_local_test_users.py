"""Add password_hash and seed local test users

Revision ID: 0002_add_local_test_users
Revises: 0001_initial_schema
Create Date: 2026-10-07

"""
import bcrypt
import sqlalchemy as sa
from alembic import op

revision = "0002_add_local_test_users"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

# Local/test-only credentials — never used once CIH/SSO replaces this auth
# provider. Same password for every seeded account, documented in
# docs/environment-variables.md.
TEST_PASSWORD = "Test@12345"

TEST_USERS = [
    ("requestor1", "requestor1@test.local", "Test Requestor One", "REQUESTOR"),
    ("requestor2", "requestor2@test.local", "Test Requestor Two", "REQUESTOR"),
    ("zoneadmin1", "zoneadmin1@test.local", "Test Zone Admin One", "ZONE_ADMIN"),
    ("zoneadmin2", "zoneadmin2@test.local", "Test Zone Admin Two", "ZONE_ADMIN"),
    ("cloudopsadmin1", "cloudopsadmin1@test.local", "Test CloudOps Admin One", "CLOUDOPS_ADMIN"),
    ("cloudopsadmin2", "cloudopsadmin2@test.local", "Test CloudOps Admin Two", "CLOUDOPS_ADMIN"),
]


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=False, server_default=""))
    op.alter_column("users", "password_hash", server_default=None)

    conn = op.get_bind()
    password_hash = bcrypt.hashpw(TEST_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    users_table = sa.table(
        "users",
        sa.column("id", sa.BigInteger),
        sa.column("username", sa.String),
        sa.column("email", sa.String),
        sa.column("display_name", sa.String),
        sa.column("password_hash", sa.String),
    )
    roles_table = sa.table("roles", sa.column("id", sa.BigInteger), sa.column("name", sa.String))
    user_roles_table = sa.table(
        "user_roles", sa.column("user_id", sa.BigInteger), sa.column("role_id", sa.BigInteger)
    )

    role_ids = {
        row.name: row.id for row in conn.execute(sa.select(roles_table.c.name, roles_table.c.id)).all()
    }

    for username, email, display_name, role_name in TEST_USERS:
        result = conn.execute(
            sa.insert(users_table)
            .values(
                username=username,
                email=email,
                display_name=display_name,
                password_hash=password_hash,
            )
            .returning(users_table.c.id)
        )
        user_id = result.scalar_one()
        conn.execute(sa.insert(user_roles_table).values(user_id=user_id, role_id=role_ids[role_name]))


def downgrade() -> None:
    conn = op.get_bind()
    usernames = [u[0] for u in TEST_USERS]
    conn.execute(sa.text("DELETE FROM user_roles WHERE user_id IN (SELECT id FROM users WHERE username = ANY(:u))").bindparams(u=usernames))
    conn.execute(sa.text("DELETE FROM users WHERE username = ANY(:u)").bindparams(u=usernames))
    op.drop_column("users", "password_hash")
