output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "alb_security_group_id" {
  value = aws_security_group.alb.id
}

output "gateway_security_group_id" {
  value = aws_security_group.gateway.id
}

output "redis_security_group_id" {
  value = aws_security_group.redis.id
}
