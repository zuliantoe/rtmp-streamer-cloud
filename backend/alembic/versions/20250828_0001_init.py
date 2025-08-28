from alembic import op
import sqlalchemy as sa


revision = "20250828_0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("admin", "user", name="userrole"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"]) 
    op.create_index("ix_users_email", "users", ["email"]) 

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("filepath", sa.String(length=1024), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "playlists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "playlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("playlist_id", sa.Integer(), sa.ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_id", sa.Integer(), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.UniqueConstraint("playlist_id", "order_index", name="uq_playlist_order"),
    )

    op.create_table(
        "stream_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("source_type", sa.Enum("video", "playlist", name="streamsourcetype"), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("destination", sa.String(length=1024), nullable=False),
        sa.Column("mode", sa.Enum("once", "loop_video", "loop_playlist", name="streammode"), nullable=False),
        sa.Column("status", sa.Enum("running", "stopped", name="streamstatus"), nullable=False, server_default="stopped"),
        sa.Column("pid", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("avg_bitrate", sa.String(length=50), nullable=True),
    )

    op.create_table(
        "logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("logs")
    op.drop_table("stream_sessions")
    op.drop_table("playlist_items")
    op.drop_table("playlists")
    op.drop_table("videos")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS streamsourcetype")
    op.execute("DROP TYPE IF EXISTS streammode")
    op.execute("DROP TYPE IF EXISTS streamstatus")


