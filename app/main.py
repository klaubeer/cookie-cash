import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import config
from app.integracoes.sheets import configurar_resumo
from app.utils.fila import worker
from app.webhook.router import router as webhook_router

logging.basicConfig(
    level=config.log_level,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "mensagem": "%(message)s"}',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Cookie Finance Bot iniciando")
    await configurar_resumo()
    tarefa_worker = asyncio.create_task(worker())
    yield
    tarefa_worker.cancel()
    logger.info("Cookie Finance Bot encerrando")


app = FastAPI(title="Cookie Finance Bot", lifespan=lifespan)
app.include_router(webhook_router)


@app.get("/health")
def health():
    return {"status": "ok"}
