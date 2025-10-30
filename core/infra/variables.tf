variable "do_token" {
  type        = string
  description = "DigitalOcean API token"
  sensitive   = true
}

variable "region" {
  type        = string
  description = "Region slug where resources will be created"
  default     = "sgp1"
}

variable "droplet_name" {
  type        = string
  description = "Name for the Baileys Bridge droplet"
  default     = "baileys-bridge"
}

variable "ssh_key_id" {
  type        = string
  description = "DigitalOcean SSH key ID or fingerprint to inject into the droplet"
}

variable "enable_floating_ip" {
  type        = bool
  description = "Whether to allocate and assign a floating IP to the droplet"
  default     = false
}
