
from fastapi import APIRouter
from app.system import get_system_resources

from app import WORKER_COUNT, THREAD_COUNT


router = APIRouter()

@router.get("/system-info")
async def system_info():
    """Get current system resources and worker configuration"""
    resources = get_system_resources()
    return {
        "system_resources": resources._asdict(),
        "worker_configuration": {
            "workers": WORKER_COUNT,
            "threads_per_worker": THREAD_COUNT
        }
    }
