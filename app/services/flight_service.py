import random
import logging
from typing import Optional, Dict, Any
import httpx
from app.config import settings

logger = logging.getLogger("flight_service")

class FlightService:
    async def search_flight(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        last_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Busca a melhor oferta de voo para o trecho.
        Se SERPAPI_KEY estiver configurada, consulta o Google Flights em tempo real.
        Caso contrário, usa o gerador simulado inteligente (Modo Demonstração).
        """
        origin = origin.strip().upper()
        destination = destination.strip().upper()

        # Link direto para o Google Flights
        booking_link = self._generate_flight_search_url(origin, destination, departure_date, return_date)

        if settings.is_flight_api_configured:
            real_result = await self._fetch_google_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                fallback_booking_link=booking_link
            )
            if real_result:
                return real_result

        # Fallback / Modo Demonstração
        logger.info(f"Usando modo demonstração para {origin} -> {destination}")
        return self._generate_mock_flight(origin, destination, departure_date, return_date, last_price, booking_link)

    async def _fetch_google_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        fallback_booking_link: str
    ) -> Optional[Dict[str, Any]]:
        """Consulta a API do Google Flights via SerpApi"""
        url = "https://serpapi.com/search"
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date,
            "currency": "BRL",
            "hl": "pt-br",
            "api_key": settings.SERPAPI_KEY
        }
        if return_date:
            params["return_date"] = return_date
            params["type"] = "1"  # Round trip (Ida e Volta)
        else:
            params["type"] = "2"  # One way (Só Ida)

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                logger.info(f"Consultando Google Flights para {origin} ➔ {destination}...")
                res = await client.get(url, params=params)
                
                if res.status_code != 200:
                    logger.warning(f"SerpApi retornou status {res.status_code}: {res.text[:200]}")
                    return None

                data = res.json()
                
                # Coleta ofertas dos blocos best_flights e other_flights
                flights_list = data.get("best_flights", []) or []
                if not flights_list:
                    flights_list = data.get("other_flights", []) or []

                if not flights_list:
                    logger.info(f"Nenhum voo encontrado no Google Flights para {origin}-{destination} em {departure_date}")
                    return None

                # Ordena pelo menor preço
                valid_flights = [f for f in flights_list if f.get("price")]
                if not valid_flights:
                    return None

                valid_flights.sort(key=lambda f: float(f.get("price", 999999)))
                cheapest = valid_flights[0]

                price = float(cheapest["price"])
                currency = "BRL"

                # Extrai informações do voo
                sub_flights = cheapest.get("flights", [])
                airlines = list({sf.get("airline") for sf in sub_flights if sf.get("airline")})
                airline_name = ", ".join(airlines) if airlines else "Companhia Regular"

                total_duration = cheapest.get("total_duration")
                duration_str = f"{total_duration // 60}h{total_duration % 60:02d}m" if total_duration else ""

                stops = len(sub_flights) - 1
                stops_str = "Voo direto" if stops == 0 else f"{stops} conexão(ões)"
                
                details = f"{stops_str}"
                if duration_str:
                    details += f" ({duration_str})"

                # Link oficial do Google Flights gerado pela busca
                booking_url = data.get("search_metadata", {}).get("google_flights_url", fallback_booking_link)

                logger.info(f"Google Flights: menor tarifa encontrada R$ {price:.2f} ({airline_name})")

                return {
                    "price": price,
                    "currency": currency,
                    "airline": airline_name,
                    "details": details,
                    "booking_url": booking_url,
                    "is_simulated": False
                }
        except Exception as e:
            logger.error(f"Erro ao consultar SerpApi Google Flights: {e}")
            return None

    def _generate_mock_flight(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        last_price: Optional[float],
        booking_link: str
    ) -> Dict[str, Any]:
        """
        Gera dados de voo simulados inteligentes para testes imediatos.
        Se houver um last_price, tem 55% de chance de gerar uma queda
        para permitir testar os alertas de email com facilidade!
        """
        known_routes = {
            ("GRU", "LIS"): (3200, 4800, "TAP Air Portugal"),
            ("GRU", "MIA"): (2800, 4200, "American Airlines"),
            ("GRU", "GIG"): (350, 750, "LATAM Airlines"),
            ("BSB", "GRU"): (400, 850, "Gol Linhas Aéreas"),
            ("GRU", "CDG"): (3800, 5600, "Air France"),
            ("GRU", "MAD"): (3400, 5100, "Iberia"),
            ("SDU", "CGH"): (450, 900, "Azul Linhas Aéreas"),
        }

        min_base, max_base, airline = known_routes.get(
            (origin, destination),
            (2500, 4500, "LATAM Airlines")
        )

        if return_date:
            min_base = int(min_base * 1.5)
            max_base = int(max_base * 1.5)

        if last_price is not None and last_price > 0:
            # 55% de chance de queda para testar notificações
            drop = random.random() < 0.55
            if drop:
                percentage = random.uniform(0.06, 0.18)
                new_price = round(last_price * (1 - percentage), 2)
            else:
                percentage = random.uniform(0.02, 0.10)
                new_price = round(last_price * (1 + percentage), 2)
        else:
            new_price = float(random.randint(min_base, max_base))

        stops = random.choice(["Voo direto", "1 conexão"])
        details = f"{stops} | Ida: {departure_date}"
        if return_date:
            details += f" | Volta: {return_date}"

        return {
            "price": new_price,
            "currency": "BRL",
            "airline": airline,
            "details": details,
            "booking_url": booking_link,
            "is_simulated": True
        }

    def _generate_flight_search_url(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str]
    ) -> str:
        """Gera link direto de busca no Google Flights"""
        if return_date:
            return f"https://www.google.com/travel/flights?q=flights+from+{origin}+to+{destination}+from+{departure_date}+to+{return_date}"
        return f"https://www.google.com/travel/flights?q=flights+from+{origin}+to+{destination}+on+{departure_date}"

flight_service = FlightService()
