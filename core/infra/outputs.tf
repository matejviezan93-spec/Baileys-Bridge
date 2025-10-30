locals {
  primary_ipv4 = try(digitalocean_floating_ip.app[0].ip_address, digitalocean_droplet.app.ipv4_address)
}

output "droplet_ipv4" {
  description = "Primary IPv4 address for the Baileys Bridge droplet"
  value       = local.primary_ipv4
}

output "ssh_connect" {
  description = "Convenient SSH command to connect to the droplet"
  value       = "ssh root@${local.primary_ipv4}"
}
