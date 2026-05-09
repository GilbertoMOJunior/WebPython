# Gilberto Mota de Oliveira Junior
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime

from domain.schemas.ComandaSchema import (
    ComandaCreate, ComandaUpdate, ComandaResponse,
    ComandaProdutosCreate, ComandaProdutosUpdate, ComandaProdutosResponse,
)
from domain.schemas.FuncionarioSchema import FuncionarioResponse
from domain.schemas.ClienteSchema import ClienteResponse
from domain.schemas.ProdutoSchema import ProdutoResponse
from domain.schemas.AuthSchema import FuncionarioAuth

from infra.orm.ComandaModel import ComandaDB, ComandaProdutoDB
from infra.orm.ProdutoModel import ProdutoDB
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.orm.ClienteModel import ClienteDB
from infra.database import get_async_db
from infra.dependencies import require_group, get_current_active_user
from infra.rate_limit import limiter, get_rate_limit

from services.AuditoriaService import AuditoriaService

router = APIRouter()


def _build_comanda_response(comanda, funcionario, cliente) -> ComandaResponse:
    return ComandaResponse(
        id=comanda.id,
        comanda=comanda.comanda,
        data_hora=comanda.data_hora,
        status=comanda.status,
        cliente_id=comanda.cliente_id,
        funcionario_id=comanda.funcionario_id,
        funcionario=FuncionarioResponse(
            id=funcionario.id,
            nome=funcionario.nome,
            matricula=funcionario.matricula,
            cpf=funcionario.cpf,
            telefone=funcionario.telefone,
            grupo=funcionario.grupo,
        ) if funcionario else None,
        cliente=ClienteResponse(
            id=cliente.id,
            nome=cliente.nome,
            cpf=cliente.cpf,
            telefone=cliente.telefone,
        ) if cliente else None,
    )


# ----- Comanda -----

@router.get(
    "/comanda/",
    response_model=List[ComandaResponse],
    tags=["Comanda"],
    summary="Listar todas as comandas - filtros e paginação - protegida por JWT",
)
@limiter.limit(get_rate_limit("moderate"))
async def get_comandas(
    request: Request,
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    id: Optional[int] = Query(None, description="Filtrar por ID"),
    comanda: Optional[str] = Query(None, description="Filtrar por número da comanda"),
    status_filtro: Optional[int] = Query(None, alias="status", description="0=aberta, 1=fechada, 2=cancelada"),
    funcionario_id: Optional[int] = Query(None, description="Filtrar por funcionário"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    data_inicio: Optional[datetime] = Query(None, description="Data inicial (ISO 8601)"),
    data_fim: Optional[datetime] = Query(None, description="Data final (ISO 8601)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user),
):
    try:
        query = (
            select(ComandaDB, FuncionarioDB, ClienteDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == ComandaDB.funcionario_id)
            .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
        )

        conditions = []
        if id is not None:
            conditions.append(ComandaDB.id == id)
        if comanda is not None:
            conditions.append(ComandaDB.comanda == comanda)
        if status_filtro is not None:
            conditions.append(ComandaDB.status == status_filtro)
        if funcionario_id is not None:
            conditions.append(ComandaDB.funcionario_id == funcionario_id)
        if cliente_id is not None:
            conditions.append(ComandaDB.cliente_id == cliente_id)
        if data_inicio is not None:
            conditions.append(ComandaDB.data_hora >= data_inicio)
        if data_fim is not None:
            conditions.append(ComandaDB.data_hora <= data_fim)

        if conditions:
            query = query.where(*conditions)

        result = await db.execute(query.offset(skip).limit(limit))
        rows = result.all()

        return [_build_comanda_response(c, f, cl) for c, f, cl in rows]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar comandas: {str(e)}",
        )


@router.get(
    "/comanda/{id}",
    response_model=ComandaResponse,
    tags=["Comanda"],
    summary="Buscar comanda por ID - protegida por JWT",
)
@limiter.limit(get_rate_limit("moderate"))
async def get_comanda(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user),
):
    try:
        result = await db.execute(
            select(ComandaDB, FuncionarioDB, ClienteDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == ComandaDB.funcionario_id)
            .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
            .where(ComandaDB.id == id)
        )
        row = result.first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada",
            )
        comanda, funcionario, cliente = row
        return _build_comanda_response(comanda, funcionario, cliente)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar comanda: {str(e)}",
        )


