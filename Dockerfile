# NutriScale OS — Backend container
# No external Python libraries needed (stdlib only) — so the image is light.
FROM python:3.12-slim
WORKDIR /app
COPY src/ ./src/
COPY backend/ ./backend/
COPY dashboard/ ./dashboard/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY CONNECTORS_SETUP.md ./
ENV PORT=8765
EXPOSE 8765
# Volume for data: docker run -v nutriscale-data:/app/data ...
VOLUME ["/app/data"]
CMD ["python3", "backend/app.py"]
