# Симулятор внешних источников (ЕГРЮЛ/ЕГРИП, НБКИ, «Прозрачный бизнес»)
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.11.32

WORKDIR /app

# Сначала зависимости — слой кэшируется, пока не меняется uv.lock
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# Код и синтетические данные: симулятор самодостаточен, внешних томов не требует
COPY simulator ./simulator
COPY data ./data

RUN useradd --system --uid 10002 --no-create-home mockuser
USER mockuser

EXPOSE 8001

CMD ["uvicorn", "simulator.main:app", "--host", "0.0.0.0", "--port", "8001"]
