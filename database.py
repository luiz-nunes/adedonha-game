from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from urllib.parse import quote_plus

# Configuração do banco de dados
# CONFIGURE SUAS CREDENCIAIS AQUI:
DB_USER = 'postgres'
DB_PASSWORD = 'Lcan58495844&'  # Sua senha
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'adedonha'

# Codificar senha para evitar problemas com caracteres especiais
password_encoded = quote_plus(DB_PASSWORD)

# Construir URL de conexão
DATABASE_URL = f'postgresql://{DB_USER}:{password_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

print(f'Conectando ao banco: postgresql://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# Criar engine
engine = create_engine(DATABASE_URL, echo=False, client_encoding='utf8')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelos
class Room(Base):
    __tablename__ = 'rooms'
    
    room_id = Column(String(8), primary_key=True)
    host_id = Column(String(50), nullable=False)
    game_state = Column(String(20), default='waiting')
    current_round = Column(Integer, default=0)
    current_letter = Column(String(1), nullable=True)
    categories = Column(Text, nullable=False)
    used_letters = Column(Text, default='')  # Letras já usadas nesta sala

class Player(Base):
    __tablename__ = 'players'
    
    player_id = Column(String(50), primary_key=True)
    room_id = Column(String(8), nullable=False)
    name = Column(String(50), nullable=False)
    score = Column(Float, default=0.0)
    is_host = Column(Boolean, default=False)

class Answer(Base):
    __tablename__ = 'answers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(8), nullable=False)
    player_id = Column(String(50), nullable=False)
    round = Column(Integer, nullable=False)
    category = Column(String(50), nullable=False)
    answer = Column(String(100), nullable=True)
    points = Column(Float, default=0.0)
    invalidated = Column(Boolean, default=False)
    validation_state = Column(String(10), default='valid')  # 'valid', 'half', 'invalid'

# Criar tabelas
def init_db():
    Base.metadata.create_all(bind=engine)
    print('✓ Banco de dados inicializado')

# Função para obter sessão
def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e
