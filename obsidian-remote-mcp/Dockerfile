FROM python:3.11-slim AS builder

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY pyproject.toml ./
COPY src ./src
RUN pip install .

FROM python:3.11-slim AS runtime
ENV VIRTUAL_ENV=/opt/venv
COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /app
COPY src ./src
COPY pyproject.toml ./
EXPOSE 8000
ENV HOST=0.0.0.0
ENV PORT=8000
CMD ["python", "-m", "obsidian_remote_mcp.server"]
