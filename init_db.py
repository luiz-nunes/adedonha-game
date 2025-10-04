"""
Script para inicializar o banco de dados PostgreSQL
Execute este script antes de rodar a aplicação pela primeira vez
"""

from database import init_db, engine
from sqlalchemy import text

def create_database():
    """Cria o banco de dados se não existir"""
    print('Inicializando banco de dados...')
    
    try:
        # Testar conexão
        with engine.connect() as conn:
            result = conn.execute(text('SELECT 1'))
            print('✓ Conexão com PostgreSQL estabelecida')
        
        # Criar tabelas
        init_db()
        print('✓ Tabelas criadas com sucesso')
        
    except Exception as e:
        print(f'❌ Erro ao inicializar banco de dados: {e}')
        print('\nVerifique se:')
        print('1. PostgreSQL está instalado e rodando')
        print('2. As credenciais em DATABASE_URL estão corretas')
        print('3. O banco de dados "adedonha" foi criado')
        print('\nPara criar o banco, execute no PostgreSQL:')
        print('   CREATE DATABASE adedonha;')
        return False
    
    return True

if __name__ == '__main__':
    if create_database():
        print('\n✅ Banco de dados pronto para uso!')
    else:
        print('\n❌ Falha na inicialização do banco de dados')
