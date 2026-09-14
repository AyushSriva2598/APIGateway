provider "aws" {
  region = var.region
}

module "networking" {
  source        = "./modules/networking"
  project       = var.project
  vpc_cidr      = var.vpc_cidr
  demo_ssh_cidr = var.demo_ssh_cidr
}

module "cache" {
  source                  = "./modules/cache"
  project                 = var.project
  private_subnet_ids      = module.networking.private_subnet_ids
  redis_security_group_id = module.networking.redis_security_group_id
}

module "compute" {
  source                    = "./modules/compute"
  project                   = var.project
  vpc_id                    = module.networking.vpc_id
  public_subnet_ids         = module.networking.public_subnet_ids
  alb_security_group_id     = module.networking.alb_security_group_id
  gateway_security_group_id = module.networking.gateway_security_group_id
  key_pair_name             = var.key_pair_name
  redis_host                = module.cache.endpoint
  redis_port                = module.cache.port
  django_secret_key         = var.django_secret_key
  allowed_hosts             = var.allowed_hosts
}

module "monitoring" {
  source                 = "./modules/monitoring"
  project                = var.project
  region                 = var.region
  alert_email            = var.alert_email
  target_group_arn_suffix = module.compute.target_group_arn_suffix
  alb_arn_suffix         = module.compute.alb_arn_suffix
  asg_name               = module.compute.asg_name
  cache_cluster_id       = module.cache.cluster_id
}

module "dns" {
  source           = "./modules/dns"
  project          = var.project
  domain_name      = var.domain_name
  alb_dns_name     = module.compute.alb_dns_name
  alb_zone_id      = module.compute.alb_zone_id
  alb_arn          = module.compute.alb_arn
  target_group_arn = module.compute.target_group_arn
}
