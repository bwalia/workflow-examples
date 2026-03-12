terraform {
  required_providers {
    citrixadc = {
      source  = "citrix/citrixadc"
      version = "~> 1.39"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}
