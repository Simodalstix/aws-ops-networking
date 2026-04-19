import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ssm as ssm,
)
from constructs import Construct


class NetworkingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        nat_type = self.node.try_get_context("nat_type") or "NONE"

        # ── VPC ──────────────────────────────────────────────────────────────

        subnet_configs = [
            ec2.SubnetConfiguration(
                name="public",
                subnet_type=ec2.SubnetType.PUBLIC,
                cidr_mask=24,
            ),
            ec2.SubnetConfiguration(
                name="isolated",
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                cidr_mask=24,
            ),
        ]

        if nat_type != "NONE":
            subnet_configs.append(
                ec2.SubnetConfiguration(
                    name="private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                )
            )

        vpc = ec2.Vpc(
            self,
            "Vpc",
            vpc_name="ops-lab-vpc-lab",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=3,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            # NAT Gateway only when explicitly requested — default is free
            nat_gateways=1 if nat_type == "GATEWAY" else 0,
            subnet_configuration=subnet_configs,
        )

        cdk.Tags.of(vpc).add("Project", "ops-lab")
        cdk.Tags.of(vpc).add("Stack", "networking")

        # ── S3 Gateway Endpoint ───────────────────────────────────────────────
        # Always attach — keeps S3 traffic off the public internet at no cost

        vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        # ── Shared SSM Security Group ─────────────────────────────────────────
        # Outbound-only; used by any instance that needs SSM Session Manager.
        # Downstream stacks read the ID from SSM and attach it to their instances.

        ssm_sg = ec2.SecurityGroup(
            self,
            "SsmSecurityGroup",
            vpc=vpc,
            security_group_name="ops-lab-ssm-sg-lab",
            description="Shared outbound-only SG for SSM Session Manager access",
            allow_all_outbound=True,
        )

        cdk.Tags.of(ssm_sg).add("Project", "ops-lab")
        cdk.Tags.of(ssm_sg).add("Stack", "networking")

        # ── SSM Parameter Store ───────────────────────────────────────────────

        self._put_param("vpc-id", vpc.vpc_id, "VPC ID")
        self._put_param("vpc-cidr", vpc.vpc_cidr_block, "VPC CIDR block")
        self._put_param("ssm-sg-id", ssm_sg.security_group_id, "Shared SSM security group ID")
        self._put_param("nat-type", nat_type, "NAT strategy in use (NONE or GATEWAY)")

        public_subnets = vpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC).subnets
        isolated_subnets = vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED).subnets

        for i, subnet in enumerate(public_subnets):
            self._put_param(f"subnet/public-{i}", subnet.subnet_id, f"Public subnet {i}")

        for i, subnet in enumerate(isolated_subnets):
            self._put_param(f"subnet/isolated-{i}", subnet.subnet_id, f"Isolated subnet {i}")

        if nat_type != "NONE":
            private_subnets = vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnets
            for i, subnet in enumerate(private_subnets):
                self._put_param(f"subnet/private-{i}", subnet.subnet_id, f"Private (NAT) subnet {i}")

        # ── Outputs ───────────────────────────────────────────────────────────

        cdk.CfnOutput(self, "VpcId", value=vpc.vpc_id, export_name="ops-lab-vpc-id")
        cdk.CfnOutput(self, "NatType", value=nat_type, export_name="ops-lab-nat-type")

    def _put_param(self, key: str, value: str, description: str) -> None:
        ssm.StringParameter(
            self,
            # Logical ID must be unique and CDK-safe
            "Param" + key.replace("/", "").replace("-", "").title().replace(" ", ""),
            parameter_name=f"/ops-lab/networking/{key}",
            string_value=value,
            description=description,
        )
