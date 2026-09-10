"""Repository base.

Repositories isolate raw Supabase/PostgREST calls from service logic, so
swapping the data layer (or mocking it in tests) never touches business code.
"""

from typing import Any

from supabase import Client


class BaseRepository:
    table: str = ""

    def __init__(self, client: Client):
        if not self.table:
            raise ValueError(f"{type(self).__name__} must define `table`.")
        self.client = client

    @property
    def query(self):
        return self.client.table(self.table)

    def by_id(self, record_id: str) -> dict[str, Any] | None:
        result = self.query.select("*").eq("id", record_id).maybe_single().execute()
        return result.data
