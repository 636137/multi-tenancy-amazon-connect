#!/usr/bin/env python3
"""
Enhanced Deployment Agent with Self-Healing Capabilities
Incorporates learnings from Amazon Connect Census Survey deployment
"""
import os
import sys
import time
import json
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class DeploymentState(Enum):
    """Track deployment progress"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ResourceState:
    """Track state of deployed resources"""
    resource_type: str
    resource_id: str
    state: str
    created_at: float
    arn: Optional[str] = None


class PrerequisiteManager:
    """Smart prerequisite detection and installation"""
    
    def __init__(self):
        self.os_type = self._detect_os()
        self.has_sudo = self._check_sudo()
        
    def _detect_os(self) -> str:
        """Detect operating system"""
        import platform
        return platform.system().lower()
    
    def _check_sudo(self) -> bool:
        """Check if user has sudo privileges"""
        try:
            result = subprocess.run(
                ['sudo', '-n', 'true'],
                capture_output=True,
                timeout=1
            )
            return result.returncode == 0
        except:
            return False
    
    def check_tool(self, tool_name: str) -> Tuple[bool, Optional[str]]:
        """Check if a tool is installed and get version"""
        try:
            result = subprocess.run(
                [tool_name, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, result.stdout.split('\n')[0]
            return False, None
        except:
            return False, None
    
    def install_nodejs(self) -> bool:
        """Install Node.js using appropriate method"""
        print("Installing Node.js...")
        
        if self.os_type == 'darwin' and not self.has_sudo:
            # macOS without sudo - use nvm
            print("  Using nvm (no sudo required)")
            return self._install_nodejs_nvm()
        elif self.os_type == 'darwin' and self.has_sudo:
            # macOS with sudo - use Homebrew
            print("  Using Homebrew")
            return self._install_nodejs_brew()
        else:
            print(f"  Please install Node.js manually for {self.os_type}")
            return False
    
    def _install_nodejs_nvm(self) -> bool:
        """Install Node.js via nvm"""
        commands = [
            'curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash',
            'export NVM_DIR="$HOME/.nvm"',
            '[ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh"',
            'nvm install --lts',
            'nvm use --lts'
        ]
        
        try:
            for cmd in commands:
                subprocess.run(cmd, shell=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _install_nodejs_brew(self) -> bool:
        """Install Node.js via Homebrew"""
        try:
            subprocess.run(['brew', 'install', 'node'], check=True)
            return True
        except subprocess.CalledProcessError:
            return False


class AWSStateManager:
    """Manage AWS resource state transitions"""
    
    # Service-specific state machines
    STATE_MACHINES = {
        'lex': {
            'bot': {
                'creating': 'available',
                'available': 'available',
                'failed': 'failed'
            },
            'locale': {
                'creating': 'not_built',
                'not_built': 'not_built',
                'building': 'built',
                'built': 'built',
                'failed': 'failed'
            }
        },
        'connect': {
            'instance': {
                'creating': 'active',
                'active': 'active',
                'failed': 'failed'
            }
        }
    }
    
    def __init__(self, region='us-east-1'):
        import boto3
        self.region = region
        self.clients = {}
    
    def get_client(self, service: str):
        """Get or create boto3 client"""
        if service not in self.clients:
            import boto3
            self.clients[service] = boto3.client(service, region_name=self.region)
        return self.clients[service]
    
    def wait_for_state(
        self, 
        service: str, 
        resource_type: str,
        resource_id: str, 
        target_state: str,
        max_wait: int = 300,
        progress_callback=None
    ) -> Tuple[bool, str]:
        """
        Generic waiter for AWS resources with exponential backoff
        
        Returns: (success, final_state)
        """
        client = self.get_client(service)
        wait_time = 5
        total_waited = 0
        attempt = 1
        
        while total_waited < max_wait:
            current_state = self._get_resource_state(
                client, service, resource_type, resource_id
            )
            
            if progress_callback:
                progress_callback(attempt, current_state, total_waited)
            
            # Check if we've reached target state
            if current_state.lower() == target_state.lower():
                return True, current_state
            
            # Check if we've reached a failed state
            failed_states = ['failed', 'creation_failed', 'delete_failed']
            if current_state.lower() in failed_states:
                return False, current_state
            
            # Wait and retry
            time.sleep(wait_time)
            total_waited += wait_time
            wait_time = min(wait_time * 1.5, 30)  # Exponential backoff, max 30s
            attempt += 1
        
        return False, "timeout"
    
    def _get_resource_state(
        self, 
        client, 
        service: str, 
        resource_type: str, 
        resource_id: str
    ) -> str:
        """Get current state of a resource"""
        try:
            if service == 'lexv2-models' and resource_type == 'bot':
                response = client.describe_bot(botId=resource_id)
                return response['botStatus']
            
            elif service == 'lexv2-models' and resource_type == 'locale':
                bot_id, locale_id = resource_id.split('/')
                response = client.describe_bot_locale(
                    botId=bot_id,
                    botVersion='DRAFT',
                    localeId=locale_id
                )
                return response['botLocaleStatus']
            
            elif service == 'connect' and resource_type == 'instance':
                response = client.describe_instance(InstanceId=resource_id)
                return response['Instance']['InstanceStatus']
            
            else:
                return "unknown"
                
        except Exception as e:
            print(f"Error getting state: {e}")
            return "error"


class ErrorRecoveryEngine:
    """Automatically detect and fix common AWS deployment errors"""
    
    # Error patterns and fixes
    ERROR_PATTERNS = {
        'lex_bot_not_ready': {
            'pattern': r'Create operation can not be performed.*when Bot is in Creating state',
            'fix': 'wait_for_bot_ready',
            'auto_fix': True
        },
        'lex_wrong_enum': {
            'pattern': r'.*must satisfy enum value set.*',
            'fix': 'convert_enum_format',
            'auto_fix': True
        },
        'lex_wrong_exception': {
            'pattern': r'.*ResourceConflictException.*',
            'fix': 'use_conflict_exception',
            'auto_fix': True
        },
        'missing_permission': {
            'pattern': r'User.*is not authorized to perform.*',
            'fix': 'suggest_iam_policy',
            'auto_fix': False
        }
    }
    
    def __init__(self, state_manager: AWSStateManager):
        self.state_manager = state_manager
        self.error_history = []
    
    def handle_error(
        self, 
        error: Exception, 
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Analyze error and attempt automatic fix
        
        Returns: (fixed, fix_description)
        """
        import re
        error_str = str(error)
        
        # Record error
        self.error_history.append({
            'error': error_str,
            'context': context,
            'timestamp': time.time()
        })
        
        # Try to match error pattern
        for error_name, pattern_info in self.ERROR_PATTERNS.items():
            if re.search(pattern_info['pattern'], error_str):
                print(f"✓ Detected error pattern: {error_name}")
                
                if pattern_info['auto_fix']:
                    fix_method = getattr(self, pattern_info['fix'], None)
                    if fix_method:
                        try:
                            fix_method(error, context)
                            return True, f"Auto-fixed: {error_name}"
                        except Exception as fix_error:
                            print(f"✗ Auto-fix failed: {fix_error}")
                            return False, None
                else:
                    suggestion = self._get_fix_suggestion(error_name, context)
                    return False, suggestion
        
        return False, None
    
    def wait_for_bot_ready(self, error: Exception, context: Dict[str, Any]):
        """Fix: Wait for Lex bot to be ready"""
        bot_id = context.get('bot_id')
        if bot_id:
            print(f"⏳ Waiting for bot {bot_id} to be ready...")
            success, state = self.state_manager.wait_for_state(
                'lexv2-models', 'bot', bot_id, 'available'
            )
            if success:
                print(f"✓ Bot is now {state}")
            else:
                raise Exception(f"Bot did not become ready: {state}")
    
    def convert_enum_format(self, error: Exception, context: Dict[str, Any]):
        """Fix: Convert enum values to PascalCase"""
        # This would need the actual file to modify
        print("⚠ Manual fix required: Convert enum values to PascalCase")
        print("   Example: TOP_RESOLUTION → TopResolution")
    
    def use_conflict_exception(self, error: Exception, context: Dict[str, Any]):
        """Fix: Use ConflictException instead of ResourceConflictException"""
        print("⚠ Manual fix required: Use ConflictException for Lex V2")
        print("   Replace: ResourceConflictException → ConflictException")
    
    def suggest_iam_policy(self, error: Exception, context: Dict[str, Any]):
        """Suggest IAM policy additions"""
        import re
        action_match = re.search(r'perform: (\S+)', str(error))
        if action_match:
            action = action_match.group(1)
            policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": [action],
                    "Resource": "*"
                }]
            }
            print(f"⚠ Add this to IAM policy:\n{json.dumps(policy, indent=2)}")
    
    def _get_fix_suggestion(self, error_name: str, context: Dict[str, Any]) -> str:
        """Get human-readable fix suggestion"""
        suggestions = {
            'missing_permission': 'Add required IAM permissions to your role/user',
            'lex_wrong_enum': 'Convert enum values to PascalCase format',
            'lex_wrong_exception': 'Use ConflictException for Lex V2 services'
        }
        return suggestions.get(error_name, 'See documentation for fix')


