# NutriScale OS — Backend container
# Koi bahari Python library nahi chahiye (sab stdlib hai) — isiliye image halki hai.
FROM python:3.12-slim
WORKDIR /app
COPY src/ ./src/
COPY backend/ ./backend/
COPY dashboard/ ./dashboard/
COPY config/ ./config/
COPY CONNECTORS_SETUP.md ./
ENV PORT=8765
EXPOSE 8765
# Data ke liye volume: docker run -v nutriscale-data:/app/data ...
VOLUME ["/app/data"]
CMD ["python3", "backend/app.py"]
