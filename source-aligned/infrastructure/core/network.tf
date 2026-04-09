# Protected: platform networking bindings — illustrative data sources only.
# Replace filters with your organization's shared VPC / service naming.

data "aws_vpc" "mesh_network" {
  tags = {
    Name = "sdp-shared-vpc-${var.environment}"
  }
}

data "aws_subnets" "mesh_private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.mesh_network.id]
  }
  tags = {
    Tier = "private"
  }
}
