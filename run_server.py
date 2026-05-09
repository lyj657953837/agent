"""Convenience script to run the Analysis Agent System server."""
import uvicorn
from analysis_agent_system.app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "analysis_agent_system.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
