# Gilberto Mota de Oliveira Junior
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from domain.schemas.ClienteSchema import ClienteCreate, ClienteUpdate, ClienteResponse
from domain.schemas.AuthSchema import FuncionarioAuth
from infra.orm.ClienteModel import ClienteDB
from infra.database import get_db
from infra.dependencies import get_current_active_user, require_group
from infra.rate_limit import limiter, get_rate_limit
from slowapi.errors import RateLimitExceeded
from services.AuditoriaService import AuditoriaService

router = APIRouter()


@router.get("/cliente/", response_model=List[ClienteResponse], tags=["Cliente"], status_code=status.HTTP_200_OK, summary="Listar todos os clientes - protegida por JWT")
@limiter.limit(get_rate_limit("moderate"))
async def get_cliente(
    request: Request,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        clientes = db.query(ClienteDB).all()
        return clientes
    except RateLimitExceeded:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao buscar clientes: {str(e)}")


@router.get("/cliente/{id}", response_model=ClienteResponse, tags=["Cliente"], status_code=status.HTTP_200_OK, summary="Buscar cliente por ID - protegida por JWT")
@limiter.limit(get_rate_limit("moderate"))
async def get_cliente_by_id(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        cliente = db.query(ClienteDB).filter(ClienteDB.id == id).first()
        if not cliente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
        return cliente
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao buscar cliente: {str(e)}")


@router.post("/cliente/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED, tags=["Cliente"], summary="Criar cliente - protegida por JWT e grupos 1 e 3")
@limiter.limit(get_rate_limit("restrictive"))
async def post_cliente(
    request: Request,
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3]))
):
    try:
        existing = db.query(ClienteDB).filter(ClienteDB.cpf == cliente_data.cpf).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um cliente com este CPF")

        novo_cliente = ClienteDB(id=None, nome=cliente_data.nome, cpf=cliente_data.cpf, telefone=cliente_data.telefone)
        db.add(novo_cliente)
        db.commit()
        db.refresh(novo_cliente)

        AuditoriaService.registrar_acao(db=db, funcionario_id=current_user.id, acao="CREATE", recurso="CLIENTE", recurso_id=novo_cliente.id, dados_novos=novo_cliente, request=request)

        return novo_cliente
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao criar cliente: {str(e)}")


@router.put("/cliente/{id}", response_model=ClienteResponse, tags=["Cliente"], status_code=status.HTTP_200_OK, summary="Atualizar cliente - protegida por JWT e grupos 1 e 3")
@limiter.limit(get_rate_limit("restrictive"))
async def put_cliente(
    request: Request,
    id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3]))
):
    try:
        cliente = db.query(ClienteDB).filter(ClienteDB.id == id).first()
        if not cliente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

        if cliente_data.cpf and cliente_data.cpf != cliente.cpf:
            existing = db.query(ClienteDB).filter(ClienteDB.cpf == cliente_data.cpf).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um cliente com este CPF")

        dados_antigos = cliente.__dict__.copy()

        update_data = cliente_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(cliente, field, value)
        db.commit()
        db.refresh(cliente)

        AuditoriaService.registrar_acao(db=db, funcionario_id=current_user.id, acao="UPDATE", recurso="CLIENTE", recurso_id=cliente.id, dados_antigos=dados_antigos, dados_novos=cliente, request=request)

        return cliente
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao atualizar cliente: {str(e)}")


@router.delete("/cliente/{id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Cliente"], summary="Remover cliente - protegida por JWT e grupo 1")
@limiter.limit(get_rate_limit("critical"))
async def delete_cliente(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        cliente = db.query(ClienteDB).filter(ClienteDB.id == id).first()
        if not cliente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

        dados_antigos = cliente.__dict__.copy()
        db.delete(cliente)
        db.commit()

        AuditoriaService.registrar_acao(db=db, funcionario_id=current_user.id, acao="DELETE", recurso="CLIENTE", recurso_id=id, dados_antigos=dados_antigos, request=request)

        return None
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao deletar cliente: {str(e)}")
