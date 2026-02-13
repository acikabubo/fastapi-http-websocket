"""
Profiling endpoints for Scalene performance analysis.

Provides endpoints to check profiling status and access profiling reports.
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.utils.profiling import get_profiling_status, profiling_manager

router = APIRouter(prefix="/api/profiling", tags=["profiling"])


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """
    Get current profiling configuration and status.

    Public endpoint - available for development and debugging.

    Returns profiling configuration, availability of Scalene,
    and instructions for running profiling.

    Returns:
        Dictionary containing profiling status and configuration.

    Example:
        GET /api/profiling/status

        Response:
        {
            "enabled": false,
            "scalene_installed": false,
            "output_directory": "profiling_reports",
            "interval_seconds": 30,
            "python_version": "3.13.0",
            "command": "scalene --html --outfile report.html -- uvicorn ..."
        }
    """
    return get_profiling_status()


@router.get("/reports")
async def list_reports() -> dict[str, Any]:
    """
    List all available profiling reports.

    Public endpoint - available for development and debugging.

    Returns a list of profiling report files with metadata.

    Returns:
        Dictionary containing list of available reports.

    Example:
        GET /api/profiling/reports

        Response:
        {
            "reports": [
                {
                    "filename": "websocket_profile_20250123_143000.html",
                    "path": "profiling_reports/websocket_profile_20250123_143000.html",
                    "size_bytes": 125000,
                    "created_at": "2025-01-23T14:30:00"
                }
            ],
            "total_count": 1
        }
    """
    if not profiling_manager.output_dir.exists():
        return {"reports": [], "total_count": 0}

    reports = []
    for report_file in profiling_manager.output_dir.glob("*.html"):
        stat = report_file.stat()
        reports.append(
            {
                "filename": report_file.name,
                "path": str(report_file.relative_to(Path.cwd())),
                "size_bytes": stat.st_size,
                "created_at": (
                    stat.st_ctime
                ),  # Unix timestamp, convert to ISO if needed
            }
        )

    # Sort by creation time, newest first
    reports.sort(key=lambda x: x["created_at"], reverse=True)  # type: ignore[arg-type,return-value]

    return {"reports": reports, "total_count": len(reports)}


@router.get("/reports/{filename}")
async def get_report(filename: str) -> FileResponse:
    """
    Download a specific profiling report.

    Public endpoint - available for development and debugging.

    Args:
        filename: Name of the report file (e.g., websocket_profile_20250123_143000.html)

    Returns:
        HTML file containing the Scalene profiling report.

    Raises:
        HTTPException: If report file is not found or invalid.

    Example:
        GET /api/profiling/reports/websocket_profile_20250123_143000.html

        Returns the HTML profiling report file.
    """
    # Validate filename (security: prevent path traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    report_path = profiling_manager.output_dir / filename

    if not report_path.exists() or not report_path.is_file():
        raise HTTPException(
            status_code=404, detail=f"Report '{filename}' not found"
        )

    if not report_path.suffix == ".html":
        raise HTTPException(
            status_code=400,
            detail="Only HTML reports are supported",
        )

    return FileResponse(
        path=report_path,
        media_type="text/html",
        filename=filename,
    )


@router.delete("/reports/{filename}")
async def delete_report(filename: str) -> JSONResponse:
    """
    Delete a specific profiling report.

    Public endpoint - available for development and debugging.

    Args:
        filename: Name of the report file to delete.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If report file is not found or invalid.

    Example:
        DELETE /api/profiling/reports/websocket_profile_20250123_143000.html

        Response:
        {
            "message": "Report deleted successfully",
            "filename": "websocket_profile_20250123_143000.html"
        }
    """
    # Validate filename (security: prevent path traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    report_path = profiling_manager.output_dir / filename

    if not report_path.exists() or not report_path.is_file():
        raise HTTPException(
            status_code=404, detail=f"Report '{filename}' not found"
        )

    report_path.unlink()

    return JSONResponse(
        content={
            "message": "Report deleted successfully",
            "filename": filename,
        }
    )
