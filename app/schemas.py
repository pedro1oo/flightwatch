from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class AlertCreate(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=100, example="Pedro Ferreira")
    client_email: EmailStr = Field(..., example="pedro@exemplo.com")
    origin: str = Field(..., min_length=3, max_length=4, example="GRU")
    destination: str = Field(..., min_length=3, max_length=4, example="LIS")
    departure_date: str = Field(..., example="2026-11-20")
    return_date: Optional[str] = Field(None, example="2026-11-30")
    max_target_price: Optional[float] = Field(None, gt=0, example=3500.0)

class PriceHistoryItem(BaseModel):
    id: int
    price: float
    currency: str
    airline: Optional[str] = None
    flight_details: Optional[str] = None
    checked_at: datetime

    class Config:
        from_attributes = True

class AlertResponse(BaseModel):
    id: int
    client_name: str
    client_email: str
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str]
    max_target_price: Optional[float]
    last_seen_price: Optional[float]
    lowest_historical_price: Optional[float]
    airline: Optional[str]
    booking_url: Optional[str]
    is_active: bool
    created_at: datetime
    last_checked_at: Optional[datetime]
    history_count: int = 0

    class Config:
        from_attributes = True

class TestEmailRequest(BaseModel):
    to_email: EmailStr
