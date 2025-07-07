from pydantic import BaseModel


class ATVUpdate(BaseModel):
    atv_id: int
    requirement: str
    note: str
    atv_order: int


class ECHCUpdate(BaseModel):
    echc_id: int
    direction: int
    characteristic: str
    note: str
    echc_order: int
