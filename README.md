# aws-ops-networking

Foundation networking stack for the ops-lab platform. Deploys a VPC and writes all resource IDs to SSM Parameter Store — every downstream stack reads from there at deploy time.

**Region:** ap-southeast-2 | **Account:** 820242933814 | **IaC:** CDK Python + Poetry

---

## What it deploys

- VPC `10.0.0.0/16` across 3 AZs, DNS enabled
- Public subnets (IGW routed) × 3
- Isolated subnets (no outbound route, database tier) × 3
- Private subnets (NAT routed) × 3 — only when `nat_type=GATEWAY`
- Internet Gateway
- S3 Gateway Endpoint (always — free, keeps S3 traffic off NAT)
- Shared SSM security group (outbound-only, attach to any instance needing Session Manager)

## SSM parameters written

```
/ops-lab/networking/vpc-id
/ops-lab/networking/vpc-cidr
/ops-lab/networking/ssm-sg-id
/ops-lab/networking/nat-type
/ops-lab/networking/subnet/public-{0,1,2}
/ops-lab/networking/subnet/isolated-{0,1,2}
/ops-lab/networking/subnet/private-{0,1,2}   # only when nat_type=GATEWAY
```

## Deploy

```bash
poetry install

# Default — no NAT, no ongoing cost
poetry run cdk deploy

# With NAT Gateway — egress demos only (~$0.045/hr)
poetry run cdk deploy --context nat_type=GATEWAY
```

First-time bootstrap:
```bash
poetry run cdk bootstrap aws://820242933814/ap-southeast-2
```

## Verify

```bash
# Check all SSM params were written
aws ssm get-parameters-by-path \
  --path /ops-lab/networking/ \
  --recursive \
  --query "Parameters[*].{Name:Name,Value:Value}" \
  --output table \
  --region ap-southeast-2

# Boto3 VPC verification script
poetry run python scripts/verify_vpc.py
```

## Destroy

```bash
poetry run cdk destroy
```

SSM parameters are removed with the stack. If deployed with `nat_type=GATEWAY`, the NAT Gateway EIP is also released.

---

## Consuming from downstream stacks

Read parameters at CDK synth time:

```python
from aws_cdk import aws_ssm as ssm

vpc_id = ssm.StringParameter.value_from_lookup(self, "/ops-lab/networking/vpc-id")
```

Or in shell:

```bash
aws ssm get-parameter \
  --name /ops-lab/networking/vpc-id \
  --query Parameter.Value \
  --output text \
  --region ap-southeast-2
```

See `docs/cli-playbooks/01-networking.md` for full operational reference.
