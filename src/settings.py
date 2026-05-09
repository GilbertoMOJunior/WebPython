from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import os

# raiz do projeto (pasta acima de src/)
BASE_DIR = Path(__file__).resolve().parent.parent

# localiza o arquivo de .env
dotenv_file = find_dotenv()

# Carrega o arquivo .env
load_dotenv(dotenv_file)

# Configurações da API
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
RELOAD = os.getenv("RELOAD")

# Configurações banco de dados
DB_SGDB = os.getenv("DB_SGDB")
DB_NAME = os.getenv("DB_NAME")

# Caso seja diferente de sqlite
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# Ajusta STR_DATABASE conforme gerenciador escolhido
if DB_SGDB == 'sqlite': # SQLite
    STR_DATABASE = f"sqlite:///{BASE_DIR / f'{DB_NAME}.db'}"
elif DB_SGDB == 'mysql': # MySQL
    import pymysql
    STR_DATABASE = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"
elif DB_SGDB == 'mssql': # SQL Server
    import pymssql
    STR_DATABASE = f"mssql+pymssql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8"
else: # SQLite
    STR_DATABASE = f"sqlite:///{BASE_DIR / 'apiDatabase.db'}"

# String de conexão assíncrona (driver async correspondente)
if STR_DATABASE.startswith("sqlite:///"):
    ASYNC_STR_DATABASE = STR_DATABASE.replace("sqlite:///", "sqlite+aiosqlite:///")
elif DB_SGDB == 'mysql':
    ASYNC_STR_DATABASE = STR_DATABASE.replace("mysql+pymysql://", "mysql+aiomysql://")
else:
    # mssql/postgres/etc: mantém sync (sem driver async configurado)
    ASYNC_STR_DATABASE = STR_DATABASE

# Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY", "n5948dncs0s238widcfnjuir909Vascodagma57bc1ef1961c7asdhfalksdjalksd")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Configurações de Rate Limiting
RATE_LIMIT_CRITICAL = os.getenv("RATE_LIMIT_CRITICAL", "5/minute")
RATE_LIMIT_MODERATE = os.getenv("RATE_LIMIT_MODERATE", "100/minute")
RATE_LIMIT_RESTRICTIVE = os.getenv("RATE_LIMIT_RESTRICTIVE", "20/minute")
RATE_LIMIT_LOW = os.getenv("RATE_LIMIT_LOW", "200/minute")
RATE_LIMIT_LIGHT = os.getenv("RATE_LIMIT_LIGHT", "300/minute")
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "50/minute")