from fastapi import FastAPI

from app.middleware import ActionMiddleware
from app.routers.websocket_router import router as websocket_router

app = FastAPI()

# Define your action map here
action_map = {1: "create_author", 2: "create_genre"}

app.add_middleware(ActionMiddleware, action_map=action_map)
app.include_router(websocket_router)
