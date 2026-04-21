from typing import List
from uuid import UUID, uuid4


class Value:
    id: UUID
    month: str
    value: float


class Metric:
    id: UUID
    title: str
    description: str