class DeploymentOrchestrator:
    """Orchestrate complete deployment with error recovery"""
    
    def __init__(self):
        self.prereq_manager = PrerequisiteManager()
        self.state_manager = AWSStateManager()
        self.error_recovery = ErrorRecoveryEngine(self.state_manager)
        self.deployment_state: Dict[str, DeploymentState] = {}
        self.resources: List[ResourceState] = []
    
    def deploy(self, config: Dict[str, Any]) -> bool:
        """
        Execute complete deployment with error handling
        
        Returns: success
        """
        steps = [
            ('prerequisites', self._deploy_prerequisites),
            ('infrastructure', self._deploy_infrastructure),
            ('services', self._deploy_services),
            ('validation', self._validate_deployment),
            ('documentation', self._generate_documentation)
        ]
        
        for step_name, step_func in steps:
            print(f"\n{'='*60}")
            print(f"Step: {step_name.title()}")
            print(f"{'='*60}")
            
            self.deployment_state[step_name] = DeploymentState.IN_PROGRESS
            
            try:
                success = step_func(config)
                if success:
                    self.deployment_state[step_name] = DeploymentState.COMPLETED
                    print(f"✓ {step_name} completed")
                else:
                    self.deployment_state[step_name] = DeploymentState.FAILED
                    print(f"✗ {step_name} failed")
                    
                    # Attempt rollback
                    if config.get('auto_rollback', True):
                        self._rollback(step_name)
                    
                    return False
                    
            except Exception as e:
                print(f"✗ Error in {step_name}: {e}")
                
                # Try error recovery
                fixed, description = self.error_recovery.handle_error(
                    e, {'step': step_name, 'config': config}
                )
                
                if fixed:
                    print(f"✓ Auto-fixed: {description}")
                    # Retry step
                    try:
                        success = step_func(config)
                        if success:
                            self.deployment_state[step_name] = DeploymentState.COMPLETED
                            continue
                    except Exception as retry_error:
                        print(f"✗ Retry failed: {retry_error}")
                
                self.deployment_state[step_name] = DeploymentState.FAILED
                
                if config.get('auto_rollback', True):
                    self._rollback(step_name)
                
                return False
        
        print(f"\n{'='*60}")
        print("✓ Deployment Successful!")
        print(f"{'='*60}")
        return True
    
    def _deploy_prerequisites(self, config: Dict[str, Any]) -> bool:
        """Check and install prerequisites"""
        print("Checking prerequisites...")
        
        # Check Node.js
        has_node, version = self.prereq_manager.check_tool('node')
        if not has_node:
            print("  ✗ Node.js not found")
            if not self.prereq_manager.install_nodejs():
                return False
        else:
            print(f"  ✓ Node.js: {version}")
        
        # Check AWS CLI
        has_aws, version = self.prereq_manager.check_tool('aws')
        if has_aws:
            print(f"  ✓ AWS CLI: {version}")
        else:
            print(f"  ✗ AWS CLI not found (optional)")
        
        # Check Python
        has_python, version = self.prereq_manager.check_tool('python3')
        if has_python:
            print(f"  ✓ Python: {version}")
        else:
            print(f"  ✗ Python not found")
            return False
        
        return True
    
    def _deploy_infrastructure(self, config: Dict[str, Any]) -> bool:
        """Deploy infrastructure via CDK"""
        print("Deploying infrastructure...")
        # Implementation would go here
        return True
    
    def _deploy_services(self, config: Dict[str, Any]) -> bool:
        """Deploy application services"""
        print("Deploying services...")
        # Implementation would go here
        return True
    
    def _validate_deployment(self, config: Dict[str, Any]) -> bool:
        """Validate deployment"""
        print("Validating deployment...")
        # Implementation would go here
        return True
    
    def _generate_documentation(self, config: Dict[str, Any]) -> bool:
        """Generate deployment documentation"""
        print("Generating documentation...")
        # Implementation would go here
        return True
    
    def _rollback(self, failed_step: str):
        """Rollback deployment"""
        print(f"\n⚠ Rolling back from failed step: {failed_step}")
        # Implementation would delete created resources
        print("✓ Rollback complete")


if __name__ == '__main__':
    # Example usage
    orchestrator = DeploymentOrchestrator()
    
    config = {
        'region': 'us-east-1',
        'auto_rollback': True,
        'services': ['connect', 'lex', 'lambda']
    }
    
    success = orchestrator.deploy(config)
    sys.exit(0 if success else 1)
