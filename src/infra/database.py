from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from settings import STR_DATABASE, ASYNC_STR_DATABASE

# engine síncrono (mantido para os routers existentes)
engine = create_engine(STR_DATABASE, echo=True)

# engine assíncrono (usado pelo ComandaRouter)
async_engine = create_async_engine(ASYNC_STR_DATABASE, echo=True)

# sessão síncrona
Session = sessionmaker(bind=engine, autocommit=False, autoflush=True)

# sessão assíncrona
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base declarativa para os modelos
Base = declarative_base()

# cria as tabelas no startup (importações dos modelos registram em Base.metadata)
async def cria_tabelas():
    Base.metadata.create_all(engine)

# dependência síncrona
def get_db():
    db_session = Session()
    try:
        yield db_session
    finally:
        db_session.close()

# dependência assíncrona
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()