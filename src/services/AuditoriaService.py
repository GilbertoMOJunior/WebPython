# Gilberto Mota de Oliveira Junior
from sqlalchemy.orm import Session
from fastapi import Request
from typing import Optional, Dict, Any
from datetime import datetime
import json

from infra.orm.AuditoriaModel import AuditoriaDB


class AuditoriaService:
    """Serviço para registrar auditoria de acessos e ações"""

    @staticmethod
    def registrar_acao(
        db: Session,
        funcionario_id: int,
        acao: str,
        recurso: str,
        recurso_id: Optional[int] = None,
        dados_antigos: Optional[Any] = None,
        dados_novos: Optional[Any] = None,
        request: Optional[Request] = None
    ) -> bool:
        """
        Registra uma ação de auditoria no sistema.

        Args:
            db: Sessão do banco de dados
            funcionario_id: ID do funcionário que realizou a ação
            acao: Tipo de ação (LOGIN, LOGOUT, CREATE, UPDATE, DELETE, etc.)
            recurso: Recurso acessado (funcionario, cliente, produto, auth)
            recurso_id: ID do recurso específico
            dados_antigos: Dados antes da alteração (objeto SQLAlchemy ou dict)
            dados_novos: Dados após a alteração (objeto SQLAlchemy ou dict)
            request: Objeto Request para capturar IP e User-Agent

        Returns:
            bool: True se registrado com sucesso, False caso contrário
        """
        try:
            ip_address = None
            user_agent = None

            if request:
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    ip_address = forwarded_for.split(",")[0].strip()
                else:
                    ip_address = request.client.host
                user_agent = request.headers.get("User-Agent")

            def serializar(obj):
                if obj is None:
                    return None
                if isinstance(obj, dict):
                    # Remove chave interna do SQLAlchemy se presente
                    limpo = {k: v for k, v in obj.items() if not k.startswith("_")}
                    return json.dumps(limpo, default=str)
                if hasattr(obj, "__table__"):
                    dados = {
                        col.name: getattr(obj, col.name)
                        for col in obj.__table__.columns
                    }
                    return json.dumps(dados, default=str)
                return json.dumps(obj, default=str)

            auditoria = AuditoriaDB(
                funcionario_id=funcionario_id,
                acao=acao.upper(),
                recurso=recurso.upper(),
                recurso_id=recurso_id,
                dados_antigos=serializar(dados_antigos),
                dados_novos=serializar(dados_novos),
                ip_address=ip_address,
                user_agent=user_agent,
                data_hora=datetime.now()
            )

            db.add(auditoria)
            db.commit()
            return True

        except Exception:
            db.rollback()
            return False
