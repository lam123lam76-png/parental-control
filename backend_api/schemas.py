from typing import Any, List, Optional, Union
from pydantic import BaseModel


class Filter(BaseModel):
    op: str
    column: str
    value: Any


class OrderBy(BaseModel):
    column: str
    ascending: Optional[bool] = True


class QueryRequest(BaseModel):
    table: str
    operation: str
    select: Optional[str] = "*"
    filters: Optional[List[Filter]] = []
    order: Optional[List[OrderBy]] = []
    limit: Optional[int] = None
    maybe_single: Optional[bool] = False
    on_conflict: Optional[str] = None
    data: Optional[Union[dict, List[dict]]] = None


class StorageRemoveRequest(BaseModel):
    paths: List[str]


class RPCRequest(BaseModel):
    params: Optional[dict] = None


class APIResponse(BaseModel):
    data: Optional[Any] = None
    error: Optional[str] = None
