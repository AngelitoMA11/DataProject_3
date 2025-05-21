FROM grafana/grafana:latest

# Instalar plugin BigQuery
RUN grafana-cli plugins install grafana-bigquery-datasource

# Copiar dashboards y datasources
COPY dashboard.yaml /etc/grafana/docker/dashboard.yaml
COPY datasource.yaml /etc/grafana/docker/datasource.yaml
