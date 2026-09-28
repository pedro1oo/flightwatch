# ✈️ FlightWatch - Monitor de Passagens Aéreas com Alertas por E-mail

Um sistema automatizado em **Python (FastAPI + SQLite + APScheduler)** que monitora continuamente os preços de passagens aéreas para os destinos escolhidos pelos seus clientes e dispara **e-mails de oportunidade** com um template HTML de alta conversão sempre que o preço cai!

---

## 🎯 Principais Funcionalidades

1. **Monitoramento Contínuo**: O sistema roda um agendador automático em segundo plano (APScheduler) a cada X minutos (configurável).
2. **Detecção Inteligente de Queda**:
   - Compara o novo preço com o valor anterior e com o menor histórico.
   - Suporte a **Preço Teto Alvo** (o cliente só é notificado se estiver abaixo do orçamento dele ou se houver queda).
   - Prevenção de spam: não repete e-mails se a tarifa permanecer a mesma.
3. **E-mails Profissionais**: Template HTML responsivo moderno com rotas, datas, companhia aérea, economia em R$ e porcentagem de desconto, além de botão com link direto para reserva.
4. **Painel Web Moderno**:
   - Cadastro intuitivo de novos alertas para clientes.
   - Indicadores em tempo real de status da API Amadeus e do servidor SMTP.
   - Botão **"Verificar Agora"** para disparar checagem imediata em qualquer rota.
   - **Histórico de preços** com data/hora de cada verificação.
   - Pré-visualização do modelo de e-mail direto pelo navegador.
   - Ferramenta de teste de envio SMTP.
5. **Modo Demonstração Integrado**: Funciona instantaneamente sem travar caso você ainda não tenha inserido as credenciais da API ou do SMTP!

---

## 🚀 Como Executar o Projeto

### 1. Pré-requisitos
- Python 3.9+ instalado.

### 2. Ativar o Ambiente Virtual e Instalar Dependências
```bash
# No diretório do projeto:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Iniciar a Aplicação
```bash
python3 run.py
```
Acesse no seu navegador: **[http://localhost:8000](http://localhost:8000)**

---

## ⚙️ Configurações (.env)

Abra o arquivo `.env` para personalizar as opções:

```env
# 1. API DE VOOS (Google Flights via SerpApi)
# Obtenha sua chave gratuita em 1 clique em: https://serpapi.com/
SERPAPI_KEY=sua_chave_serpapi_aqui

# 2. CONFIGURAÇÃO DE EMAIL (SMTP)
# Exemplo para Gmail (requer Senha de App de 16 dígitos):
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-de-app-16-digitos
SMTP_FROM_NAME=Passagens Baratas ✈️
SMTP_USE_TLS=true

# 3. INTERVALO DO ROBÔ (em minutos)
CHECK_INTERVAL_MINUTES=60
```

> **Dica sobre a API do Google Flights (SerpApi)**:
> 1. Acesse [https://serpapi.com/](https://serpapi.com/) e clique em **"Register"** ou **"Sign in with Google"**.
> 2. No painel inicial (Dashboard), copie o campo **"Your Private API Key"**.
> 3. Cole no seu arquivo `.env` em `SERPAPI_KEY`.
>
> **Dica sobre envio de e-mail pelo Gmail**: Se usar o Gmail, ative a autenticação em 2 etapas na sua conta Google e gere uma [Senha de App](https://myaccount.google.com/apppasswords). Essa senha de 16 letras é colocada em `SMTP_PASSWORD`.

---

## 🧪 Executando os Testes Automatizados

O projeto inclui suíte de testes unitários e de integração:

```bash
source .venv/bin/activate
PYTHONPATH=. python -m unittest discover tests
```

---

## 📂 Estrutura de Arquivos

```
.
├── app/
│   ├── config.py             # Leitor de variáveis de ambiente (.env)
│   ├── database.py           # Conexão e sessão do SQLite
│   ├── main.py               # Servidor FastAPI e agendador APScheduler
│   ├── models.py             # Modelos de dados (Alert, PriceHistory)
│   ├── schemas.py            # Validação Pydantic
│   ├── services/
│   │   ├── flight_service.py # Integração Amadeus API + Mock inteligente
│   │   ├── email_service.py  # Envio SMTP + Renderização Jinja2
│   │   └── monitor_service.py# Lógica de detecção de queda e disparo
│   └── templates/
│       ├── index.html        # Painel Web interativo com Tailwind CSS
│       └── email_template.html# Template de e-mail responsivo
├── tests/
│   ├── test_flow.py          # Teste de detecção de queda e e-mail
│   └── test_api.py           # Teste de endpoints da API e dashboard
├── run.py                    # Script de inicialização rápida
├── requirements.txt          # Dependências do projeto
└── README.md
```
