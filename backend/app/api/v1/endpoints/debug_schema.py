"""
Debug endpoint to check database schema
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db

router = APIRouter()


@router.get("/schema/users")
async def check_users_schema(db: AsyncSession = Depends(get_db)):
    """
    Check the actual schema of the users table in the database
    """
    try:
        # Query the information_schema to get column details
        query = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)

        result = await db.execute(query)
        columns = [
            {
                "name": row[0],
                "type": row[1],
                "nullable": row[2]
            }
            for row in result.fetchall()
        ]

        # Also check alembic version
        version_query = text("SELECT version_num FROM alembic_version")
        version_result = await db.execute(version_query)
        version = version_result.scalar_one_or_none()

        return {
            "alembic_version": version,
            "columns": columns,
            "has_is_deleted": any(col["name"] == "is_deleted" for col in columns),
            "has_deleted_at": any(col["name"] == "deleted_at" for col in columns)
        }
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__
        }
