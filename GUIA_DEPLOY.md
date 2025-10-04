# 🚀 Guia Completo de Deploy - Adedonha

## 📋 Índice
1. [Arquivos Necessários](#arquivos-necessários)
2. [Melhores Opções Gratuitas](#melhores-opções-gratuitas)
3. [Deploy no Render (Recomendado)](#deploy-no-render)
4. [Deploy no Railway](#deploy-no-railway)
5. [Deploy no Fly.io](#deploy-no-flyio)
6. [Configurações Importantes](#configurações-importantes)

---

## 📦 Arquivos Necessários

### ✅ Arquivos Essenciais (DEVEM ser enviados):

```
Adedonha2/
├── app.py                    # Aplicação principal
├── database.py               # Configuração do banco
├── init_db.py               # Inicialização do banco
├── requirements.txt         # Dependências Python
├── Procfile                 # Comando de inicialização
├── runtime.txt              # Versão do Python
├── .gitignore              # Arquivos a ignorar
└── templates/
    ├── index.html          # Página inicial
    └── room.html           # Sala de jogo
```

### ❌ Arquivos que NÃO devem ser enviados:

```
❌ .env                      # Contém senhas (usar variáveis de ambiente)
❌ .venv/                    # Ambiente virtual local
❌ __pycache__/              # Cache do Python
❌ *.pyc                     # Arquivos compilados
❌ app_backup.py             # Backups
❌ *.md (exceto README.md)   # Documentações locais
❌ migrate_*.py              # Scripts de migração (rodar manualmente)
❌ config_db.py              # Configuração local
❌ run.bat / run.sh          # Scripts locais
```

---

## 🏆 Melhores Opções Gratuitas

### 1. 🥇 **Render** (MAIS RECOMENDADO)

**Vantagens:**
- ✅ PostgreSQL gratuito incluído
- ✅ Deploy automático via GitHub
- ✅ SSL/HTTPS automático
- ✅ Fácil configuração
- ✅ 750 horas/mês grátis
- ✅ Suporta WebSockets

**Limitações:**
- ⚠️ Dorme após 15min de inatividade (primeiro acesso demora ~30s)
- ⚠️ 512MB RAM

**Plano:** Free (sem cartão de crédito)

---

### 2. 🥈 **Railway**

**Vantagens:**
- ✅ PostgreSQL gratuito incluído
- ✅ Deploy muito rápido
- ✅ Interface moderna
- ✅ Suporta WebSockets
- ✅ Não dorme

**Limitações:**
- ⚠️ $5 de crédito grátis/mês (~500 horas)
- ⚠️ Requer cartão de crédito (não cobra se não passar do limite)

**Plano:** Trial ($5/mês grátis)

---

### 3. 🥉 **Fly.io**

**Vantagens:**
- ✅ Não dorme
- ✅ Rápido
- ✅ PostgreSQL incluído
- ✅ Suporta WebSockets

**Limitações:**
- ⚠️ Configuração mais técnica
- ⚠️ Requer cartão de crédito

**Plano:** Free (3 máquinas pequenas)

---

### ❌ **NÃO Recomendados:**

**Heroku:**
- ❌ Não tem plano gratuito desde 2022
- ❌ Mínimo $7/mês

**PythonAnywhere:**
- ❌ Não suporta WebSockets (essencial para o jogo)

**Vercel/Netlify:**
- ❌ Focados em frontend, não suportam WebSockets persistentes

---

## 🚀 Deploy no Render (Passo a Passo)

### Passo 1: Preparar o Código

1. **Criar conta no GitHub** (se não tiver)
   - Acesse: https://github.com

2. **Criar repositório**
   ```
   Nome: adedonha-game
   Visibilidade: Public
   ```

3. **Subir código para GitHub**
   ```bash
   cd C:\Adedonha2
   git init
   git add app.py database.py init_db.py requirements.txt Procfile runtime.txt templates/
   git commit -m "Deploy inicial"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/adedonha-game.git
   git push -u origin main
   ```

### Passo 2: Criar Conta no Render

1. Acesse: https://render.com
2. Clique em "Get Started for Free"
3. Faça login com GitHub

### Passo 3: Criar Banco PostgreSQL

1. No Dashboard, clique em "New +"
2. Selecione "PostgreSQL"
3. Configure:
   ```
   Name: adedonha-db
   Database: adedonha
   User: postgres
   Region: Oregon (US West)
   Plan: Free
   ```
4. Clique em "Create Database"
5. **IMPORTANTE:** Copie a "Internal Database URL" (algo como `postgresql://...`)

### Passo 4: Criar Web Service

1. No Dashboard, clique em "New +"
2. Selecione "Web Service"
3. Conecte seu repositório GitHub
4. Configure:
   ```
   Name: adedonha-game
   Region: Oregon (US West)
   Branch: main
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python app.py
   Plan: Free
   ```

### Passo 5: Configurar Variáveis de Ambiente

1. **Localize a seção de variáveis:**
   - Após criar o Web Service, você estará na página de detalhes do serviço
   - No menu lateral esquerdo, procure por uma das opções:
     - **"Environment"** ou
     - **"Environment Variables"** ou
     - **"Settings"** → depois clique em "Environment Variables"
   - Alternativamente, role a página para baixo até encontrar a seção "Environment Variables"

2. **Adicione as variáveis:**
   - Clique em "Add Environment Variable" ou "+ Add"
   - Adicione cada variável:

```
Key: DATABASE_URL
Value: [Cole a Internal Database URL do Passo 3]

Key: PYTHON_VERSION
Value: 3.11.9
```

3. **Salve as alterações:**
   - Clique em "Save Changes" ou "Add"
   - O Render fará um novo deploy automaticamente

**IMPORTANTE:** Se o Render continuar usando Python 3.13, vá em Settings → Build & Deploy e force "Clear build cache & deploy"

### Passo 6: Modificar database.py

**IMPORTANTE:** Antes de fazer deploy, modifique o `database.py`:

```python
import os
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

# Usar variável de ambiente para DATABASE_URL
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    # Fallback para desenvolvimento local
    DB_USER = 'postgres'
    DB_PASSWORD = 'Lcan58495844&'
    DB_HOST = 'localhost'
    DB_PORT = '5432'
    DB_NAME = 'adedonha'
    password_encoded = quote_plus(DB_PASSWORD)
    DATABASE_URL = f'postgresql://{DB_USER}:{password_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

print(f'Conectando ao banco: {DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else "local"}')

# Criar engine
engine = create_engine(DATABASE_URL, echo=False, client_encoding='utf8')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ... resto do código permanece igual
```

### Passo 7: Modificar app.py

**Adicione no início do arquivo:**

```python
import os

# ... imports existentes ...

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
```

### Passo 8: Deploy!

1. Faça commit das alterações:
   ```bash
   git add database.py app.py
   git commit -m "Configurar para produção"
   git push
   ```

2. Render detectará automaticamente e fará deploy!

3. Aguarde ~5 minutos

4. Acesse: `https://adedonha-game.onrender.com`

### Passo 9: Verificar Deploy

**O banco de dados é inicializado automaticamente!**

1. Aguarde o deploy finalizar (~5 minutos)
2. Acesse a URL do seu app: `https://adedonha-game.onrender.com`
3. Verifique os logs no Render:
   - Clique em "Logs" no menu lateral
   - Procure por: `✓ Banco de dados conectado`
4. Se houver erro, verifique:
   - `DATABASE_URL` está configurada corretamente
   - A URL do banco é a "Internal Database URL"

**Nota:** O plano Free do Render não permite acesso ao Shell, mas não é necessário! O código já inicializa o banco automaticamente quando a aplicação inicia.

---

## 🚂 Deploy no Railway (Alternativa)

### Passo 1: Criar Conta

1. Acesse: https://railway.app
2. Login com GitHub
3. Adicione cartão de crédito (não será cobrado no plano gratuito)

### Passo 2: Novo Projeto

1. Clique em "New Project"
2. Selecione "Deploy from GitHub repo"
3. Escolha seu repositório

### Passo 3: Adicionar PostgreSQL

1. Clique em "+ New"
2. Selecione "Database" → "PostgreSQL"
3. Railway criará automaticamente

### Passo 4: Configurar Variáveis

1. Clique no seu serviço web
2. Vá em "Variables"
3. Railway já adiciona `DATABASE_URL` automaticamente!

### Passo 5: Deploy

- Deploy acontece automaticamente!
- Acesse: `https://seu-app.up.railway.app`

---

## ✈️ Deploy no Fly.io

### Passo 1: Instalar CLI

```bash
# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex

# Mac/Linux
curl -L https://fly.io/install.sh | sh
```

### Passo 2: Login

```bash
fly auth login
```

### Passo 3: Criar App

```bash
cd C:\Adedonha2
fly launch
```

Responda:
```
App name: adedonha-game
Region: São Paulo (gru)
PostgreSQL: Yes
Redis: No
Deploy now: No
```

### Passo 4: Configurar

Edite `fly.toml`:
```toml
[env]
  PORT = "8080"

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443
```

### Passo 5: Deploy

```bash
fly deploy
```

---

## ⚙️ Configurações Importantes

### 1. Modificar `database.py` para Produção

```python
import os

# Usar variável de ambiente
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    # Desenvolvimento local
    DATABASE_URL = 'postgresql://postgres:senha@localhost:5432/adedonha'
```

### 2. Modificar `app.py` para Produção

```python
import os

# No final do arquivo:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False') == 'True'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
```

### 3. Verificar `requirements.txt`

**IMPORTANTE:** Não inclua pandas (só é usado localmente)

```txt
Flask==3.0.0
Flask-SocketIO==5.3.5
python-socketio==5.10.0
python-engineio==4.8.0
eventlet==0.33.3
psycopg2-binary==2.9.9
SQLAlchemy==2.0.35
gunicorn==21.2.0
```

**Nota:** SQLAlchemy 2.0.35+ é compatível com Python 3.13 (caso o Render ignore o runtime.txt)

### 4. Criar `Procfile`

```
web: python app.py
```

### 5. Criar `runtime.txt` e `.python-version`

**runtime.txt:**
```
python-3.11.9
```

**.python-version:**
```
3.11.9
```

**Nota:** Alguns serviços leem `.python-version` em vez de `runtime.txt`

---

## 🔧 Troubleshooting

### Problema: "Application Error"

**Solução:**
1. Verifique logs no dashboard da plataforma
2. Confirme que `DATABASE_URL` está configurada
3. O banco inicializa automaticamente no primeiro acesso

### Problema: Erro ao instalar pandas (Python 3.13)

**Erro:**
```
error: too few arguments to function '_PyLong_AsByteArray'
```

**Causa:** Render está usando Python 3.13 em vez de 3.11

**Solução:**
1. Verifique se `runtime.txt` existe com: `python-3.11.9`
2. Atualize `requirements.txt` para: `pandas==2.2.2`
3. No Render, vá em "Environment" e adicione:
   ```
   PYTHON_VERSION=3.11.9
   ```
4. Faça novo deploy:
   ```bash
   git add runtime.txt requirements.txt
   git commit -m "Fix Python version"
   git push
   ```

### Problema: WebSocket não conecta

**Solução:**
1. Verifique se a plataforma suporta WebSockets
2. Confirme que está usando HTTPS (não HTTP)
3. Adicione `cors_allowed_origins="*"` no SocketIO

### Problema: Banco de dados vazio

**Solução:**
1. Acesse terminal da plataforma
2. Execute:
   ```bash
   python init_db.py
   python migrate_add_validation_state.py
   ```

### Problema: App dorme (Render Free)

**Solução:**
- Use um serviço de "keep-alive" como:
  - UptimeRobot (https://uptimerobot.com)
  - Cron-job.org (https://cron-job.org)
- Configure para fazer ping a cada 10 minutos

---

## 📊 Comparação Final

| Plataforma | Custo | Setup | Performance | Recomendação |
|------------|-------|-------|-------------|--------------|
| **Render** | Grátis | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 🥇 Melhor para começar |
| **Railway** | $5/mês grátis | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🥈 Melhor performance |
| **Fly.io** | Grátis | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🥉 Mais técnico |

---

## 🎯 Recomendação Final

### Para Iniciantes:
**Use Render** - Mais fácil, sem cartão de crédito, PostgreSQL incluído.

### Para Melhor Performance:
**Use Railway** - Não dorme, mais rápido, mas requer cartão.

### Para Produção Séria:
**Use Fly.io** ou **Railway Paid** - Melhor infraestrutura.

---

## 📝 Checklist de Deploy

- [ ] Código no GitHub
- [ ] `database.py` modificado para usar `DATABASE_URL`
- [ ] `app.py` modificado para usar `PORT`
- [ ] `requirements.txt` atualizado
- [ ] `Procfile` criado
- [ ] `runtime.txt` criado
- [ ] Conta criada na plataforma
- [ ] PostgreSQL criado
- [ ] Variáveis de ambiente configuradas
- [ ] Deploy realizado
- [ ] `init_db.py` executado
- [ ] Migrações executadas
- [ ] Teste realizado

---

## 🆘 Precisa de Ajuda?

1. **Logs:** Sempre verifique os logs da plataforma
2. **Documentação:** Cada plataforma tem docs excelentes
3. **Comunidade:** Discord/Fórum de cada plataforma

---

## 🎉 Pronto!

Seu jogo Adedonha estará online e acessível para todos!

**URL Final:** `https://seu-app.plataforma.com`

Compartilhe com seus amigos e divirta-se! 🎮
