from __future__ import annotations

from sqlalchemy import text

from omoi_os.ticketing.db import get_engine
from omoi_os.ticketing.models import Base


def main() -> None:
    engine = get_engine()
    # Create tables
    Base.metadata.create_all(engine)
    # Optional: additional indexes that are not covered in models (kept minimal here)
    with engine.begin() as conn:
        # Ensure pgvector extension exists (PostgreSQL only)
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass
        # Create IVFFlat index for vector column if present
        try:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_tickets_embedding_vector "
                    "ON tickets USING ivfflat (embedding_vector vector_l2_ops) WITH (lists = 100)"
                )
            )
        except Exception:
            pass
        # Example of creating a GIN index on tags if needed later:
        # conn.execute(text('CREATE INDEX IF NOT EXISTS idx_tickets_tags ON tickets USING GIN ((tags));'))
        pass
    print("Database initialized.")


if __name__ == "__main__":
    main()


