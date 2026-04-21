from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/add")
def add_report():
    pass


@router.get("/get/:id")
def get_report():
    pass


@router.get("/get/:user_id")
def get_all_my_reports():
    pass


@router.put("/change")
def update_report():
    pass


@router.delete("/remove")
def delete_report():
    pass
