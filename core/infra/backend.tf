terraform {
  required_version = ">= 1.4.0"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.29"
    }
  }

  backend "local" {
    path = "terraform.tfstate"
  }
}
