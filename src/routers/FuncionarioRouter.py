# Gilberto Mota de Oliveira Junior
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from domain.schemas.FuncionarioSchema import FuncionarioCreate, FuncionarioUpdate, FuncionarioResponse
from domain.schemas.AuthSchema import FuncionarioAuth
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.database import get_db
from infra.security import get_password_hash
from infra.dependencies import get_current_active_user, require_group
from infra.rate_limit import limiter, get_rate_limit
from slowapi.errors import RateLimitExceeded
from services.AuditoriaService import AuditoriaService

router = APIRouter()


@router.get("/funcionario/", response_model=List[FuncionarioResponse], tags=["Funcionário"], status_code=status.HTTP_200_OK, summary="Listar todos os funcionários - protegida por JWT e grupo 1")
@limiter.limit(get_rate_limit("moderate"))
async def get_funcionarios(
    request: Request,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        funcionarios = db.query(FuncionarioDB).all()
        return funcionarios
    except RateLimitExceeded:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao buscar funcionários: {str(e)}")


@router.get("/funcionario/{id}", response_model=FuncionarioResponse, tags=["Funcionário"], status_code=status.HTTP_200_OK, summary="Buscar funcionário por ID - protegida por JWT")
@limiter.limit(get_rate_limit("moderate"))
async def get_funcionario_by_id(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.id == id).first()
        if not funcionario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado")
        return funcionario
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao buscar funcionário: {str(e)}")


@router.post("/funcionario/", response_model=FuncionarioResponse, status_code=status.HTTP_201_CREATED, tags=["Funcionário"], summary="Criar funcionário - protegida por JWT e grupo 1")
@limiter.limit(get_rate_limit("restrictive"))
async def post_funcionario(
    request: Request,
    funcionario_data: FuncionarioCreate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        existing = db.query(FuncionarioDB).filter(FuncionarioDB.cpf == funcionario_data.cpf).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um funcionário com este CPF")

        hashed_password = get_password_hash(funcionario_data.senha)
        novo_funcionario = FuncionarioDB(
            id=None,
            nome=funcionario_data.nome,
            matricula=funcionario_data.matricula,
            cpf=funcionario_data.cpf,
            telefone=funcionario_data.telefone,
            grupo=funcionario_data.grupo,
            senha=hashed_password
        )
        db.add(novo_funcionario)
        db.commit()
        db.refresh(novo_funcionario)

        AuditoriaService.registrar_acao(db=db, funcionario_id=current_user.id, acao="CREATE", recurso="FUNCIONARIO", recurso_id=novo_funcionario.id, dados_novos=novo_funcionario, request=request)

        return novo_funcionario
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao criar funcionário: {str(e)}")


@router.put("/funcionario/{id}", response_model=FuncionarioResponse, tags=["Funcionário"], status_code=status.HTTP_200_OK, summary="Atualizar funcionário - protegida por JWT e grupo 1")
@limiter.limit(get_rate_limit("restrictive"))
async def put_funcionario(
    request: Request,
    id: int,
    funcionario_data: FuncionarioUpdate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.id == id).first()
        if not funcionario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado")

        if funcionario_data.cpf and funcionario_data.cpf != funcionario.cpf:
            existing = db.query(FuncionarioDB).filter(FuncionarioDB.cpf == funcionario_data.cpf).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um funcionário com este CPF")

        if funcionario_data.senha:
            funcionario_data.senha = get_password_hash(funcionario_data.senha)

        dados_antigos = funcionario.__dict__.copy()

        update_data = funcionario_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(funcionario, field, value)
        db.commit()
        db.refresh(funcionario)

        AuditoriaService.registrar_acao(db=db, funcionario_id=current_user.id, acao="UPDATE", recurso="FUNCIONARIO", recurso_id=funcionario.id, dados_antigos=dados_antigos, dados_novos=funcionario, request=request)

        return funcionario
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao atualizar funcionário: {str(e)}")


@router.delete("/funcionario/{id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Funcionário"], summary="Remover funcionário - protegida por JWT e grupo 1")
@limiter.limit(get_rate_limit("critical"))
async def delete_funcionario(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    try:
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.id == id).first()
        if not funcionario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado")

        if current_user.id == id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não é possível excluir seu próprio usuário")

        dados_antigos = funcionario.__dict__.copy()
        db.delete(funcionario)
        db.commit()

        AuditoriaService.registrar_acao(db=db, funcionario_id=current_user.id, acao="DELETE", recurso="FUNCIONARIO", recurso_id=id, dados_antigos=dados_antigos, request=request)

        return None
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao deletar funcionário: {str(e)}")
