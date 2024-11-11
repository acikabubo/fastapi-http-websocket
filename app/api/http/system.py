from fastapi import APIRouter, Depends

from app import THREAD_COUNT, WORKER_COUNT
from app.auth import get_admin_user
from app.schemas.user import UserModel
from app.system import get_system_resources

router = APIRouter()


@router.get("/system-info")
async def system_info(current_user: UserModel = Depends(get_admin_user)):
    """Get current system resources and worker configuration"""
    resources = get_system_resources()
    return {
        "system_resources": resources._asdict(),
        "worker_configuration": {
            "workers": WORKER_COUNT,
            "threads_per_worker": THREAD_COUNT,
        },
        "requested_by": current_user.username,
    }
