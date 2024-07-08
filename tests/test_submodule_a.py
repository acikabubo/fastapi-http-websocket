from unittest.mock import AsyncMock, patch

import pytest

from app.models import ResponseModel
from app.routers.ws.handlers.submodule_a import SubmoduleAHandler


@pytest.fixture
def handler(async_session):
    return SubmoduleAHandler(session=async_session)


@pytest.mark.asyncio
async def test_function_a(handler):
    with patch("app.routers.ws.handlers.submodule_a.Author") as mock_author:
        mock_author.return_value = {"name": "Test Author"}

        data = {"name": "Test Author", "req_id": "some-uuid"}
        response = await handler.function_a(data)

        assert response == ResponseModel.ok_msg(
            pkg_id=1, req_id="some-uuid", data={"message": "Author created"}
        )


# Similarly, create test cases for other handlers and submodules
