import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader

from app.config import settings

logger = logging.getLogger("email_service")

def format_currency_brl(val):
    if val is None:
        return "0,00"
    return f"{float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
jinja_env.filters["brl"] = format_currency_brl

class EmailService:
    def __init__(self):
        self.last_sent_email_html: Optional[str] = None
        self.last_sent_email_subject: Optional[str] = None
        self.last_sent_email_recipient: Optional[str] = None

    def render_price_drop_email(
        self,
        client_name: str,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        old_price: Optional[float],
        new_price: float,
        airline: Optional[str],
        flight_details: Optional[str],
        max_target_price: Optional[float],
        booking_url: str
    ) -> str:
        """Renderiza o template HTML do alerta de voo"""
        template = jinja_env.get_template("email_template.html")
        
        savings_val = 0.0
        savings_pct = 0
        if old_price and old_price > new_price:
            savings_val = round(old_price - new_price, 2)
            savings_pct = int(round((savings_val / old_price) * 100))

        return template.render(
            client_name=client_name,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            old_price=old_price,
            new_price=new_price,
            savings_val=savings_val,
            savings_pct=savings_pct,
            airline=airline,
            flight_details=flight_details,
            max_target_price=max_target_price,
            booking_url=booking_url
        )

    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Envia email real via SMTP ou simula e armazena visualização caso SMTP não esteja configurado.
        """
        # Salva o último email gerado para permitir inspeção no painel
        self.last_sent_email_html = html_content
        self.last_sent_email_subject = subject
        self.last_sent_email_recipient = to_email

        if not text_content:
            text_content = f"{subject}\n\nAcesse o FlightWatch para visualizar os detalhes desta oportunidade."

        if not settings.is_smtp_configured:
            logger.info(f"[SIMULAÇÃO] Email para {to_email} disparado. Assunto: '{subject}'")
            return {
                "success": True,
                "mode": "simulated",
                "message": f"Modo demonstração: email para {to_email} gerado e salvo para visualização no navegador."
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_USER))
            msg["To"] = to_email

            part_text = MIMEText(text_content, "plain", "utf-8")
            part_html = MIMEText(html_content, "html", "utf-8")

            msg.attach(part_text)
            msg.attach(part_html)

            logger.info(f"Conectando a {settings.SMTP_HOST}:{settings.SMTP_PORT} para enviar a {to_email}...")
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, [to_email], msg.as_string())

            logger.info(f"Email SMTP enviado com sucesso para {to_email}!")
            return {"success": True, "mode": "smtp", "message": f"Email enviado para {to_email} via SMTP!"}

        except Exception as e:
            logger.error(f"Falha ao enviar email via SMTP: {e}")
            return {"success": False, "mode": "smtp", "error": str(e)}

    def send_price_drop_alert(
        self,
        client_name: str,
        client_email: str,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        old_price: Optional[float],
        new_price: float,
        airline: Optional[str],
        flight_details: Optional[str],
        max_target_price: Optional[float],
        booking_url: str
    ) -> Dict[str, Any]:
        """Dispara o email de oportunidade de passagem aérea"""
        subject = f"✈️ O preço da passagem para {destination} caiu para R$ {new_price:,.2f}!"
        html_content = self.render_price_drop_email(
            client_name=client_name,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            old_price=old_price,
            new_price=new_price,
            airline=airline,
            flight_details=flight_details,
            max_target_price=max_target_price,
            booking_url=booking_url
        )
        return self.send_email(to_email=client_email, subject=subject, html_content=html_content)

    def send_test_email(self, to_email: str) -> Dict[str, Any]:
        """Envia um email de teste de configuração"""
        subject = "✈️ Teste de Configuração - FlightWatch"
        html = f"""
        <div style="font-family: sans-serif; padding: 20px; color: #1e293b;">
            <h2>✈️ Teste de Notificação FlightWatch</h2>
            <p>Se você está lendo esta mensagem, o seu servidor SMTP foi configurado com <strong>sucesso absoluto</strong>!</p>
            <p>O monitor de passagens aéreas está pronto para avisar assim que as passagens baixarem de preço.</p>
        </div>
        """
        return self.send_email(to_email=to_email, subject=subject, html_content=html)

email_service = EmailService()
