# Gilberto Mota de Oliveira Junior
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta

from domain.schemas.AuthSchema import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    FuncionarioAuth
)

from infra.orm.FuncionarioModel import FuncionarioDB
from infra.database import get_db
from infra.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token
)
from infra.dependencies import get_current_active_user

from settings import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

router = APIRouter()


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["Autenticação"],
    summary="Login de funcionário - pública - retorna access e refresh token"
)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Realiza login do funcionário e retorna access token e refresh token
    """
    try:
        # Busca funcionário pelo CPF
        funcionario = db.query(FuncionarioDB).filter(
            FuncionarioDB.cpf == login_data.cpf
        ).first()
        
        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="CPF ou senha inválidos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verifica senha
        if not verify_password(login_data.senha, funcionario.senha):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="CPF ou senha inválidos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": funcionario.cpf,
                "id": funcionario.id,
                "grupo": funcionario.grupo
            },
            expires_delta=access_token_expires
        )

        # Refresh token
        refresh_token = create_refresh_token(
            data={
                "sub": funcionario.cpf,
                "id": funcionario.id,
                "grupo": funcionario.grupo
            }
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao realizar login: {str(e)}"
        )


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    tags=["Autenticação"],
    summary="Refresh token - pública - renova access token"
)
async def refresh_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Renova o access token usando um refresh token válido
    """
    try:
        # Decodifica refresh token
        payload = verify_refresh_token(refresh_data.refresh_token)

        cpf = payload.get("sub")

        # Busca funcionário
        funcionario = db.query(FuncionarioDB).filter(
            FuncionarioDB.cpf == cpf
        ).first()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Funcionário não encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Novo access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": funcionario.cpf,
                "id": funcionario.id,
                "grupo": funcionario.grupo
            },
            expires_delta=access_token_expires
        )

        # Novo refresh token
        new_refresh_token = create_refresh_token(
            data={
                "sub": funcionario.cpf,
                "id": funcionario.id,
                "grupo": funcionario.grupo
            }
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erro ao renovar token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/auth/me",
    response_model=FuncionarioAuth,
    tags=["Autenticação"],
    summary="Dados do usuário atual - protegida por autenticação"
)
async def get_current_user_info(
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    return current_user


@router.post(
    "/auth/logout",
    tags=["Autenticação"],
    summary="Logout - pública"
)
async def logout():
    return {"message": "Logout realizado com sucesso"}