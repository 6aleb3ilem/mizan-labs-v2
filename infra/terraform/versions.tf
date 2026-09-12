terraform {
  required_version = ">= 1.9"
  required_providers {
    google     = { source = "hashicorp/google", version = "~> 6.0" }
    cloudflare = { source = "cloudflare/cloudflare", version = "~> 5.0" }
    random     = { source = "hashicorp/random", version = "~> 3.6" }
  }
  backend "gcs" {
    # bucket and prefix are given with `terraform init -backend-config=environments/<env>.backend.hcl`
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}
