variable "region" {
  type = string
  default = "ap-south-1"
}
variable "project" {
  type = string
  default = "taskmanager"
}
variable "vpc_cidr" {
  type = string
  default = "10.0.0.0/16"
}
variable "subnet_cidr" {
  type = string
  default = "10.0.1.0/24"
}
variable "instance_type" {
  type = string
  default = "t3.medium"
}
variable "public_key" {
  type = string
  description = "SSH public key contents"
}
variable "allowed_ssh_cidr" {
  type        = string
  default     = "0.0.0.0/0"
  description = "Restrict to your IP/32 in real use"
}
