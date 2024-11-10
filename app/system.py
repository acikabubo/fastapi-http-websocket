import psutil
import math
from typing import NamedTuple
from app.logging import logger

class SystemResources(NamedTuple):
    cpu_cores: int
    memory_gb: float
    cpu_usage_percent: float
    available_memory_gb: float

def get_system_resources() -> SystemResources:
    """Get current system resources"""
    cpu_cores = psutil.cpu_count(logical=True)
    memory_gb = psutil.virtual_memory().total / (1024 ** 3)  # Convert to GB
    cpu_usage = psutil.cpu_percent(interval=1)
    available_memory_gb = psutil.virtual_memory().available / (1024 ** 3)

    return SystemResources(
        cpu_cores=cpu_cores,
        memory_gb=memory_gb,
        cpu_usage_percent=cpu_usage,
        available_memory_gb=available_memory_gb
    )

def calculate_workers() -> tuple[int, int]:
    """
    Calculate optimal number of workers and threads based on system resources.
    Returns:
        tuple: (worker_count, thread_count)
    """
    resources = get_system_resources()

    # Gunicorn recommendation: (2 x $num_cores) + 1
    # However, we'll make this more sophisticated

    # Base calculation on CPU cores
    workers_by_cpu = (2 * resources.cpu_cores) + 1

    # Consider memory constraints (assume each worker needs ~512MB minimum)
    memory_headroom_gb = 2.0  # Leave 2GB for the OS and other processes
    worker_memory_gb = 0.512  # 512MB per worker
    available_memory_gb = resources.available_memory_gb - memory_headroom_gb
    workers_by_memory = max(1, math.floor(available_memory_gb / worker_memory_gb))

    # Take the minimum of CPU-based and memory-based calculations
    worker_count = min(workers_by_cpu, workers_by_memory)

    # Calculate thread count (threads per worker)
    # For CPU-bound tasks, it's usually best to keep this low
    thread_count = 1 if resources.cpu_cores <= 2 else 2

    logger.info(f"System resources: {resources}")
    logger.info(f"Calculated workers by CPU: {workers_by_cpu}")
    logger.info(f"Calculated workers by memory: {workers_by_memory}")
    logger.info(f"Final configuration: {worker_count} workers with {thread_count} threads each")

    return worker_count, thread_count
