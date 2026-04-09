variable "environment" {
  type = string
}

variable "domain_slug" {
  type = string
}

variable "data_owner" {
  type = string
}

variable "data_retention_days" {
  type = number
}

variable "enable_pii_masking" {
  type = bool
}
