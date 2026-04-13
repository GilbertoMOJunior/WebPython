# Gilberto Mota de Oliveira Junior
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from infra.database import Base

class AuditoriaDB(Base):
    __tablename__ = "tb_auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    funcionario_id = Column(Integer, ForeignKey("tb_funcionario.id", ondelete="RESTRICT"), nullable=False)
    acao = Column(String(50), nullable=False)       # LOGIN, LOGOUT, CREATE, UPDATE, DELETE
    recurso = Column(String(100), nullable=False)   # FUNCIONARIO, CLIENTE, PRODUTO, AUTH
    recurso_id = Column(Integer, nullable=True)
    dados_antigos = Column(Text, nullable=True)     # JSON antes da alteração
    dados_novos = Column(Text, nullable=True)       # JSON após a alteração
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    data_hora = Column(DateTime, nullable=False)
