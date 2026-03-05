"""
CDK Stack for Flow Tester UI

Deploys:
- S3 bucket for React UI
- CloudFront distribution
- API Gateway with Lambda integrations
- Lambda functions for flow parsing and test execution
- DynamoDB table for scenarios
"""
from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_s3_deployment as s3_deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
)
from constructs import Construct
import os


class FlowTesterStack(Stack):
    """CDK Stack for Flow Tester UI application."""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Get config from context
        sip_media_app_id = self.node.try_get_context('sip_media_app_id') or ''
        from_number = self.node.try_get_context('from_number') or ''
        
        # ============================================
        # DynamoDB Table for Test Scenarios
        # ============================================
        
        scenarios_table = dynamodb.Table(
            self, 'ScenariosTable',
            table_name='flow-test-scenarios',
            partition_key=dynamodb.Attribute(
                name='scenario_id',
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute='ttl'
        )
        
        # Add GSI for status queries
        scenarios_table.add_global_secondary_index(
            index_name='status-index',
            partition_key=dynamodb.Attribute(
                name='status',
                type=dynamodb.AttributeType.STRING
            )
        )
        
        # ============================================
        # Lambda Functions
        # ============================================
        
        # Shared Lambda layer with common dependencies
        lambda_layer = lambda_.LayerVersion(
            self, 'CommonLayer',
            code=lambda_.Code.from_asset('lambda-layer'),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description='Common dependencies for Flow Tester lambdas'
        )
        
        # Parse Flow Lambda
        parse_flow_fn = lambda_.Function(
            self, 'ParseFlowFunction',
            function_name='flow-tester-parse-flow',
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler='handler.handler',
            code=lambda_.Code.from_asset('lambda/parse-flow'),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                'LOG_LEVEL': 'INFO'
            }
        )
        
        # Generate Tests Lambda
        generate_tests_fn = lambda_.Function(
            self, 'GenerateTestsFunction',
            function_name='flow-tester-generate-tests',
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler='handler.handler',
            code=lambda_.Code.from_asset('lambda/generate-tests'),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                'SCENARIOS_TABLE': scenarios_table.table_name
            }
        )
        scenarios_table.grant_write_data(generate_tests_fn)
        
        # Run Tests Lambda
        run_tests_fn = lambda_.Function(
            self, 'RunTestsFunction',
            function_name='flow-tester-run-tests',
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler='handler.handler',
            code=lambda_.Code.from_asset('lambda/run-tests'),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                'SCENARIOS_TABLE': scenarios_table.table_name,
                'SIP_MEDIA_APP_ID': sip_media_app_id,
                'FROM_NUMBER': from_number
            }
        )
        scenarios_table.grant_read_write_data(run_tests_fn)
        
        # Grant Chime SDK permissions
        run_tests_fn.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'chime:CreateSipMediaApplicationCall',
                'chime:UpdateSipMediaApplicationCall',
                'chime:GetSipMediaApplicationCall'
            ],
            resources=['*']
        ))
        
        # Get Results Lambda
        get_results_fn = lambda_.Function(
            self, 'GetResultsFunction',
            function_name='flow-tester-get-results',
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler='handler.get_test_results',
            code=lambda_.Code.from_asset('lambda/run-tests'),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                'SCENARIOS_TABLE': scenarios_table.table_name
            }
        )
        scenarios_table.grant_read_data(get_results_fn)
        
        # ============================================
        # API Gateway
        # ============================================
        
        api = apigw.RestApi(
            self, 'FlowTesterApi',
            rest_api_name='Flow Tester API',
            description='API for Flow Tester UI',
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=['Content-Type', 'Authorization']
            )
        )
        
        # /parse endpoint
        parse_resource = api.root.add_resource('parse')
        parse_resource.add_method(
            'POST',
            apigw.LambdaIntegration(parse_flow_fn)
        )
        
        # /generate endpoint  
        generate_resource = api.root.add_resource('generate')
        generate_resource.add_method(
            'POST',
            apigw.LambdaIntegration(generate_tests_fn)
        )
        
        # /run endpoint
        run_resource = api.root.add_resource('run')
        run_resource.add_method(
            'POST',
            apigw.LambdaIntegration(run_tests_fn)
        )
        
        # /results endpoint
        results_resource = api.root.add_resource('results')
        results_resource.add_method(
            'POST',
            apigw.LambdaIntegration(get_results_fn)
        )
        
        # ============================================
        # S3 Bucket for React UI
        # ============================================
        
        ui_bucket = s3.Bucket(
            self, 'UIBucket',
            bucket_name=f'flow-tester-ui-{self.account}',
            website_index_document='index.html',
            website_error_document='index.html',
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
        
        # ============================================
        # CloudFront Distribution
        # ============================================
        
        oai = cloudfront.OriginAccessIdentity(
            self, 'OAI',
            comment='OAI for Flow Tester UI'
        )
        ui_bucket.grant_read(oai)
        
        distribution = cloudfront.Distribution(
            self, 'Distribution',
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(ui_bucket, origin_access_identity=oai),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED
            ),
            additional_behaviors={
                '/api/*': cloudfront.BehaviorOptions(
                    origin=origins.RestApiOrigin(api),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER
                )
            },
            default_root_object='index.html',
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path='/index.html',
                    ttl=Duration.seconds(0)
                )
            ]
        )
        
        # ============================================
        # Outputs
        # ============================================
        
        CfnOutput(self, 'CloudFrontURL',
            value=f'https://{distribution.distribution_domain_name}',
            description='CloudFront URL for Flow Tester UI'
        )
        
        CfnOutput(self, 'ApiEndpoint',
            value=api.url,
            description='API Gateway endpoint'
        )
        
        CfnOutput(self, 'S3Bucket',
            value=ui_bucket.bucket_name,
            description='S3 bucket for UI files'
        )
        
        CfnOutput(self, 'ScenariosTable',
            value=scenarios_table.table_name,
            description='DynamoDB table for test scenarios'
        )
