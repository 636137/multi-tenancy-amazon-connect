#!/usr/bin/env python3
"""CDK App for Flow Tester UI."""
import aws_cdk as cdk
from cdk.flow_tester_stack import FlowTesterStack

app = cdk.App()

FlowTesterStack(
    app, 'FlowTesterStack',
    env=cdk.Environment(
        account=app.node.try_get_context('account'),
        region=app.node.try_get_context('region') or 'us-east-1'
    ),
    description='Flow Tester UI - Test Amazon Connect flows with AI callers'
)

app.synth()
