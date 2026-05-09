# Gilberto Mota de Oliveira Junior
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from datetime import datetime, timezone
import psutil

from infra.database import get_db
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.orm.ClienteModel import ClienteDB
from infra.orm.ProdutoModel import ProdutoDB

router = APIRouter()


@router.get(
    "/health",
    tags=["Health"],
    summary="Health check básico - verificação de saúde da API"
)
async def health_check():
    """Verificação básica de saúde da API. Usado por load balancers e orquestradores."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "pastelaria-api",
        "version": "1.0.0"
    }


@router.get(
    "/health/database",
    tags=["Health"],
    summary="Health check do banco de dados - verifica conexão"
)
async def database_health():
    """Verifica conexão com o banco de dados executando uma query simples."""
    try:
        db = next(get_db())
        result = db.execute(text("SELECT 1 as test")).fetchone()
        if result and result[0] == 1:
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database query failed"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}"
        )
    finally:
        try:
            db.close()
        except Exception:
            pass


@router.get(
    "/health/database/tables",
    tags=["Health"],
    summary="Health check das tabelas - verifica se tabelas críticas existem e têm dados"
)
async def database_tables_health():
    """Verifica se as tabelas críticas existem e estão acessíveis."""
    try:
        db = next(get_db())
        checks = {}

        try:
            count = db.query(FuncionarioDB).count()
            checks["funcionarios"] = {"status": "healthy", "count": count}
        except Exception as e:
            checks["funcionarios"] = {"status": "error", "error": str(e)}

        try:
            count = db.query(ClienteDB).count()
            checks["clientes"] = {"status": "healthy", "count": count}
        except Exception as e:
            checks["clientes"] = {"status": "error", "error": str(e)}

        try:
            count = db.query(ProdutoDB).count()
            checks["produtos"] = {"status": "healthy", "count": count}
        except Exception as e:
            checks["produtos"] = {"status": "error", "error": str(e)}

        all_healthy = all(check["status"] == "healthy" for check in checks.values())

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "tables": checks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database tables check failed: {str(e)}"
        )
    finally:
        try:
            db.close()
        except Exception:
            pass


@router.get(
    "/health/system",
    tags=["Health"],
    summary="Health check do sistema - verifica recursos (memória, disco, CPU)"
)
async def system_health():
    """Verifica o uso de recursos do sistema (memória, disco, CPU)."""
    try:
        memory = psutil.virtual_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "status": "healthy" if memory.percent < 90 else "warning"
        }

        disk = psutil.disk_usage(".")
        disk_percent = (disk.used / disk.total) * 100
        disk_info = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": round(disk_percent, 2),
            "status": "healthy" if disk_percent < 90 else "warning"
        }

        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_info = {
            "percent": cpu_percent,
            "count": psutil.cpu_count(),
            "status": "healthy" if cpu_percent < 80 else "warning"
        }

        all_healthy = all([
            memory_info["status"] == "healthy",
            disk_info["status"] == "healthy",
            cpu_info["status"] == "healthy"
        ])

        return {
            "status": "healthy" if all_healthy else "warning",
            "memory": memory_info,
            "disk": disk_info,
            "cpu": cpu_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"System health check failed: {str(e)}"
        )


@router.get(
    "/health/full",
    tags=["Health"],
    summary="Health check completo - verificação de todos os componentes"
)
async def full_health_check():
    """Verificação completa de todos os componentes da API."""
    try:
        checks = {}

        checks["api"] = {"status": "healthy", "message": "API responding"}

        try:
            db = next(get_db())
            db.execute(text("SELECT 1"))
            checks["database"] = {"status": "healthy", "message": "Database connected"}
            db.close()
        except Exception as e:
            checks["database"] = {"status": "unhealthy", "message": str(e)}

        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(".")
            cpu = psutil.cpu_percent(interval=1)
            disk_percent = (disk.used / disk.total) * 100
            system_healthy = (memory.percent < 90 and disk_percent < 90 and cpu < 80)
            checks["system"] = {
                "status": "healthy" if system_healthy else "warning",
                "memory_percent": memory.percent,
                "disk_percent": round(disk_percent, 2),
                "cpu_percent": cpu
            }
        except Exception as e:
            checks["system"] = {"status": "error", "message": str(e)}

        overall_status = "healthy"
        for check in checks.values():
            if check["status"] in ("unhealthy", "error"):
                overall_status = "unhealthy"
                break
            elif check["status"] == "warning" and overall_status == "healthy":
                overall_status = "warning"

        return {
            "status": overall_status,
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "pastelaria-api",
            "version": "1.0.0"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Full health check failed: {str(e)}"
        )


@router.get(
    "/ready",
    tags=["Health"],
    summary="Readiness probe - verifica se API está pronta para receber tráfego"
)
async def readiness_check():
    """Verifica se a API está pronta para receber tráfego."""
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready - database unavailable: {str(e)}"
        )
    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get(
    "/live",
    tags=["Health"],
    summary="Liveness probe - verifica se API está viva (não travada)"
)
async def liveness_check():
    """Verifica se a API está viva. Usado por Kubernetes para reiniciar containers travados."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": "running"
    }
