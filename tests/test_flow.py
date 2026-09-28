import asyncio
import os
import unittest
from datetime import datetime

from app.database import Base, engine, SessionLocal
from app.models import Alert, PriceHistory
from app.services.monitor_service import monitor_service
from app.services.email_service import email_service
from app.services.flight_service import flight_service

class TestFlightAlertSystem(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    async def test_full_alert_and_drop_flow(self):
        # 1. Cria um alerta
        alert = Alert(
            client_name="Pedro Ferreira Teste",
            client_email="pedro.teste@exemplo.com",
            origin="GRU",
            destination="LIS",
            departure_date="2026-11-20",
            return_date="2026-11-30",
            max_target_price=4000.0,
            last_seen_price=4200.0, # Preço alto anterior
            lowest_historical_price=4200.0,
            is_active=True
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        self.assertIsNotNone(alert.id)

        # 2. Força um resultado de voo com preço mais baixo para garantir queda
        async def mock_search_flight(*args, **kwargs):
            return {
                "price": 3200.0,
                "currency": "BRL",
                "airline": "TAP Air Portugal",
                "details": "Voo Direto | 10h",
                "booking_url": "https://www.google.com/travel/flights",
                "is_simulated": True
            }

        flight_service.search_flight = mock_search_flight

        # 3. Executa verificação do alerta
        result = await monitor_service.check_alert(alert.id, self.db)

        self.assertTrue(result["success"])
        self.assertEqual(result["current_price"], 3200.0)
        self.assertEqual(result["old_price"], 4200.0)
        self.assertTrue(result["price_dropped"])
        self.assertTrue(result["email_sent"])

        # 4. Verifica se o e-mail foi renderizado com sucesso
        self.assertIsNotNone(email_service.last_sent_email_html)
        self.assertIn("3.200,00", email_service.last_sent_email_html)
        self.assertIn("LIS", email_service.last_sent_email_html)
        self.assertIn("Pedro Ferreira Teste", email_service.last_sent_email_html)

        # 5. Verifica se o histórico foi gravado
        history = self.db.query(PriceHistory).filter(PriceHistory.alert_id == alert.id).all()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].price, 3200.0)

        # Limpeza
        self.db.delete(alert)
        self.db.commit()
        print("✅ Fluxo de detecção de queda e disparo de e-mail testado com 100% de sucesso!")

if __name__ == "__main__":
    unittest.main()
