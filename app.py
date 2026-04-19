#!/usr/bin/env python3
import aws_cdk as cdk
from networking_lab.networking_stack import NetworkingStack

app = cdk.App()

NetworkingStack(
    app,
    "OpsNetworkingStack",
    env=cdk.Environment(
        account="820242933814",
        region="ap-southeast-2",
    ),
)

app.synth()
