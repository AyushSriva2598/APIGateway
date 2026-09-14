variable "project" {
  type        = string
  description = "Project name for resource tagging"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID"
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnet IDs for ALB and ASG"
}

variable "alb_security_group_id" {
  type        = string
  description = "Security group ID for the ALB"
}

variable "gateway_security_group_id" {
  type        = string
  description = "Security group ID for gateway EC2 instances"
}

variable "key_pair_name" {
  type        = string
  description = "EC2 key pair name for SSH access during demo"
}

variable "redis_host" {
  type        = string
  description = "ElastiCache Redis endpoint"
}

variable "redis_port" {
  type        = number
  description = "ElastiCache Redis port"
}

variable "django_secret_key" {
  type        = string
  sensitive   = true
  description = "Django SECRET_KEY"
}

variable "allowed_hosts" {
  type        = string
  description = "Django ALLOWED_HOSTS"
}
