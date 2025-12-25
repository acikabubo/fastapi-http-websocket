from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Request(_message.Message):
    __slots__ = ("pkg_id", "req_id", "method", "data_json")
    PKG_ID_FIELD_NUMBER: _ClassVar[int]
    REQ_ID_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    DATA_JSON_FIELD_NUMBER: _ClassVar[int]
    pkg_id: int
    req_id: str
    method: str
    data_json: str
    def __init__(self, pkg_id: _Optional[int] = ..., req_id: _Optional[str] = ..., method: _Optional[str] = ..., data_json: _Optional[str] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ("pkg_id", "req_id", "status_code", "data_json", "meta")
    PKG_ID_FIELD_NUMBER: _ClassVar[int]
    REQ_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    DATA_JSON_FIELD_NUMBER: _ClassVar[int]
    META_FIELD_NUMBER: _ClassVar[int]
    pkg_id: int
    req_id: str
    status_code: int
    data_json: str
    meta: Metadata
    def __init__(self, pkg_id: _Optional[int] = ..., req_id: _Optional[str] = ..., status_code: _Optional[int] = ..., data_json: _Optional[str] = ..., meta: _Optional[_Union[Metadata, _Mapping]] = ...) -> None: ...

class Broadcast(_message.Message):
    __slots__ = ("pkg_id", "req_id", "data_json")
    PKG_ID_FIELD_NUMBER: _ClassVar[int]
    REQ_ID_FIELD_NUMBER: _ClassVar[int]
    DATA_JSON_FIELD_NUMBER: _ClassVar[int]
    pkg_id: int
    req_id: str
    data_json: str
    def __init__(self, pkg_id: _Optional[int] = ..., req_id: _Optional[str] = ..., data_json: _Optional[str] = ...) -> None: ...

class Metadata(_message.Message):
    __slots__ = ("page", "per_page", "total", "pages")
    PAGE_FIELD_NUMBER: _ClassVar[int]
    PER_PAGE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    PAGES_FIELD_NUMBER: _ClassVar[int]
    page: int
    per_page: int
    total: int
    pages: int
    def __init__(self, page: _Optional[int] = ..., per_page: _Optional[int] = ..., total: _Optional[int] = ..., pages: _Optional[int] = ...) -> None: ...

class PaginatedRequest(_message.Message):
    __slots__ = ("page", "per_page", "filters_json")
    PAGE_FIELD_NUMBER: _ClassVar[int]
    PER_PAGE_FIELD_NUMBER: _ClassVar[int]
    FILTERS_JSON_FIELD_NUMBER: _ClassVar[int]
    page: int
    per_page: int
    filters_json: str
    def __init__(self, page: _Optional[int] = ..., per_page: _Optional[int] = ..., filters_json: _Optional[str] = ...) -> None: ...