@router.post(
    "/comanda/",
    response_model=ComandaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Comanda"],
    summary="Criar nova comanda - protegida por JWT",
)
@limiter.limit(get_rate_limit("restrictive"))
async def create_comanda(
    comanda_data: ComandaCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user),
):
    try:
        # funcionário deve existir
        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.id == comanda_data.funcionario_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Funcionário não encontrado",
            )

        # cliente, se informado, deve existir
        if comanda_data.cliente_id:
            result = await db.execute(
                select(ClienteDB).where(ClienteDB.id == comanda_data.cliente_id)
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cliente não encontrado",
                )

        # na criação só pode abrir (status=0)
        if comanda_data.status != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status inválido - na abertura a comanda deve estar com status 0 (aberta)",
            )

        # impede abrir comanda com mesmo número se já estiver aberta
        result = await db.execute(
            select(ComandaDB)
            .where(ComandaDB.comanda == comanda_data.comanda)
            .where(ComandaDB.status == 0)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comanda já existe e está aberta",
            )

        new_comanda = ComandaDB(
            comanda=comanda_data.comanda,
            data_hora=datetime.now(),
            status=comanda_data.status,
            cliente_id=comanda_data.cliente_id,
            funcionario_id=comanda_data.funcionario_id,
        )
        db.add(new_comanda)
        await db.commit()
        await db.refresh(new_comanda)

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="COMANDA",
            recurso_id=new_comanda.id,
            dados_novos=new_comanda,
            request=request,
        )
        return new_comanda

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar comanda: {str(e)}",
        )


@router.put(
    "/comanda/{id}",
    response_model=ComandaResponse,
    tags=["Comanda"],
    summary="Atualizar comanda - protegida por JWT e grupo 1",
)
@limiter.limit(get_rate_limit("restrictive"))
async def update_comanda(
    id: int,
    comanda_data: ComandaUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    try:
        result = await db.execute(select(ComandaDB).where(ComandaDB.id == id))
        comanda = result.scalar_one_or_none()
        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada",
            )

        dados_antigos_obj = comanda.__dict__.copy()

        if comanda_data.comanda is not None:
            comanda.comanda = comanda_data.comanda
        if comanda_data.status is not None:
            comanda.status = comanda_data.status
        if comanda_data.cliente_id is not None:
            if comanda_data.cliente_id != 0:  # 0 = remover cliente
                result = await db.execute(
                    select(ClienteDB).where(ClienteDB.id == comanda_data.cliente_id)
                )
                if not result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cliente não encontrado",
                    )
                comanda.cliente_id = comanda_data.cliente_id
            else:
                comanda.cliente_id = None
        if comanda_data.funcionario_id is not None:
            result = await db.execute(
                select(FuncionarioDB).where(FuncionarioDB.id == comanda_data.funcionario_id)
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Funcionário não encontrado",
                )
            comanda.funcionario_id = comanda_data.funcionario_id

        await db.commit()
        await db.refresh(comanda)

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="COMANDA",
            recurso_id=comanda.id,
            dados_antigos=dados_antigos_obj,
            dados_novos=comanda,
            request=request,
        )
        return comanda

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar comanda: {str(e)}",
        )


@router.delete(
    "/comanda/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Comanda"],
    summary="Remover comanda - protegida por JWT e grupo 1",
)
@limiter.limit(get_rate_limit("critical"))
async def delete_comanda(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    try:
        result = await db.execute(select(ComandaDB).where(ComandaDB.id == id))
        comanda = result.scalar_one_or_none()
        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada",
            )

        # bloqueia exclusão de comanda com itens vinculados
        result = await db.execute(
            select(func.count(ComandaProdutoDB.id))
            .where(ComandaProdutoDB.comanda_id == id)
        )
        produtos_count = result.scalar() or 0
        if produtos_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível excluir comanda com {produtos_count} produtos vinculados. Remova os produtos primeiro.",
            )

        dados_antigos_obj = comanda.__dict__.copy()
        await db.delete(comanda)
        await db.commit()

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="COMANDA",
            recurso_id=id,
            dados_antigos=dados_antigos_obj,
            request=request,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover comanda: {str(e)}",
        )


@router.put(
    "/comanda/{id}/cancelar",
    response_model=ComandaResponse,
    tags=["Comanda"],
    summary="Cancelar comanda - protegida por JWT e grupo 1",
)
@limiter.limit(get_rate_limit("critical"))
async def cancelar_comanda(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    try:
        result = await db.execute(select(ComandaDB).where(ComandaDB.id == id))
        comanda = result.scalar_one_or_none()
        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada",
            )
        if comanda.status == 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comanda já está cancelada",
            )
        if comanda.status == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comanda já está fechada e não pode ser cancelada",
            )

        dados_antigos = {
            "id": comanda.id,
            "comanda": comanda.comanda,
            "status": comanda.status,
            "data_hora": comanda.data_hora.isoformat() if comanda.data_hora else None,
        }

        comanda.status = 2  # cancelada
        await db.commit()
        await db.refresh(comanda)

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CANCEL",
            recurso="COMANDA",
            recurso_id=comanda.id,
            dados_antigos=dados_antigos,
            request=request,
        )

        result = await db.execute(
            select(ComandaDB, FuncionarioDB, ClienteDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == ComandaDB.funcionario_id)
            .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
            .where(ComandaDB.id == id)
        )
        comanda, funcionario, cliente = result.first()
        return _build_comanda_response(comanda, funcionario, cliente)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao cancelar comanda: {str(e)}",
        )


# ----- Comanda x Produtos -----

