output "endpoint" {
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
  description = "ElastiCache Redis endpoint address"
}

output "port" {
  value       = aws_elasticache_cluster.redis.cache_nodes[0].port
  description = "ElastiCache Redis port"
}

output "cluster_id" {
  value       = aws_elasticache_cluster.redis.cluster_id
  description = "ElastiCache cluster ID for CloudWatch metrics"
}
