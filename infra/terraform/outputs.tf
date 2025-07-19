output "spa_bucket" {
  value = ibm_cos_bucket.spa.bucket_name
}

output "videos_bucket" {
  value = ibm_cos_bucket.videos.bucket_name
}

output "cis_zone_id" {
  value = ibm_cis.zone.id
}

output "app_id_guid" {
  value = ibm_resource_instance.appid.guid
}

output "kafka_brokers" {
  value = ibm_resource_instance.kafka.kafka[0].kafka_admin_url
}

output "kafka_api_key" {
  value     = ibm_event_streams_api_key.kafka_key.api_key
  sensitive = true
}

output "jwks_url" {
  value = "https://${ibm_resource_instance.appid.guid}.appid.cloud.ibm.com/oauth/v4/${ibm_resource_instance.appid.guid}/publickeys"
}
