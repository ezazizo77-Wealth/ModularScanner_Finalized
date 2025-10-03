#!/usr/bin/env python3
"""
Enhanced Universal Message Router with robust environment variable loading
"""

import asyncio
import json
import uuid
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Custom environment variable loader - More reliable than dotenv
def load_env_variables():
    """Manually load environment variables from .env file"""
    env_file_path = '.env'
    
    # Check if .env file exists
    if not os.path.exists(env_file_path):
        print(f"Warning: {env_file_path} file not found")
        return False
    
    try:
        # Read the .env file
        with open(env_file_path, 'r') as f:
            lines = f.readlines()
        
        # Process each line
        env_vars_set = 0
        for line in lines:
            line = line.strip()
            # Skip empty lines or comments
            if not line or line.startswith('#'):
                continue
            
            # Split on the first equals sign
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                # Strip quotes if present
                value = value.strip().strip('\'"')
                # Set environment variable if not already set
                if not os.getenv(key):
                    os.environ[key] = value
                    env_vars_set += 1
            
        print(f"Loaded {env_vars_set} environment variables from {env_file_path}")
        
        # Debug output for critical variables (without showing values)
        print("Environment status after loading:")
        for key in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "OPENAI_API_KEY"]:
            print(f"  {key}: {'Set' if os.getenv(key) else 'Not set'}")
        
        return True
    except Exception as e:
        print(f"Error loading environment variables: {e}")
        return False

# Load environment variables before any imports that might use them
load_env_variables()

# Now try regular dotenv loading as backup
try:
    from dotenv import load_dotenv
    load_dotenv()  # This is now a backup method
except ImportError:
    print("Warning: python-dotenv not installed, using only manual environment loading")

# Import MCP components
from mcp.server import FastMCP
try:
    from openai import AsyncOpenAI
except ImportError:
    print("Warning: OpenAI library not installed")
    AsyncOpenAI = None

# Import other components (with error handling)
try:
    from session_manager import SessionManager, Message, Session
    from error_handler import ErrorHandler, LogLevel, StructuredLogger, RetryConfig, CircuitBreakerConfig, retry_on_failure, circuit_breaker_protection
    from performance_monitor import PerformanceMonitor, performance_monitor
    from notion_integration import NotionAPIIntegration, DecisionAnalysis
    from slack_integration import SlackAPIIntegration, NotificationData, NotificationType
except ImportError as e:
    print(f"Warning: Could not import some components: {e}")

class UniversalMessageRouter:
    """Enhanced Universal Message Router with improved environment handling"""
    
    def __init__(self):
        """Initialize the enhanced Universal Message Router"""
        self.server = FastMCP("universal-message-router")
        
        # Initialize system components
        self._init_logging()
        self._init_session_management()
        self._init_performance_monitoring()
        self._init_openai_client()
        self._init_oversight_system()
        self._init_retry_configuration()
        
        # Set up tools after components are initialized
        self.setup_tools()
        
        # Log initialization
        self.logger.log(
            LogLevel.INFO,
            "Universal Message Router initialized with enhanced environment handling",
            features=["robust_env_loading", "session_management", "error_handling", "performance_monitoring"]
        )
    
    def _init_logging(self):
        """Initialize logging system"""
        try:
            import os
            project_dir = os.path.dirname(os.path.abspath(__file__))
            log_file = os.path.join(project_dir, "universal_router.log")
            self.logger = StructuredLogger("universal-message-router", log_file)
            self.error_handler = ErrorHandler(self.logger)
        except Exception as e:
            print(f"Warning: Could not initialize logging: {e}")
            # Fallback logger
            class SimpleLogger:
                def log(self, level, message, **kwargs):
                    print(f"[{level}] {message}")
            self.logger = SimpleLogger()
            self.error_handler = None
    
    def _init_session_management(self):
        """Initialize session management"""
        try:
            import os
            project_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(project_dir, "sessions.db")
            self.session_manager = SessionManager(
                db_path=db_path,
                max_sessions=1000
            )
            self.phase_tracking = {}  # Simple in-memory phase tracking
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Session management initialization failed: {e}")
            self.session_manager = None
            self.phase_tracking = {}
    
    def _init_performance_monitoring(self):
        """Initialize performance monitoring"""
        try:
            self.performance_monitor = PerformanceMonitor()
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Performance monitoring initialization failed: {e}")
            self.performance_monitor = None
    
    def _init_openai_client(self):
        """Initialize OpenAI client with better error handling"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.logger.log(
                    LogLevel.WARNING, 
                    "OPENAI_API_KEY environment variable not set, OpenAI functionality will be limited"
                )
                self.openai = None
            else:
                self.openai = AsyncOpenAI(api_key=api_key)
                self.logger.log(LogLevel.INFO, "OpenAI client initialized successfully")
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"OpenAI client initialization failed: {e}")
            self.openai = None
    
    def _init_oversight_system(self):
        """Initialize oversight system"""
        try:
            self.notion_integration = None
            self.slack_integration = None
            # Will be configured during setup
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Oversight system initialization failed: {e}")
            self.notion_integration = None
            self.slack_integration = None
    
    def _init_retry_configuration(self):
        """Initialize retry and circuit breaker configuration"""
        try:
            self.retry_config = RetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_backoff=True,
                jitter=True
            )
            
            self.circuit_breaker_config = CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60.0
            )
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Retry configuration initialization failed: {e}")
            self.retry_config = None
            self.circuit_breaker_config = None
    
    def setup_tools(self):
        """Define the universal message router tools"""
        # Your existing tool setup code goes here
        # This is just a placeholder - replace with actual tool setup
        @self.server.tool("send_message")
        async def send_message(sender: str, recipient: str, message: str, 
                              session_id: Optional[str] = None,
                              context: Optional[Dict[str, Any]] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> str:
            """
            Universal Message Router with Identity Awareness and Strategic Enhancements.
            
            Args:
                message: The message content to send
                sender: Identity sending the message (sonny, amy, marcus, ben, aziz)
                recipient: Identity receiving the message (sonny, amy, marcus, ben, aziz)
                session_id: Optional session ID for conversation continuity
                context: Optional context for session preservation (strategic enhancement)
                metadata: Optional metadata for audit trail (strategic enhancement)
                
            Returns:
                Response from recipient identity or status confirmation
            """
            # Placeholder implementation
            return f"Message from {sender} to {recipient} sent successfully"

    async def run(self):
        """Run the universal message router"""
        await self.server.run()

# Main entry point
if __name__ == "__main__":
    # Create and run the universal message router
    router = UniversalMessageRouter()
    asyncio.run(router.run())
