output "nameservers" {
  value       = var.domain_name != "" ? aws_route53_zone.main[0].name_servers : []
  description = "Point your domain registrar NS records to these"
}

output "domain_url" {
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "N/A (no domain configured)"
  description = "Domain URL if configured"
}
