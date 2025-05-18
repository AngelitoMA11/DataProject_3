FROM grafana/grafana:latest

# Instalar plugin BigQuery
RUN grafana-cli plugins install grafana-bigquery-datasource

# Copiar dashboards y datasources
COPY dashboards /etc/grafana/provisioning/dashboards
COPY datasource.yaml /etc/grafana/provisioning/datasources/datasource.yaml
