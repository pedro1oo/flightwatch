import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_dashboard_page(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("FlightWatch", res.text)
        self.assertIn("Passagens Monitoradas", res.text)

    def test_system_status(self):
        res = self.client.get("/api/system-status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("flight_api_configured", data)
        self.assertIn("smtp_configured", data)

    def test_crud_and_check_flow(self):
        # 1. Cria alerta
        payload = {
            "client_name": "Mariana Souza",
            "client_email": "mariana@email.com",
            "origin": "GRU",
            "destination": "MIA",
            "departure_date": "2026-12-10",
            "return_date": "2026-12-20",
            "max_target_price": 3800.0
        }
        res = self.client.post("/api/alerts", json=payload)
        self.assertEqual(res.status_code, 200)
        created = res.json()
        alert_id = created["id"]
        self.assertEqual(created["origin"], "GRU")
        self.assertEqual(created["destination"], "MIA")
        self.assertIsNotNone(created["last_seen_price"])

        # 2. Lista alertas
        res = self.client.get("/api/alerts")
        self.assertEqual(res.status_code, 200)
        alerts = res.json()
        self.assertTrue(any(a["id"] == alert_id for a in alerts))

        # 3. Dispara checagem manual
        res = self.client.post(f"/api/alerts/{alert_id}/check")
        self.assertEqual(res.status_code, 200)
        check_data = res.json()
        self.assertTrue(check_data["success"])

        # 4. Consulta histórico de preços
        res = self.client.get(f"/api/alerts/{alert_id}/history")
        self.assertEqual(res.status_code, 200)
        history = res.json()
        self.assertGreaterEqual(len(history), 1)

        # 5. Visualiza preview do email gerado
        res = self.client.get("/api/preview-last-email")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Alerta de Passagem Aérea", res.text)

        # 6. Pausa e reativa
        res = self.client.post(f"/api/alerts/{alert_id}/toggle")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["is_active"])

        # 7. Exclui o alerta
        res = self.client.delete(f"/api/alerts/{alert_id}")
        self.assertEqual(res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
