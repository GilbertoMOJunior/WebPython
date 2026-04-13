# Gilberto Mota de Oliveira Junior
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from datetime import datetime, timezone
import psutil

from infra.database import get_db
from infra.orm.FuncionarioModel import FuncionarioDB

router = APIRouter()


@router.get("/health", tags=["Health"], summary="Health check básico - Verificação básica de saúde da API")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "pastelaria-api",
        "version": "1.0.0"
    }


@router.get("/health/database", tags=["Health"], summary="Health check do banco de dados")
async def database_health():
    try:
        db = next(get_db())
        result = db.execute(text("SELECT 1 as test")).fetchone()
        if result and result[0] == 1:
            return {"status": "healthy", "database": "connected", "timestamp": datetime.now(timezone.utc).isoformat()}
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database query failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Database unavailable: {str(e)}")
    finally:
        try:
            db.close()
        except:
            pass


@router.get("/health/database/tables", tags=["Health"], summary="Health check das tabelas críticas")
async def database_tables_health():
    try:
        db = next(get_db())
        checks = {}
        try:
            count = db.query(FuncionarioDB).count()
            checks["funcionarios"] = {"status": "healthy", "count": count}
        except Exception as e:
            checks["funcionarios"] = {"status": "error", "error": str(e)}

        all_healthy = all(c["status"] == "healthy" for c in checks.values())
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "tables": checks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Tables check failed: {str(e)}")
    finally:
        try:
            db.close()
        except:
            pass


@router.get("/health/system", tags=["Health"], summary="Health check do sistema - memória, disco, CPU")
async def system_health():
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(".")
        cpu_percent = psutil.cpu_percent(interval=1)

        memory_info = {"total": memory.total, "available": memory.available, "percent": memory.percent, "status": "healthy" if memory.percent < 90 else "warning"}
        disk_info = {"total": disk.total, "used": disk.used, "free": disk.free, "percent": round((disk.used / disk.total) * 100, 2), "status": "healthy" if (disk.used / disk.total) * 100 < 90 else "warning"}
        cpu_info = {"percent": cpu_percent, "count": psutil.cpu_count(), "status": "healthy" if cpu_percent < 80 else "warning"}

        all_healthy = all(i["status"] == "healthy" for i in [memory_info, disk_info, cpu_info])
        return {
            "status": "healthy" if all_healthy else "warning",
            "memory": memory_info,
            "disk": disk_info,
            "cpu": cpu_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"System health check failed: {str(e)}")


@router.get("/health/full", tags=["Health"], summary="Health check completo - todos os componentes")
async def full_health_check():
    try:
        checks = {}
        checks["api"] = {"status": "healthy", "message": "API responding"}

        try:
            db = next(get_db())
            db.execute(text("SELECT 1"))
            db.close()
            checks["database"] = {"status": "healthy", "message": "Database connected"}
        except Exception as e:
            checks["database"] = {"status": "unhealthy", "message": str(e)}

        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(".")
            cpu = psutil.cpu_percent(interval=1)
            system_healthy = memory.percent < 90 and (disk.used / disk.total) * 100 < 90 and cpu < 80
            checks["system"] = {
                "status": "healthy" if system_healthy else "warning",
                "memory_percent": memory.percent,
                "disk_percent": round((disk.used / disk.total) * 100, 2),
                "cpu_percent": cpu
            }
        except Exception as e:
            checks["system"] = {"status": "error", "message": str(e)}

        overall = "healthy"
        for c in checks.values():
            if c["status"] in ("unhealthy", "error"):
                overall = "unhealthy"
                break
            elif c["status"] == "warning" and overall == "healthy":
                overall = "warning"

        return {"status": overall, "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat(), "service": "pastelaria-api", "version": "1.0.0"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Full health check failed: {str(e)}")


@router.get("/ready", tags=["Health"], summary="Readiness probe - API pronta para receber tráfego")
async def readiness_check():
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Service not ready: {str(e)}")
    return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/live", tags=["Health"], summary="Liveness probe - API está viva")
async def liveness_check():
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}
