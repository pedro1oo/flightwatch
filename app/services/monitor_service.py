import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models import Alert, PriceHistory
from app.services.flight_service import flight_service
from app.services.email_service import email_service

logger = logging.getLogger("monitor_service")

class MonitorService:
    async def check_alert(self, alert_id: int, db: Session) -> Dict[str, Any]:
        """
        Executa a verificação de preço de uma passagem aérea para um alerta específico.
        Se o preço tiver caído, dispara o email automaticamente para o cliente.
        """
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return {"success": False, "error": f"Alerta {alert_id} não encontrado"}

        old_price = alert.last_seen_price

        # Busca preço atual
        flight_data = await flight_service.search_flight(
            origin=alert.origin,
            destination=alert.destination,
            departure_date=alert.departure_date,
            return_date=alert.return_date,
            last_price=old_price
        )

        current_price = flight_data["price"]
        airline = flight_data.get("airline")
        details = flight_data.get("details")
        booking_url = flight_data.get("booking_url", "")

        # Registra no histórico de preços
        history = PriceHistory(
            alert_id=alert.id,
            price=current_price,
            currency=flight_data.get("currency", "BRL"),
            airline=airline,
            flight_details=details,
            checked_at=datetime.utcnow()
        )
        db.add(history)

        price_dropped = False
        email_sent = False
        email_result = None

        # Lógica de verificação de queda de preço
        if old_price is None:
            # Primeira verificação para este alerta
            alert.last_seen_price = current_price
            alert.lowest_historical_price = current_price
            
            # Se o usuário definiu um preço teto e o voo já está abaixo do teto:
            if alert.max_target_price and current_price <= alert.max_target_price:
                price_dropped = True
                email_result = email_service.send_price_drop_alert(
                    client_name=alert.client_name,
                    client_email=alert.client_email,
                    origin=alert.origin,
                    destination=alert.destination,
                    departure_date=alert.departure_date,
                    return_date=alert.return_date,
                    old_price=None,
                    new_price=current_price,
                    airline=airline,
                    flight_details=details,
                    max_target_price=alert.max_target_price,
                    booking_url=booking_url
                )
                email_sent = True
                alert.last_notified_price = current_price

        elif current_price < old_price:
            # O PREÇO CAIU!
            price_dropped = True
            
            # Verifica critério de preço teto (se houver)
            meets_target = (alert.max_target_price is None) or (current_price <= alert.max_target_price)
            
            # Não repete email se já notificou exatamente por este mesmo valor
            is_new_notification = (alert.last_notified_price != current_price)

            if meets_target and is_new_notification:
                logger.info(
                    f"✈️ Queda detectada para {alert.client_name} ({alert.origin}->{alert.destination})! "
                    f"De R$ {old_price} para R$ {current_price}"
                )
                email_result = email_service.send_price_drop_alert(
                    client_name=alert.client_name,
                    client_email=alert.client_email,
                    origin=alert.origin,
                    destination=alert.destination,
                    departure_date=alert.departure_date,
                    return_date=alert.return_date,
                    old_price=old_price,
                    new_price=current_price,
                    airline=airline,
                    flight_details=details,
                    max_target_price=alert.max_target_price,
                    booking_url=booking_url
                )
                email_sent = True
                alert.last_notified_price = current_price

        # Atualiza registros do alerta
        alert.last_seen_price = current_price
        if alert.lowest_historical_price is None or current_price < alert.lowest_historical_price:
            alert.lowest_historical_price = current_price

        alert.airline = airline
        alert.booking_url = booking_url
        alert.last_checked_at = datetime.utcnow()

        db.commit()
        db.refresh(alert)

        return {
            "success": True,
            "alert_id": alert.id,
            "origin": alert.origin,
            "destination": alert.destination,
            "old_price": old_price,
            "current_price": current_price,
            "price_dropped": price_dropped,
            "email_sent": email_sent,
            "email_result": email_result,
            "is_simulated": flight_data.get("is_simulated", False)
        }

    async def check_all_active_alerts(self, db: Session) -> List[Dict[str, Any]]:
        """Verifica todos os alertas ativos no banco de dados"""
        active_alerts = db.query(Alert).filter(Alert.is_active == True).all()
        logger.info(f"Iniciando verificação de {len(active_alerts)} alertas ativos...")
        results = []
        for alert in active_alerts:
            res = await self.check_alert(alert.id, db)
            results.append(res)
        return results

monitor_service = MonitorService()