@router.post(
    "/comanda/{comanda_id}/produto",
    response_model=ComandaProdutosResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Comanda"],
    summary="Adicionar produto à comanda - protegida por JWT",
)
@limiter.limit(get_rate_limit("restrictive"))
async def add_produto_to_comanda(
    comanda_id: int,
    produto_data: ComandaProdutosCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user),
):
    try:
        result = await db.execute(select(ComandaDB).where(ComandaDB.id == comanda_id))
        comanda = result.scalar_one_or_none()
        if not comanda:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada",
            )
        if comanda.status != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível adicionar produtos a uma comanda fechada ou cancelada",
            )

        result = await db.execute(select(ProdutoDB).where(ProdutoDB.id == produto_data.produto_id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Produto não encontrado",
            )

        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.id == produto_data.funcionario_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Funcionário não encontrado",
            )

        new_item = ComandaProdutoDB(
            comanda_id=comanda_id,
            produto_id=produto_data.produto_id,
            funcionario_id=produto_data.funcionario_id,
            quantidade=produto_data.quantidade,
            valor_unitario=produto_data.valor_unitario,
        )
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="COMANDA_PRODUTO",
            recurso_id=new_item.id,
            dados_novos=new_item,
            request=request,
        )
        return new_item

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao adicionar produto à comanda: {str(e)}",
        )


@router.get(
    "/comanda/{id}/produtos",
    response_model=List[ComandaProdutosResponse],
    tags=["Comanda"],
    summary="Listar produtos de uma comanda - protegida por JWT",
)
@limiter.limit(get_rate_limit("moderate"))
async def get_comanda_produtos(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user),
):
    try:
        result = await db.execute(select(ComandaDB).where(ComandaDB.id == id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comanda não encontrada",
            )

        produtos_result = await db.execute(
            select(ComandaProdutoDB, ProdutoDB, FuncionarioDB)
            .outerjoin(ProdutoDB, ComandaProdutoDB.produto_id == ProdutoDB.id)
            .outerjoin(FuncionarioDB, ComandaProdutoDB.funcionario_id == FuncionarioDB.id)
            .where(ComandaProdutoDB.comanda_id == id)
        )

        out: List[ComandaProdutosResponse] = []
        for item, produto, funcionario in produtos_result.all():
            produto_response = (
                ProdutoResponse(
                    id=produto.id,
                    nome=produto.nome,
                    descricao=produto.descricao,
                    foto=produto.foto,
                    valor_unitario=produto.valor_unitario,
                )
                if produto
                else None
            )
            funcionario_response = (
                FuncionarioResponse(
                    id=funcionario.id,
                    nome=funcionario.nome,
                    matricula=funcionario.matricula,
                    cpf=funcionario.cpf,
                    telefone=funcionario.telefone,
                    grupo=funcionario.grupo,
                )
                if funcionario
                else None
            )
            out.append(ComandaProdutosResponse(
                id=item.id,
                comanda_id=item.comanda_id,
                funcionario_id=item.funcionario_id,
                funcionario=funcionario_response,
                produto_id=item.produto_id,
                produto=produto_response,
                quantidade=item.quantidade,
                valor_unitario=float(item.valor_unitario),
            ))
        return out

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar produtos da comanda: {str(e)}",
        )


@router.put(
    "/comanda/produto/{id}",
    response_model=ComandaProdutosResponse,
    tags=["Comanda"],
    summary="Atualizar item da comanda - quantidade e/ou valor - protegida por JWT e grupo 1",
)
@limiter.limit(get_rate_limit("restrictive"))
async def update_comanda_produto(
    id: int,
    produto_data: ComandaProdutosUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    try:
        result = await db.execute(select(ComandaProdutoDB).where(ComandaProdutoDB.id == id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto da comanda não encontrado",
            )

        dados_antigos_obj = item.__dict__.copy()

        if produto_data.quantidade is not None:
            if produto_data.quantidade <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quantidade deve ser maior que zero",
                )
            item.quantidade = produto_data.quantidade
        if produto_data.valor_unitario is not None:
            if produto_data.valor_unitario <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Valor unitário deve ser maior que zero",
                )
            item.valor_unitario = produto_data.valor_unitario

        await db.commit()
        await db.refresh(item)

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="COMANDA_PRODUTO",
            recurso_id=item.id,
            dados_antigos=dados_antigos_obj,
            dados_novos=item,
            request=request,
        )
        return item

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar produto da comanda: {str(e)}",
        )


@router.delete(
    "/comanda/produto/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Comanda"],
    summary="Remover item da comanda - protegida por JWT e grupo 1",
)
@limiter.limit(get_rate_limit("critical"))
async def remove_produto_from_comanda(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    try:
        result = await db.execute(select(ComandaProdutoDB).where(ComandaProdutoDB.id == id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto da comanda não encontrado",
            )

        dados_antigos_obj = item.__dict__.copy()
        await db.delete(item)
        await db.commit()

        AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="COMANDA_PRODUTO",
            recurso_id=id,
            dados_antigos=dados_antigos_obj,
            request=request,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover produto da comanda: {str(e)}",
        )
