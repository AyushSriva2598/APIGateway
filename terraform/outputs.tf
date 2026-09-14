output "alb_url" {
  value       = "http://${module.compute.alb_dns_name}"
  description = "Public ALB URL"
}

output "health_check" {
  value       = "curl -s http://${module.compute.alb_dns_name}/healthz | jq ."
  description = "Command to test the deployment"
}

output "cloudwatch_dashboard" {
  value       = module.monitoring.dashboard_url
  description = "CloudWatch dashboard URL"
}

output "domain_url" {
  value       = module.dns.domain_url
  description = "Custom domain URL (if configured)"
}

output "route53_nameservers" {
  value       = module.dns.nameservers
  description = "Update your domain registrar NS records to these"
}

output "teardown" {
  value       = "terraform destroy -auto-approve"
  description = "Command to destroy all demo infrastructure"
}
