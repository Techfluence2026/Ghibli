from datetime import datetime
from typing import List
from uuid import UUID, uuid4


class Medicine:
    name: str
    dose: str
    rate: str


class Prescription:
    id: UUID
    patient_id: UUID
    patient_name: str
    disease_date: str
    url: str
    medications: List[Medicine]
    status: str
    doctors_remark: str
    created_at: datetime

    def __init__(self):
        self.id = uuid4()
        self.created_at = datetime.now()
