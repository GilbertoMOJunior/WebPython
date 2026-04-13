# Gilberto Mota de Oliveira Junior
from sqlalchemy.orm import Session
from fastapi import Request
from typing import Optional, Dict, Any
from datetime import datetime
import json

from infra.orm.AuditoriaModel import AuditoriaDB

class AuditoriaService:

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
        try:
            ip_address = None
            user_agent = None

            if request:
                forwarded_for = request.headers.get("X-Forwarded-For")
                ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
                user_agent = request.headers.get("User-Agent")

            def serializar(obj):
                if obj is None:
                    return None
                if isinstance(obj, dict):
                    # Filtra chaves internas do SQLAlchemy
                    return json.dumps({k: v for k, v in obj.items() if not k.startswith("_")}, default=str)
                if hasattr(obj, "__table__"):
                    d = {col.name: getattr(obj, col.name) for col in obj.__table__.columns}
                    return json.dumps(d, default=str)
                return json.dumps(obj, default=str)

            auditoria = AuditoriaDB(
                funcionario_id=funcionario_id,
                acao=acao,
                recurso=recurso,
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
