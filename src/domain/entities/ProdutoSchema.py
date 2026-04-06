# Gilberto Mota de Oliveira Junior
from pydantic import BaseModel, ConfigDict
from typing import Optional

class ProdutoCreate(BaseModel):
    nome: str
    descricao: str
    foto: Optional[bytes] = None
    valor_unitario: float

class ProdutoUpdate(BaseModel):
    nome: str 
    descricao: str 
    foto: Optional[bytes] = None
    valor_unitario: float 

class ProdutoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    nome: str
    descricao: str
    foto: Optional[bytes] = None
    valor_unitario: float

class ProdutoPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nome: str
    descricao: str
    foto: Optional[bytes] = None