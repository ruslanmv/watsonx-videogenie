terraform {
  required_version = ">= 1.6"
  required_providers {
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = "~> 2.6"
    }
  }
}

provider "ibm" {
  region = var.region
}

resource "ibm_resource_group" "vg" {
  name = "videogenie-rg"
}

# CIS – DNS + edge
resource "ibm_cis" "zone" {
  name              = var.domain
  plan              = "standard-edge"
  resource_group_id = ibm_resource_group.vg.id
}

resource "ibm_cis_certificate" "wildcard" {
  cis_id    = ibm_cis.zone.id
  cert_type = "letsencrypt-dns"
  hosts     = ["*.${var.domain}"]
}

# Cloud Object Storage
resource "ibm_resource_instance" "cos" {
  name              = "vg-cos"
  service           = "cloud-object-storage"
  plan              = "standard"
  location          = var.region
  resource_group_id = ibm_resource_group.vg.id
}

resource "ibm_cos_bucket" "spa" {
  bucket_name              = "${var.prefix}-spa-assets"
  region                   = var.region
  storage_class            = var.cos_class
  ibm_resource_instance_id = ibm_resource_instance.cos.id
  website {
    index_document = "index.html"
  }
}

resource "ibm_cos_bucket" "videos" {
  bucket_name              = "${var.prefix}-videos-prod"
  region                   = var.region
  ibm_resource_instance_id = ibm_resource_instance.cos.id
  storage_class            = var.cos_class
  lifecycle_rule {
    id     = "archive-old"
    status = "Enabled"
    transition {
      days          = 30
      storage_class = "cold"
    }
  }
}

# App ID
resource "ibm_resource_instance" "appid" {
  name              = "vg-appid"
  service           = "appid"
  plan              = "lite"
  region            = var.region
  resource_group_id = ibm_resource_group.vg.id
}

# Event Streams (Kafka)
resource "ibm_resource_instance" "kafka" {
  name              = "vg-kafka"
  service           = "messagehub"
  plan              = var.event_streams_plan
  region            = var.region
  resource_group_id = ibm_resource_group.vg.id
}

resource "ibm_event_streams_api_key" "kafka_key" {
  name        = "vg-kafka-key"
  instance_id = ibm_resource_instance.kafka.id
}

# Log Analysis
resource "ibm_resource_instance" "logdna" {
  name              = "vg-logdna"
  service           = "logdna"
  plan              = "7-day-inactivity"
  region            = var.region
  resource_group_id = ibm_resource_group.vg.id
}

# Secrets Manager
resource "ibm_resource_instance" "secrets" {
  name              = "vg-secrets"
  service           = "secrets-manager"
  plan              = "standard"
  region            = var.region
  resource_group_id = ibm_resource_group.vg.id
}

resource "ibm_sm_secret" "watsonx" {
  instance_id = ibm_resource_instance.secrets.id
  secret_type = "arbitrary"
  name        = "watsonx-apikey"
  payload     = var.watsonx_apikey
}
