variable "project" {
  type        = string
  default     = "apigateway"
  description = "Project name used for resource naming and tagging"
}

variable "region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "CIDR block for the VPC"
}

variable "demo_ssh_cidr" {
  type        = string
  description = "Your public IP in CIDR notation (e.g. 203.0.113.50/32) for SSH access"
}

variable "key_pair_name" {
  type        = string
  description = "Name of an existing EC2 key pair in the target region"
}

variable "django_secret_key" {
  type        = string
  sensitive   = true
  description = "Django SECRET_KEY for production settings"
}

variable "allowed_hosts" {
  type        = string
  default     = "*"
  description = "Django ALLOWED_HOSTS value"
}

variable "alert_email" {
  type        = string
  description = "Email address for CloudWatch alarm notifications via SNS"
}

variable "domain_name" {
  type        = string
  default     = ""
  description = "Domain name for Route 53 + ACM. Leave empty to skip DNS."
}
