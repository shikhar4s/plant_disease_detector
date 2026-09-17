FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY plant_disease_detector_frontend/package*.json ./
RUN npm ci
COPY plant_disease_detector_frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY plant_disease_detector/requirements.txt /app/plant_disease_detector/requirements.txt
RUN pip install --no-cache-dir -r /app/plant_disease_detector/requirements.txt
COPY plant_disease_detector/ /app/plant_disease_detector/
COPY scripts/start.sh /app/scripts/start.sh
COPY scripts/prepare_model.py /app/scripts/prepare_model.py
RUN python /app/scripts/prepare_model.py
COPY --from=frontend /build/dist /app/plant_disease_detector_frontend/dist
RUN DEBUG=true python /app/plant_disease_detector/manage.py collectstatic --noinput
EXPOSE 8000
CMD ["bash", "/app/scripts/start.sh"]

