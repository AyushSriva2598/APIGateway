variable "project" {
  type        = string
  description = "Project name for resource tagging"
}

variable "region" {
  type        = string
  description = "AWS region"
}

variable "alert_email" {
  type        = string
  description = "Email address for SNS alarm notifications"
}

variable "alb_arn_suffix" {
  type        = string
  description = "ALB ARN suffix for CloudWatch dimensions"
}

variable "target_group_arn_suffix" {
  type        = string
  description = "Target group ARN suffix for CloudWatch dimensions"
}

variable "asg_name" {
  type        = string
  description = "Auto Scaling Group name for CloudWatch dimensions"
}

variable "cache_cluster_id" {
  type        = string
  description = "ElastiCache cluster ID for CloudWatch dimensions"
}
