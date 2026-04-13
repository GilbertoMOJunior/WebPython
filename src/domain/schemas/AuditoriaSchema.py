# Gilberto Mota de Oliveira Junior
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class AuditoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    funcionario_id: int
    funcionario: Dict[str, Any]
    acao: str
    recurso: str
    recurso_id: Optional[int] = None
    dados_antigos: Optional[str] = None
    dados_novos: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    data_hora: datetime
