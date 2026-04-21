from datetime import datetime
from typing import List
from uuid import UUID, uuid4

class Test:
    name: str
    result: str
    unit: str
    reference_range: str

class Report:
    id: UUID
    patient_id: UUID
    patient_name: str
    url: str
    tests: List[Test]
    doctor: str
    lab_no: str
    status: str
    created_at: datetime

    def __init__(self):
        self.id = uuid4()
        self.created_at = datetime.now()
