import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import requests

from utils.config import SUPABASE_URL, SUPABASE_KEY


class SupabaseResponse:
    def __init__(self, data: Any = None, error: Optional[str] = None, status_code: int = 200):
        self.data = data
        self.error = error
        self.status_code = status_code


class SupabaseTableQuery:
    def __init__(self, client: "SupabaseClient", table: str):
        self.client = client
        self.table = table
        self.operation = "select"
        self.select_columns = "*"
        self.filters: List[Dict[str, Any]] = []
        self.order_by: List[Dict[str, Any]] = []
        self.limit_value: Optional[int] = None
        self.data: Any = None
        self.on_conflict: Optional[str] = None
        self.maybe_single_value: bool = False

    def select(self, columns: str = "*") -> "SupabaseTableQuery":
        self.operation = "select"
        self.select_columns = columns
        return self

    def insert(self, data: Any) -> "SupabaseTableQuery":
        self.operation = "insert"
        self.data = data
        return self

    def upsert(self, data: Any, on_conflict: Optional[str] = None) -> "SupabaseTableQuery":
        self.operation = "upsert"
        self.data = data
        self.on_conflict = on_conflict
        return self

    def update(self, data: Any) -> "SupabaseTableQuery":
        self.operation = "update"
        self.data = data
        return self

    def delete(self) -> "SupabaseTableQuery":
        self.operation = "delete"
        return self

    def eq(self, column: str, value: Any) -> "SupabaseTableQuery":
        self.filters.append({"op": "eq", "column": column, "value": value})
        return self

    def neq(self, column: str, value: Any) -> "SupabaseTableQuery":
        self.filters.append({"op": "neq", "column": column, "value": value})
        return self

    def lt(self, column: str, value: Any) -> "SupabaseTableQuery":
        self.filters.append({"op": "lt", "column": column, "value": value})
        return self

    def lte(self, column: str, value: Any) -> "SupabaseTableQuery":
        self.filters.append({"op": "lte", "column": column, "value": value})
        return self

    def gt(self, column: str, value: Any) -> "SupabaseTableQuery":
        self.filters.append({"op": "gt", "column": column, "value": value})
        return self

    def gte(self, column: str, value: Any) -> "SupabaseTableQuery":
        self.filters.append({"op": "gte", "column": column, "value": value})
        return self

    def in_(self, column: str, values: List[Any]) -> "SupabaseTableQuery":
        self.filters.append({"op": "in", "column": column, "value": values})
        return self

    def order(self, column: str, options: Optional[Dict[str, Any]] = None) -> "SupabaseTableQuery":
        ascending = True
        if isinstance(options, dict) and options.get("ascending") is not None:
            ascending = bool(options.get("ascending"))
        elif isinstance(options, bool):
            ascending = options
        self.order_by.append({"column": column, "ascending": ascending})
        return self

    def limit(self, value: int) -> "SupabaseTableQuery":
        self.limit_value = value
        return self

    def maybeSingle(self) -> "SupabaseTableQuery":
        self.maybe_single_value = True
        return self

    def single(self) -> "SupabaseTableQuery":
        return self.maybeSingle()

    def execute(self, timeout: Optional[float] = None) -> SupabaseResponse:
        return self.client._execute_query(self, timeout)

    def then(self, resolve, reject):
        try:
            result = self.execute()
            return resolve(result)
        except Exception as exc:
            return reject(exc)


class StorageBucket:
    def __init__(self, client: "SupabaseClient", bucket: str):
        self.client = client
        self.bucket = bucket

    def upload(self, *, path: str, file: bytes, file_options: Optional[Dict[str, Any]] = None) -> SupabaseResponse:
        url = f"{self.client.base_url}/api/storage/{self.bucket}/upload"
        data = {"path": path}
        files = {
            "file": (Path(path).name, file, file_options.get("content-type") if file_options else "application/octet-stream")
        }
        headers = self.client.headers.copy()
        response = requests.post(url, headers=headers, data=data, files=files)
        return self.client._build_response(response)

    def download(self, path: str, timeout: Optional[float] = None) -> bytes:
        url = f"{self.client.base_url}/api/storage/{self.bucket}/download"
        response = requests.get(url, headers=self.client.headers, params={"path": path}, timeout=timeout)
        response.raise_for_status()
        return response.content

    def remove(self, paths: Union[str, List[str]]) -> SupabaseResponse:
        if isinstance(paths, str):
            paths = [paths]
        url = f"{self.client.base_url}/api/storage/{self.bucket}/remove"
        response = requests.post(url, headers={**self.client.headers, "Content-Type": "application/json"}, json={"paths": paths})
        return self.client._build_response(response)


class StorageClient:
    def __init__(self, client: "SupabaseClient"):
        self.client = client

    def from_(self, bucket: str) -> StorageBucket:
        return StorageBucket(self.client, bucket)


class SupabaseClient:
    def __init__(self, url: str, key: str):
        self.base_url = url.rstrip("/")
        # Use Bearer token for self-hosted backend
        self.headers = {"Authorization": f"Bearer {key}"} if key else {}
        self.storage = StorageClient(self)

    def table(self, table_name: str) -> SupabaseTableQuery:
        return SupabaseTableQuery(self, table_name)

    def _build_response(self, response: requests.Response) -> SupabaseResponse:
        try:
            payload = response.json()
            data = payload.get("data")
            error = payload.get("error")
        except ValueError:
            data = None
            error = f"Invalid JSON response ({response.status_code})"
        if response.status_code >= 400:
            if not error:
                error = f"HTTP {response.status_code}: {response.text}"
            return SupabaseResponse(data=None, error=error, status_code=response.status_code)
        return SupabaseResponse(data=data, error=error, status_code=response.status_code)

    def _execute_query(self, query: SupabaseTableQuery, timeout: Optional[float] = None) -> SupabaseResponse:
        url = f"{self.base_url}/api/query"
        payload = {
            "table": query.table,
            "operation": query.operation,
            "select": query.select_columns,
            "filters": query.filters,
            "order": query.order_by,
            "limit": query.limit_value,
            "maybe_single": query.maybe_single_value,
            "on_conflict": query.on_conflict,
            "data": query.data,
        }
        response = requests.post(url, headers={**self.headers, "Content-Type": "application/json"}, json=payload, timeout=timeout)
        return self._build_response(response)


def create_client(url: str, key: str) -> SupabaseClient:
    return SupabaseClient(url, key)


Client = SupabaseClient





