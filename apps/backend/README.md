# BodeSmart API (apps/back)

Backend mínimo con FastAPI. Todo está en `main.py`.

## Arrancar

```powershell
cd C:\projects\project-software-design\apps\back
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Abre `http://localhost:8000/docs` para ver los endpoints.

## Endpoints

- `GET /` — mensaje de prueba
- `GET /health` — estado del servicio
