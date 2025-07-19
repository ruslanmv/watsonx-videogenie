
# Terraform Infrastructure for VideoGenie on IBM Cloud

Welcome to the infrastructure repository for VideoGenie\! This Terraform module is designed to provision all the foundational IBM Cloud services required to run the VideoGenie stack. By managing these resources with Infrastructure as Code (IaC), we ensure a repeatable, consistent, and version-controlled setup.

This module handles everything outside of the OpenShift cluster, including DNS, CDN, security, storage, messaging, and logging. The philosophy is simple: apply this configuration once, use the outputs to configure your application's Helm chart and CI/CD pipelines, and you're ready to go.

-----

## ✨ Provisioned Resources

This module will create and configure the following IBM Cloud services:

  * **Resource Group:** A dedicated group (`videogenie-rg`) to contain all project resources for better organization and access management.
  * **Cloud Internet Services (CIS):** For managing the project's DNS zone, providing CDN caching, and provisioning a wildcard TLS certificate via Let's Encrypt.
  * **Cloud Object Storage (COS):** Two buckets are created:
      * `vg-spa-assets`: For hosting the static files of the front-end single-page application.
      * `vg-videos-prod`: For storing the generated MP4 video files, with a lifecycle rule to archive old videos to cold storage.
  * **App ID:** Provides authentication and authorization services for the application.
  * **Event Streams (Kafka):** A managed Kafka instance for asynchronous messaging between microservices.
  * **Log Analysis:** Centralized logging for the entire stack.
  * **Secrets Manager:** A secure vault for storing sensitive information, such as the `watsonx` API key.

-----

## 🚀 Getting Started

You can provision the infrastructure using either Terraform (recommended) or the IBM Cloud CLI for manual setup.

### **Prerequisites**

  * [Terraform CLI](https://learn.hashicorp.com/tutorials/terraform/install-cli) (version 1.6 or higher)
  * [IBM Cloud CLI](https://cloud.ibm.com/docs/cli)
  * An IBM Cloud account with the necessary permissions.
  * An API key for `watsonx` to be stored in Secrets Manager.

### **Option 1: Provisioning with Terraform (Recommended)**

1.  **Navigate to the Terraform Directory:**
    ```bash
    cd infra/terraform
    ```
2.  **Initialize Terraform:**
    This command downloads the required IBM Cloud provider plugin.
    ```bash
    terraform init
    ```
3.  **Apply the Configuration:**
    This command will provision all the resources defined in the `.tf` files. You will need to provide your domain name and `watsonx` API key.
    ```bash
    terraform apply -var="domain=videogenie.cloud" -var="watsonx_apikey=YOUR_API_KEY" -auto-approve
    ```
4.  **Destroying the Infrastructure:**
    When you no longer need the resources, you can tear them down with a single command.
    ```bash
    terraform destroy -var="domain=videogenie.cloud" -auto-approve
    ```

### **Option 2: Manual Provisioning with the IBM Cloud CLI**

If you prefer to create the resources manually, you can use the following commands.

```bash
# 1. Create and target a new resource group
ibmcloud resource group-create videogenie-rg
ibmcloud target -g videogenie-rg -r eu-de

# 2. Set up CIS for DNS and TLS
ibmcloud cis instance-create vg-cis standard-edge --reference-zone videogenie.cloud
ibmcloud cis tls-cert-create vg-cis --type letsencrypt-dns --hosts "*.videogenie.cloud"

# 3. Create Cloud Object Storage instance and buckets
ibmcloud resource service-instance-create vg-cos cloud-object-storage standard eu-de
ibmcloud cos bucket-create --bucket vg-spa-assets --ibm-service-instance-id $(ibmcloud resource service-instance vg-cos --id) --region eu-de --class standard --website
ibmcloud cos bucket-create --bucket vg-videos-prod --ibm-service-instance-id $(ibmcloud resource service-instance vg-cos --id) --region eu-de --class standard

# 4. Create App ID for authentication
ibmcloud resource service-instance-create vg-appid appid lite eu-de

# 5. Create Event Streams for messaging
ibmcloud resource service-instance-create vg-kafka messagehub standard eu-de
ibmcloud resource service-key-create kafka-key Manager --instance-id vg-kafka

# 6. Create Log Analysis for logging
ibmcloud resource service-instance-create vg-logdna logdna "7-day-inactivity" eu-de

# 7. Create Secrets Manager and store the watsonx API key
ibmcloud resource service-instance-create vg-secrets secrets-manager standard eu-de
ibmcloud secrets-manager secret-create --secret-type arbitrary --name watsonx-apikey --payload $WATSONX_APIKEY --instance-id vg-secrets
```

-----

## Terraform Module Details

### Input Variables (`variables.tf`)

The following variables can be used to customize the deployment.

| Variable Name | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `region` | The IBM Cloud region for resource deployment. | `string` | `eu-de` |
| `domain` | The root DNS domain for the project. | `string` | n/a |
| `prefix` | A prefix for resource names. | `string` | `vg` |
| `event_streams_plan` | The plan tier for the Kafka instance. | `string` | `standard` |
| `cos_class` | The storage class for the COS buckets. | `string` | `standard` |
| `watsonx_apikey` | The `watsonx` API key to store in Secrets Manager. | `string` | n/a |

### Outputs (`outputs.tf`)

After a successful `terraform apply`, the following outputs will be displayed. These are essential for configuring your application.

| Output Name | Description |
| :--- | :--- |
| `spa_bucket` | The name of the COS bucket for the front-end SPA. |
| `videos_bucket` | The name of the COS bucket for storing generated videos. |
| `cis_zone_id` | The ID of the CIS DNS zone. |
| `app_id_guid` | The GUID of the App ID instance. |
| `kafka_brokers` | The list of Kafka broker URLs for Event Streams. |
| `kafka_api_key` | The API key for connecting to Event Streams. |
| `jwks_url` | The JWKS URL from App ID for validating JWTs. |

-----

