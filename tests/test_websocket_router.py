# import pytest
# from fastapi.testclient import TestClient

# from app.main import app

# client = TestClient(app)


# def test_websocket_connection():
#     with client.websocket_connect("/ws") as websocket:
#         websocket.send_json(
#             {
#                 "pkg_id": 1,
#                 "data": {"name": "Test Author", "req_id": "some-uuid"},
#             }
#         )
#         data = websocket.receive_json()
#         assert data["status_code"] == 0
