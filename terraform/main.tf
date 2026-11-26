module "network" {
  source      = "./modules/network"
  project     = var.project
  vpc_cidr    = var.vpc_cidr
  subnet_cidr = var.subnet_cidr
}

module "compute" {
  source           = "./modules/compute"
  project          = var.project
  vpc_id           = module.network.vpc_id
  subnet_id        = module.network.subnet_id
  instance_type    = var.instance_type
  public_key       = var.public_key
  allowed_ssh_cidr = var.allowed_ssh_cidr
}
