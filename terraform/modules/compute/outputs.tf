output "alb_dns_name" {
  value       = aws_lb.gateway.dns_name
  description = "ALB DNS name"
}

output "alb_zone_id" {
  value       = aws_lb.gateway.zone_id
  description = "ALB hosted zone ID for Route 53 alias"
}

output "alb_arn" {
  value       = aws_lb.gateway.arn
  description = "ALB ARN"
}

output "alb_arn_suffix" {
  value       = aws_lb.gateway.arn_suffix
  description = "ALB ARN suffix for CloudWatch metrics"
}

output "target_group_arn" {
  value       = aws_lb_target_group.gateway.arn
  description = "Target group ARN"
}

output "target_group_arn_suffix" {
  value       = aws_lb_target_group.gateway.arn_suffix
  description = "Target group ARN suffix for CloudWatch metrics"
}

output "asg_name" {
  value       = aws_autoscaling_group.gateway.name
  description = "ASG name for CloudWatch metrics"
}
