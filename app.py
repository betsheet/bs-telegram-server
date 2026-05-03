from fastapi import FastAPI
from routers.auth_router import router as auth_router
from routers.channels_router import router as channels_router
from routers.listening_router import router as listening_router

app: FastAPI = FastAPI()

app.include_router(auth_router)
app.include_router(channels_router)
app.include_router(listening_router)

@app.get("/")
def root():
    return {"status": "ok"}


if __name__ == "__main__":
    # Para pruebas rápidas sin necesidad de levantar toda la infraestructura de microservicios
    # asyncio.run(get_telegram_app_credentials())
    import uvicorn
    uvicorn.run(app, host="localhost", port=8008)