---
name: aws-deployment
description: Deploy AWS infrastructure with Amazon Connect, Lex, Lambda, and other services. Use for end-to-end deployment automation with error handling, self-healing, idempotent operations, and security best practices.
argument-hint: "[service] [action]"
user-invocable: true
disable-model-invocation: false
---

# AWS Infrastructure Deployment Skill

Expert guidance for deploying AWS infrastructure with robust error handling and self-healing capabilities. Specializes in Amazon Connect, Lex V2, Lambda, DynamoDB, and other AWS services.

## Core Capabilities

### Smart Prerequisite Management
- Proactive system requirement detection
- Platform-aware installation (macOS, Linux)
- Adaptive installation methods based on permissions:
  - macOS without sudo → nvm, pip --user, local installs
  - macOS with sudo → Homebrew, system installs
  - Linux → apt, yum, or compiled from source

### AWS Service State Machines
- Resource lifecycle state awareness:
  - Lex bots: Creating → Available → Built
  - Connect instances: Creating → Active
  - Lambda: Pending → Active
  - DynamoDB: Creating → Active
- Exponential backoff with progress updates
- Async operation handling

### Error Pattern Recognition & Self-Healing
- API version awareness (Lex V1 vs V2)
- Auto-fix common issues:
  - Resource timing → Add wait loops
  - Missing permissions → Suggest IAM policy updates
  - Wrong parameter formats → Auto-convert
  - Conflicting resources → Skip or update existing
- Automatic rollback script generation

### Idempotent Deployment
- Check before create
- Update vs create intelligence
- State tracking for resume capability
- Partial failure recovery

## Deployment Workflow Pattern

```
1. Validate Prerequisites
   ├── Check OS and permissions
   ├── Verify required tools
   └── Test AWS credentials

2. Plan Deployment
   ├── Analyze dependencies
   ├── Calculate costs
   └── Generate deployment order

3. Deploy Infrastructure (CDK/CloudFormation)
   ├── Create foundational resources
   ├── Deploy databases
   ├── Deploy compute (Lambda)
   └── Set up IAM roles

4. Deploy Application Services
   ├── Create Connect instance (wait for active)
   ├── Create Lex bot (wait for available)
   ├── Configure integrations
   └── Import contact flows

5. Test & Validate
   ├── Run unit tests
   ├── Run integration tests
   └── Verify end-to-end flow

6. Generate Documentation
   ├── Deployment summary
   ├── Access instructions
   └── Maintenance procedures

7. Cleanup on Failure
   ├── Rollback partial deployments
   └── Clean up orphaned resources
```

## AWS Service-Specific Knowledge

### Amazon Lex V2
- Bot creation is asynchronous - wait for "Available" state
- Locales require parent bot to be ready before creation
- Slot types must exist before creating intents
- Build operation is separate and takes time
- Exception: Use `ConflictException`, not `ResourceConflictException`
- Enum values: Use PascalCase (e.g., "TopResolution")

### Amazon Connect
- Instance creation takes several minutes
- Storage configuration requires instance to be active
- Contact flows are JSON with specific structure
- Lambda integration requires explicit permissions
- Phone number claiming may require manual steps

### AWS Lambda
- Handle import paths and dependencies carefully
- Environment variables for configuration
- Separate execution role from resource access
- Set timeouts appropriately
- Use layers for shared dependencies

### DynamoDB
- Plan partition key + sort key design
- Choose on-demand vs provisioned billing
- Enable point-in-time recovery
- Plan GSI/LSI before table creation

### IAM
- Service principals vary by service
- Trust policies vs permissions policies
- Prefer managed policies where possible
- Use role assumption for cross-service access

## Error Handling Patterns

### Timing Issues
```python
def wait_for_resource(service, resource_id, target_state, max_wait=300):
    wait_time = 5
    total_waited = 0
    while total_waited < max_wait:
        status = check_resource_status(service, resource_id)
        if status == target_state:
            return True
        elif status in FAILED_STATES:
            raise DeploymentError(f"Resource entered failed state: {status}")
        time.sleep(wait_time)
        total_waited += wait_time
        wait_time = min(wait_time * 1.5, 30)  # Exponential backoff
    raise TimeoutError(f"Resource did not reach {target_state}")
```

### Permission Issues
```python
def handle_permission_error(error, resource_type):
    required_actions = get_required_actions(resource_type)
    return {
        "error": str(error),
        "missing_actions": missing_actions,
        "suggested_policy": generate_policy(missing_actions)
    }
```

## Security Best Practices

- Use .env files with .gitignore
- Prefer IAM roles over access keys
- Use AWS Secrets Manager for production
- Never log credentials
- Create least-privilege IAM policies
- Enable encryption at rest and in transit
- Check for common security misconfigurations

## Cost Awareness

- Calculate costs before deployment
- Tag all resources for cost tracking
- Suggest cheaper alternatives when appropriate
- Set up CloudWatch alarms for cost thresholds

## Common Pitfalls to Avoid

1. **Don't assume resources are ready immediately** - Always wait and verify
2. **Don't hardcode ARNs or IDs** - Get them from stack outputs
3. **Don't skip error handling** - AWS operations fail frequently
4. **Don't forget to test permissions** - Test with least privilege first
5. **Don't ignore costs** - Calculate and warn about expensive resources
6. **Don't deploy without rollback plan** - Always have an undo strategy
7. **Don't log secrets** - Sanitize logs and output
8. **Don't skip validation** - Verify each step before proceeding

## Success Criteria

A successful deployment includes:
- [ ] All resources created and verified
- [ ] Tests passing end-to-end
- [ ] Documentation generated with actual resource IDs
- [ ] Security best practices implemented
- [ ] Monitoring and alarms configured
- [ ] Cost estimates provided
- [ ] Rollback scripts available
- [ ] Access instructions clear and tested

## Behavior Guidelines

### Do:
- Check prerequisites before starting
- Provide progress updates frequently
- Generate comprehensive documentation
- Test after each deployment step
- Handle errors gracefully with auto-recovery
- Ask for confirmation on destructive operations
- Estimate costs before deployment
- Create rollback scripts proactively

### Don't:
- Assume tools are installed
- Skip error handling
- Deploy without testing
- Hardcode credentials
- Ignore AWS service limits
- Create resources without tags
- Leave orphaned resources on failure
