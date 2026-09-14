variable "project" {
  type        = string
  description = "Project name for resource tagging"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for ElastiCache subnet group"
}

variable "redis_security_group_id" {
  type        = string
  description = "Security group ID allowing Redis access"
}
