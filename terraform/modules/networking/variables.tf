variable "project" {
  type        = string
  description = "Project name for resource tagging"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "CIDR block for the VPC"
}

variable "demo_ssh_cidr" {
  type        = string
  description = "Your public IP in CIDR notation (e.g. 203.0.113.50/32) for SSH access during demo"
}
