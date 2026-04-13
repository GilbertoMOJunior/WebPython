# Gilberto Mota de Oliveira Junior
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta

from domain.schemas.AuthSchema import LoginRequest, TokenResponse, RefreshTokenRequest, FuncionarioAuth
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.database import get_db
from infra.security import verify_password, create_access_token, create_refresh_token, verify_refresh_token
from infra.dependencies import get_current_active_user
from infra.rate_limit import limiter, get_rate_limit
from slowapi.errors import RateLimitExceeded
from services.AuditoriaService import AuditoriaService
from settings import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse, tags=["Autenticação"], summary="Login de funcionário - pública - retorna access e refresh token")
@limiter.limit(get_rate_limit("critical"))
async def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    try:
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.cpf == login_data.cpf).first()
        if not funcionario:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="CPF ou senha inválidos", headers={"WWW-Authenticate": "Bearer"})

        if not verify_password(login_data.senha, funcionario.senha):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="CPF ou senha inválidos", headers={"WWW-Authenticate": "Bearer"})

        access_token = create_access_token(
            data={"sub": funcionario.cpf, "id": funcionario.id, "grupo": funcionario.grupo},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token = create_refresh_token(
            data={"sub": funcionario.cpf, "id": funcionario.id, "grupo": funcionario.grupo}
        )

        AuditoriaService.registrar_acao(db=db, funcionario_id=funcionario.id, acao="LOGIN", recurso="AUTH", request=request)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao realizar login: {str(e)}")


@router.post("/auth/refresh", response_model=TokenResponse, tags=["Autenticação"], summary="Refresh token - pública - renova access token")
@limiter.limit(get_rate_limit("critical"))
async def refresh_token(request: Request, refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        payload = verify_refresh_token(refresh_data.refresh_token)
        cpf = payload.get("sub")

        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.cpf == cpf).first()
        if not funcionario:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Funcionário não encontrado", headers={"WWW-Authenticate": "Bearer"})

        access_token = create_access_token(
            data={"sub": funcionario.cpf, "id": funcionario.id, "grupo": funcionario.grupo},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        new_refresh_token = create_refresh_token(
            data={"sub": funcionario.cpf, "id": funcionario.id, "grupo": funcionario.grupo}
        )

        AuditoriaService.registrar_acao(db=db, funcionario_id=funcionario.id, acao="REFRESH", recurso="AUTH", request=request)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Erro ao renovar token: {str(e)}", headers={"WWW-Authenticate": "Bearer"})


@router.get("/auth/me", response_model=FuncionarioAuth, tags=["Autenticação"], summary="Dados do usuário atual - protegida por autenticação")
@limiter.limit(get_rate_limit("moderate"))
async def get_current_user_info(request: Request, current_user: FuncionarioAuth = Depends(get_current_active_user)):
    return current_user


@router.post("/auth/logout", tags=["Autenticação"], summary="Logout - pública")
@limiter.limit(get_rate_limit("critical"))
async def logout(request: Request):
    return {"message": "Logout realizado com sucesso"}
