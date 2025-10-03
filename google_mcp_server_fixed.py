#!/usr/bin/env python3
"""
Google Services MCP Server for AI Triad Collaboration
With enhanced environment variable loading
"""

# Load environment variables before any other imports
import load_env_variables

# System imports
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

# Google API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

# MCP imports
from mcp.server import FastMCP

# Infrastructure imports
from error_handler import ErrorHandler, StructuredLogger
from performance_monitor import PerformanceMonitor, performance_monitor

# Print environment variable status after loading (for verification)
print("\nEnvironment variables in Google MCP Server after loading:")
for key in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "OPENAI_API_KEY"]:
    print(f"  {key}: {'Set' if os.getenv(key) else 'Not set'}")

class GoogleIdentityManager:
    """Manage Google OAuth authentication for different AI identities"""
    
    def __init__(self):
        # Connect to Aziz's personal Google account
        self.primary_account = "ezazizo77@gmail.com"
        self.identities = {
            "sonny": {"name": "sonny", "email": "ezazizo77@gmail.com"},
            "amy": {"name": "amy", "email": "ezazizo77@gmail.com"},
            "marcus": {"name": "marcus", "email": "ezazizo77@gmail.com"},
            "ben": {"name": "ben", "email": "ezazizo77@gmail.com"}
        }
        
        # OAuth configuration - with better error handling
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        # Verify credentials are available
        if not self.client_id or not self.client_secret:
            print("WARNING: Google OAuth credentials not properly set in environment variables")
            print(f"GOOGLE_CLIENT_ID: {'Set' if self.client_id else 'Not set'}")
            print(f"GOOGLE_CLIENT_SECRET: {'Set' if self.client_secret else 'Not set'}")
        
        self.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        
        # Scopes for Google services
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/script.projects",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Token storage
        self.token_file = "google_tokens.pickle"
        self.credentials = None
    
    def get_identity(self, identity_name: str) -> Dict[str, str]:
        """Get identity information"""
        return self.identities.get(identity_name, {})
    
    def load_credentials(self) -> Optional[Credentials]:
        """Load saved credentials from file"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    self.credentials = pickle.load(token)
                return self.credentials
        except Exception as e:
            print(f"Error loading credentials: {e}")
        return None
    
    def save_credentials(self, credentials: Credentials):
        """Save credentials to file"""
        try:
            with open(self.token_file, 'wb') as token:
                pickle.dump(credentials, token)
            self.credentials = credentials
        except Exception as e:
            print(f"Error saving credentials: {e}")
    
    def get_authorization_url(self) -> str:
        """Get OAuth authorization URL"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured. Please check your .env file.")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        auth_url, _ = flow.authorization_url(prompt='consent')
        return auth_url
    
    def exchange_code_for_token(self, authorization_code: str) -> Credentials:
        """Exchange authorization code for access token"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured. Please check your .env file.")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        flow.fetch_token(code=authorization_code)
        credentials = flow.credentials
        self.save_credentials(credentials)
        return credentials
    
    def get_valid_credentials(self) -> Optional[Credentials]:
        """Get valid credentials, refreshing if necessary"""
        credentials = self.load_credentials()
        
        if not credentials:
            return None
        
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    self.save_credentials(credentials)
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    return None
            else:
                return None
        
        return credentials

# Rest of the Google MCP server code remains the same

class GoogleServiceFactory:
    """Factory for creating Google API service clients"""
    
    def __init__(self, identity_manager: GoogleIdentityManager, logger):
        self.identity_manager = identity_manager
        self.logger = logger
    
    def create_drive_service(self) -> Any:
        """Create a Google Drive service client"""
        credentials = self.identity_manager.get_valid_credentials()
        if not credentials:
            self.logger.log("ERROR", "No valid credentials for Drive service")
            return None
        
        try:
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            self.logger.log("ERROR", f"Error creating Drive service: {e}")
            return None
    
    def create_sheets_service(self) -> Any:
        """Create a Google Sheets service client"""
        credentials = self.identity_manager.get_valid_credentials()
        if not credentials:
            self.logger.log("ERROR", "No valid credentials for Sheets service")
            return None
        
        try:
            return build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            self.logger.log("ERROR", f"Error creating Sheets service: {e}")
            return None
    
    def create_script_service(self) -> Any:
        """Create a Google Apps Script service client"""
        credentials = self.identity_manager.get_valid_credentials()
        if not credentials:
            self.logger.log("ERROR", "No valid credentials for Apps Script service")
            return None
        
        try:
            return build('script', 'v1', credentials=credentials)
        except Exception as e:
            self.logger.log("ERROR", f"Error creating Apps Script service: {e}")
            return None

class GoogleMCPServer:
    """Google MCP Server for AI Triad Collaboration"""
    
    def __init__(self):
        """Initialize the Google MCP Server"""
        # Set up logging
        import os
        project_dir = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(project_dir, "google_mcp_server.log")
        self.logger = StructuredLogger("google-mcp-server", log_file)
        self.error_handler = ErrorHandler(self.logger)
        self.performance_monitor = PerformanceMonitor()
        
        # Create server
        self.server = FastMCP("google-mcp-server")
        
        # Initialize Google integration
        self.identity_manager = GoogleIdentityManager()
        self.service_factory = GoogleServiceFactory(self.identity_manager, self.logger)
        
        # Set up MCP tools
        self.setup_tools()
        
        # Log successful initialization
        self.logger.log("INFO", "Google MCP Server initialized")
    
    def setup_tools(self):
        """Set up all Google MCP tools"""
        self.setup_auth_tools()
        self.setup_sheets_tools()
        self.setup_apps_script_tools()
        self.setup_drive_tools()
        self.setup_test_tools()
    
    def setup_auth_tools(self):
        """Set up authentication tools"""
        # Auth tools implementation stays the same
        pass
    
    def setup_sheets_tools(self):
        """Set up Google Sheets tools"""
        # Sheets tools implementation stays the same
        pass
    
    def setup_apps_script_tools(self):
        """Set up Google Apps Script tools"""
        # Apps Script tools implementation stays the same
        pass
    
    def setup_drive_tools(self):
        """Set up Google Drive tools"""
        # Drive tools implementation stays the same
        pass
    
    def setup_test_tools(self):
        """Set up test tools"""
        @self.server.tool("test_google_connection")
        async def test_google_connection() -> Dict[str, Any]:
            """
            Test Google API connection and authentication.
            
            Returns:
                JSON with connection status
            """
            try:
                # Check credentials
                credentials = self.identity_manager.get_valid_credentials()
                
                # Environment variable status
                env_status = {
                    "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID") is not None,
                    "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET") is not None
                }
                
                # Check services
                drive_service = None
                sheets_service = None
                script_service = None
                
                if credentials:
                    # Try to create services
                    try:
                        drive_service = self.service_factory.create_drive_service()
                    except Exception as e:
                        self.logger.log("ERROR", f"Error creating Drive service: {e}")
                    
                    try:
                        sheets_service = self.service_factory.create_sheets_service()
                    except Exception as e:
                        self.logger.log("ERROR", f"Error creating Sheets service: {e}")
                    
                    try:
                        script_service = self.service_factory.create_script_service()
                    except Exception as e:
                        self.logger.log("ERROR", f"Error creating Script service: {e}")
                
                # Run a test operation if Drive service is available
                drive_test = None
                if drive_service:
                    try:
                        response = drive_service.files().list(pageSize=1).execute()
                        drive_test = {
                            "success": True,
                            "file_count": len(response.get('files', []))
                        }
                    except Exception as e:
                        drive_test = {
                            "success": False,
                            "error": str(e)
                        }
                
                # Get token file info
                token_file = self.identity_manager.token_file
                token_status = {
                    "exists": os.path.exists(token_file),
                    "size": os.path.getsize(token_file) if os.path.exists(token_file) else 0
                }
                
                return {
                    "status": "success",
                    "connection_test": {
                        "authenticated": credentials is not None,
                        "token_status": token_status,
                        "env_variables": env_status,
                        "services": {
                            "drive": drive_service is not None,
                            "sheets": sheets_service is not None,
                            "script": script_service is not None
                        },
                        "drive_test": drive_test
                    },
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                self.logger.log("ERROR", f"Error testing Google connection: {e}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
    
    async def run(self):
        """Run the Google MCP server"""
        await self.server.run()

# Main entry point
if __name__ == "__main__":
    # Create and run the Google MCP server
    print("Starting Google MCP server with enhanced environment variable loading...")
    server = GoogleMCPServer()
    asyncio.run(server.run())
