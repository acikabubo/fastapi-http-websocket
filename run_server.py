import psutil
import uvicorn

if __name__ == "__main__":
    cpu_cores = psutil.cpu_count(logical=True)
    workers = (2 * cpu_cores) + 1
    uvicorn.run("app:application", host="0.0.0.0", port=8000, workers=workers)
