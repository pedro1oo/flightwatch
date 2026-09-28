import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import Base, engine, get_db, SessionLocal
from app.models import Alert, PriceHistory
from app.schemas import AlertCreate, AlertResponse, PriceHistoryItem, TestEmailRequest
from app.services.monitor_service import monitor_service
from app.services.email_service import email_service

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("flightwatch")

# Cria tabelas no SQLite
Base.metadata.create_all(bind=engine)

# Agendador em segundo plano
scheduler = AsyncIOScheduler()

async def scheduled_flight_check():
    """Tarefa periódica de monitoramento automático"""
    logger.info("⏰ Executando checagem periódica agendada de preços...")
    db = SessionLocal()
    try:
        results = await monitor_service.check_all_active_alerts(db)
        logger.info(f"⏰ Checagem concluída. Total avaliado: {len(results)}")
    except Exception as e:
        logger.error(f"Erro na checagem agendada: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialização do scheduler
    logger.info(f"Iniciando agendador automático (intervalo: {settings.CHECK_INTERVAL_MINUTES} minutos)...")
    scheduler.add_job(scheduled_flight_check, "interval", minutes=settings.CHECK_INTERVAL_MINUTES)
    scheduler.start()
    yield
    # Finalização
    logger.info("Encerrando agendador...")
    scheduler.shutdown()

app = FastAPI(title="FlightWatch API", version="1.0.0", lifespan=lifespan)

# Templates
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ==========================================
# ROTAS DE PÁGINAS WEB
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Página inicial com Dashboard interativo"""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "check_interval": settings.CHECK_INTERVAL_MINUTES,
            "flight_api_configured": settings.is_flight_api_configured,
            "smtp_configured": settings.is_smtp_configured
        }
    )

# ==========================================
# ROTAS DA API REST
# ==========================================

@app.get("/api/system-status")
def system_status():
    """Retorna o status de conexão dos serviços externos"""
    return {
        "flight_api_configured": settings.is_flight_api_configured,
        "smtp_configured": settings.is_smtp_configured,
        "check_interval_minutes": settings.CHECK_INTERVAL_MINUTES,
        "smtp_host": settings.SMTP_HOST
    }

@app.get("/api/alerts", response_model=List[AlertResponse])
def list_alerts(db: Session = Depends(get_db)):
    """Lista todos os alertas cadastrados"""
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()
    out = []
    for a in alerts:
        item = AlertResponse.model_validate(a)
        item.history_count = len(a.price_history)
        out.append(item)
    return out

@app.post("/api/alerts", response_model=AlertResponse)
async def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    """Cadastra um novo alerta e executa a primeira busca de preço imediatamente"""
    alert = Alert(
        client_name=payload.client_name,
        client_email=payload.client_email,
        origin=payload.origin.upper().strip(),
        destination=payload.destination.upper().strip(),
        departure_date=payload.departure_date,
        return_date=payload.return_date,
        max_target_price=payload.max_target_price
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Executa a 1ª checagem imediatamente para já ter o preço base
    await monitor_service.check_alert(alert.id, db)
    db.refresh(alert)

    resp = AlertResponse.model_validate(alert)
    resp.history_count = len(alert.price_history)
    return resp

@app.delete("/api/alerts/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """Remove um alerta de monitoramento"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")
    db.delete(alert)
    db.commit()
    return {"success": True, "message": "Alerta removido com sucesso."}

@app.post("/api/alerts/{alert_id}/toggle")
def toggle_alert(alert_id: int, db: Session = Depends(get_db)):
    """Pausa ou reativa o monitoramento de um alerta"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")
    alert.is_active = not alert.is_active
    db.commit()
    db.refresh(alert)
    return {"success": True, "is_active": alert.is_active}

@app.post("/api/alerts/{alert_id}/check")
async def check_single_alert(alert_id: int, db: Session = Depends(get_db)):
    """Dispara a checagem de preço de um alerta específico agora"""
    result = await monitor_service.check_alert(alert_id, db)
    return result

@app.post("/api/alerts/check-all")
async def check_all_alerts(db: Session = Depends(get_db)):
    """Dispara a checagem de preços de todos os alertas ativos agora"""
    results = await monitor_service.check_all_active_alerts(db)
    return results

@app.get("/api/alerts/{alert_id}/history", response_model=List[PriceHistoryItem])
def get_price_history(alert_id: int, db: Session = Depends(get_db)):
    """Retorna o histórico de preços consultados para um alerta"""
    history = db.query(PriceHistory).filter(PriceHistory.alert_id == alert_id).order_by(PriceHistory.checked_at.desc()).all()
    return history

@app.post("/api/test-email")
def test_email(payload: TestEmailRequest):
    """Envia um e-mail de teste para verificar as credenciais SMTP"""
    result = email_service.send_test_email(payload.to_email)
    return result

@app.get("/api/preview-last-email", response_class=HTMLResponse)
def preview_last_email():
    """Exibe no navegador o modelo HTML do último e-mail gerado"""
    if email_service.last_sent_email_html:
        return email_service.last_sent_email_html

    # Se ainda não disparou nenhum, gera um modelo de exemplo
    sample_html = email_service.render_price_drop_email(
        client_name="Pedro Ferreira",
        origin="GRU",
        destination="LIS",
        departure_date="2026-11-20",
        return_date="2026-11-30",
        old_price=4120.00,
        new_price=3390.50,
        airline="TAP Air Portugal",
        flight_details="Voo direto | Bagagem inclusa",
        max_target_price=3500.00,
        booking_url="https://www.google.com/travel/flights"
    )
    return sample_html
