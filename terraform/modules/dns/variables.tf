variable "project" {
  type        = string
  description = "Project name for resource tagging"
}

variable "domain_name" {
  type        = string
  default     = ""
  description = "Domain name for Route 53 and ACM. Leave empty to skip DNS setup."
}

variable "alb_dns_name" {
  type        = string
  description = "ALB DNS name for Route 53 alias record"
}

variable "alb_zone_id" {
  type        = string
  description = "ALB hosted zone ID for Route 53 alias record"
}

variable "alb_arn" {
  type        = string
  description = "ALB ARN for HTTPS listener"
}

variable "target_group_arn" {
  type        = string
  description = "Target group ARN for HTTPS listener forwarding"
}
