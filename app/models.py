from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(100), nullable=False)
    client_email = Column(String(120), nullable=False, index=True)
    
    # Aeroportos (códigos IATA, ex: GRU, LIS, MIA, GIG)
    origin = Column(String(10), nullable=False, index=True)
    destination = Column(String(10), nullable=False, index=True)
    
    # Datas da viagem (formato YYYY-MM-DD)
    departure_date = Column(String(20), nullable=False)
    return_date = Column(String(20), nullable=True)
    
    # Preços
    max_target_price = Column(Float, nullable=True)  # Preço teto opcional
    last_seen_price = Column(Float, nullable=True)   # Preço na última checagem
    lowest_historical_price = Column(Float, nullable=True)  # Menor preço já registrado
    last_notified_price = Column(Float, nullable=True)      # Preço informado no último email
    
    # Informações do último voo
    airline = Column(String(100), nullable=True)
    booking_url = Column(String(500), nullable=True)
    
    # Controle
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_checked_at = Column(DateTime, nullable=True)

    # Relacionamento de histórico
    price_history = relationship("PriceHistory", back_populates="alert", cascade="all, delete-orphan", order_by="desc(PriceHistory.checked_at)")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    
    price = Column(Float, nullable=False)
    currency = Column(String(10), default="BRL")
    airline = Column(String(100), nullable=True)
    flight_details = Column(Text, nullable=True)
    
    checked_at = Column(DateTime, default=datetime.utcnow)

    alert = relationship("Alert", back_populates="price_history")
