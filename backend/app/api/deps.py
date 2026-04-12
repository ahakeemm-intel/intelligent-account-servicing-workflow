from app.core.database import get_db

# Re-export for convenience — all routes import from here
__all__ = ["get_db"]
