# Crear el dataset
resource "google_bigquery_dataset" "dataset" {
  dataset_id = var.bq_dataset
  project    = var.project_id
}

# Crear múltiples tablas con su respectivo esquema
resource "google_bigquery_table" "table" {
  for_each  = { for t in var.tables : t.name => t }
  
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = each.value.name
  project    = var.project_id
  schema     = file(each.value.schema)
  deletion_protection  = false  
}


