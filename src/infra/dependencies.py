# Gilberto Mota de Oliveira Junior
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from infra.database import get_db
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.security import verify_access_token

from domain.schemas.AuthSchema import FuncionarioAuth

# Scheme para extrair token do header Authorization: Bearer <token>
security = HTTPBearer()


# Dependency para validar token e retornar usuário atual
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> FuncionarioAuth:
    """Dependency que valida o token e retorna o usuário atual"""

    try:
        # Extrai e valida o token
        payload = verify_access_token(credentials.credentials)

        cpf: str = payload.get("sub")
        id_funcionario: int = payload.get("id")

        if cpf is None or id_funcionario is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido - dados incompletos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Busca o funcionário no banco
        funcionario = db.query(FuncionarioDB).filter(
            FuncionarioDB.id == id_funcionario
        ).first()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Funcionário não encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verifica se o CPF do token corresponde ao do banco
        if funcionario.cpf != cpf:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido - CPF não corresponde",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return FuncionarioAuth(
            id=funcionario.id,
            nome=funcionario.nome,
            matricula=funcionario.matricula,
            cpf=funcionario.cpf,
            grupo=funcionario.grupo
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erro ao validar token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Dependency para verificar se o usuário está ativo
def get_current_active_user(
    current_user: FuncionarioAuth = Depends(get_current_user)
) -> FuncionarioAuth:
    """Verifica se o usuário está ativo"""
    # Aqui você pode validar um campo tipo: funcionario.ativo
    return current_user


# Dependency para verificar grupo
def require_group(group_required: list[int] = None):
    """
    Verifica se o usuário pertence a um grupo específico
    """

    def check_group(
        current_user: FuncionarioAuth = Depends(get_current_active_user)
    ) -> FuncionarioAuth:

        # Permite qualquer usuário autenticado
        if group_required is None:
            return current_user

        # Verifica grupo
        if current_user.grupo not in group_required:
            groups_str = ", ".join(map(str, group_required))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão negada - requerido um dos grupos: {groups_str}"
            )

        return current_user

    return check_group