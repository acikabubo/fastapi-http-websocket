"""
Test WebSocket handler for unit testing.

This handler is only used by the test suite and can be removed
when implementing your own handlers.
"""

from {{cookiecutter.module_name}}.api.ws.constants import PkgID
from {{cookiecutter.module_name}}.routing import pkg_router
from {{cookiecutter.module_name}}.schemas.request import RequestModel
from {{cookiecutter.module_name}}.schemas.response import ResponseModel


@pkg_router.register(PkgID.TEST_HANDLER, roles=["admin"])
async def test_handler(request: RequestModel) -> ResponseModel:
    """
    Test handler for unit tests.

    Requires 'admin' role for access.

    Args:
        request: The WebSocket request model.

    Returns:
        ResponseModel with test data.
    """
    return ResponseModel.ok_msg(
        request.pkg_id,
        request.req_id,
        data={"message": "test response"},
    )
