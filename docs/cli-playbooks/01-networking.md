# Networking Stack — CLI Playbook

## Deploy

```bash
# Activate virtualenv (first time)
poetry install
source .venv/bin/activate   # or: poetry shell

# Synthesise (dry run — no AWS calls)
cdk synth

# Deploy — no NAT (free, default)
cdk deploy

# Deploy — with NAT Gateway (costs ~$0.045/hr — egress demos only)
cdk deploy --context nat_type=GATEWAY
```

## Verify after deploy

```bash
python scripts/verify_vpc.py
```

## Read SSM parameters

```bash
# All networking params at once
aws ssm get-parameters-by-path \
  --path /ops-lab/networking \
  --recursive \
  --query "Parameters[*].{Name:Name,Value:Value}" \
  --output table \
  --region ap-southeast-2

# Single param
aws ssm get-parameter \
  --name /ops-lab/networking/vpc-id \
  --query Parameter.Value \
  --output text \
  --region ap-southeast-2
```

## Inspect VPC

```bash
# Get VPC ID from SSM, then describe it
VPC_ID=$(aws ssm get-parameter \
  --name /ops-lab/networking/vpc-id \
  --query Parameter.Value --output text \
  --region ap-southeast-2)

aws ec2 describe-vpcs --vpc-ids "$VPC_ID" \
  --query "Vpcs[0].{ID:VpcId,CIDR:CidrBlock,DNS:EnableDnsHostnames}" \
  --region ap-southeast-2

# List subnets
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].{ID:SubnetId,AZ:AvailabilityZone,CIDR:CidrBlock,Type:MapPublicIpOnLaunch}" \
  --output table \
  --region ap-southeast-2
```

## Destroy

```bash
cdk destroy
# SSM parameters are destroyed with the stack.
# If nat_type=GATEWAY was used, the NAT Gateway EIP is also released.
```

## Bootstrap (first-time only)

```bash
cdk bootstrap aws://820242933814/ap-southeast-2
```
