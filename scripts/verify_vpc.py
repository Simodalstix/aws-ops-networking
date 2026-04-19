#!/usr/bin/env python3
"""
Post-deploy verification: reads SSM parameters written by OpsNetworkingStack
and confirms the VPC and subnets exist in EC2.
"""
import boto3
import sys

REGION = "ap-southeast-2"
SSM_PREFIX = "/ops-lab/networking"

ec2 = boto3.client("ec2", region_name=REGION)
ssm = boto3.client("ssm", region_name=REGION)


def get_param(key: str) -> str:
    resp = ssm.get_parameter(Name=f"{SSM_PREFIX}/{key}")
    return resp["Parameter"]["Value"]


def check(label: str, ok: bool, detail: str = "") -> None:
    status = "OK  " if ok else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    if not ok:
        sys.exit(1)


def main() -> None:
    print("=== aws-ops-networking post-deploy verification ===\n")

    vpc_id = get_param("vpc-id")
    vpc_cidr = get_param("vpc-cidr")
    ssm_sg_id = get_param("ssm-sg-id")
    nat_type = get_param("nat-type")

    print(f"VPC ID   : {vpc_id}")
    print(f"VPC CIDR : {vpc_cidr}")
    print(f"SSM SG   : {ssm_sg_id}")
    print(f"NAT type : {nat_type}\n")

    # VPC
    vpcs = ec2.describe_vpcs(VpcIds=[vpc_id])["Vpcs"]
    check("VPC exists", len(vpcs) == 1, vpc_id)
    check("VPC CIDR correct", vpcs[0]["CidrBlock"] == "10.0.0.0/16", vpcs[0]["CidrBlock"])
    check("DNS hostnames enabled", vpcs[0].get("EnableDnsHostnames", False))

    # Security group
    sgs = ec2.describe_security_groups(GroupIds=[ssm_sg_id])["SecurityGroups"]
    check("SSM security group exists", len(sgs) == 1, ssm_sg_id)
    check("SSM SG has no inbound rules", sgs[0]["IpPermissions"] == [])

    # Subnets
    for tier in ("public", "isolated"):
        for i in range(3):
            subnet_id = get_param(f"subnet/{tier}-{i}")
            subnets = ec2.describe_subnets(SubnetIds=[subnet_id])["Subnets"]
            check(f"{tier} subnet {i} exists", len(subnets) == 1, subnet_id)

    if nat_type != "NONE":
        for i in range(3):
            subnet_id = get_param(f"subnet/private-{i}")
            subnets = ec2.describe_subnets(SubnetIds=[subnet_id])["Subnets"]
            check(f"private subnet {i} exists", len(subnets) == 1, subnet_id)

        # Confirm NAT Gateway is active
        nat_gws = ec2.describe_nat_gateways(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "state", "Values": ["available"]},
            ]
        )["NatGateways"]
        check("NAT Gateway active", len(nat_gws) >= 1)

    # S3 Gateway Endpoint
    endpoints = ec2.describe_vpc_endpoints(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
            {"Name": "service-name", "Values": [f"com.amazonaws.{REGION}.s3"]},
            {"Name": "vpc-endpoint-type", "Values": ["Gateway"]},
            {"Name": "vpc-endpoint-state", "Values": ["available"]},
        ]
    )["VpcEndpoints"]
    check("S3 Gateway Endpoint active", len(endpoints) >= 1)

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
