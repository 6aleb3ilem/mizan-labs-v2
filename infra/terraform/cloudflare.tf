# Object storage: documents (immutable originals and renditions) and attachments.
resource "cloudflare_r2_bucket" "documents" {
  account_id = var.cloudflare_account_id
  name       = "${local.name}-documents"
  location   = "WEUR"
}

resource "cloudflare_r2_bucket" "attachments" {
  account_id = var.cloudflare_account_id
  name       = "${local.name}-attachments"
  location   = "WEUR"
}

# One Pages project per single-page application, with preview deployments per pull request.
resource "cloudflare_pages_project" "spa" {
  for_each          = local.spa_projects
  account_id        = var.cloudflare_account_id
  name              = "${local.name}-${each.key}"
  production_branch = "main"
  build_config = {
    build_command   = "pnpm install --frozen-lockfile && pnpm --filter @mizan/${each.key} build"
    destination_dir = "frontend/apps/${each.key}/dist"
    root_dir        = ""
  }
  deployment_configs = {
    preview = {
      env_vars = { VITE_API_BASE_URL = { type = "plain_text", value = "https://${local.api_host}/api/v1" } }
    }
    production = {
      env_vars = { VITE_API_BASE_URL = { type = "plain_text", value = "https://${local.api_host}/api/v1" } }
    }
  }
}

resource "cloudflare_pages_domain" "spa" {
  for_each     = local.spa_projects
  account_id   = var.cloudflare_account_id
  project_name = cloudflare_pages_project.spa[each.key].name
  name         = each.value
}

resource "cloudflare_dns_record" "spa" {
  for_each = local.spa_projects
  zone_id  = var.cloudflare_zone_id
  name     = each.value
  type     = "CNAME"
  content  = cloudflare_pages_project.spa[each.key].subdomain
  proxied  = true
  ttl      = 1
}

resource "cloudflare_dns_record" "api" {
  zone_id = var.cloudflare_zone_id
  name    = local.api_host
  type    = "CNAME"
  content = "ghs.googlehosted.com"
  proxied = true
  ttl     = 1
}

# WAF: rate limit the public verification endpoints harder than the rest (SPEC §18.5).
resource "cloudflare_ruleset" "verify_rate_limit" {
  zone_id = var.cloudflare_zone_id
  name    = "${local.name} verification rate limits"
  kind    = "zone"
  phase   = "http_ratelimit"
  rules = [{
    action      = "block"
    description = "digest lookups: 5 per minute per IP"
    expression  = "(http.host eq \"${local.api_host}\" and http.request.uri.path matches \"^/api/v1/verify/.*/digest$\")"
    ratelimit = {
      characteristics     = ["ip.src", "cf.colo.id"]
      period              = 60
      requests_per_period = 5
      mitigation_timeout  = 60
    }
    enabled = true
  }]
}
