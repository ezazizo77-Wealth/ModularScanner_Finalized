#!/usr/bin/env python3
"""
Google Services MCP Server for AI Triad Collaboration
Enhanced with robust environment variable loading
"""

# Load environment variables before any other imports
import load_env_variables

# Import system modules
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import Google API components
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import pickle
except ImportError as e:
    print(f"Error importing Google API modules: {e}")
    print("Please install required packages: pip install google-api-python-client google-auth google-auth-oauthlib")
    sys.exit(1)

# Import MCP components
try:
    from mcp.server import FastMCP
except ImportError as e:
    print(f"Error importing MCP server: {e}")
    print("Please install required MCP packages")
    sys.exit(1)

# Import existing infrastructure with error handling
try:
    from error_handler import ErrorHandler, StructuredLogger
    from performance_monitor import PerformanceMonitor, performance_monitor
except ImportError as e:
    print(f"Warning: Could not import some infrastructure components: {e}")
    # Fallback logger
    class SimpleLogger:
        def log(self, level, message, **kwargs):
            print(f"[{level}] {message}")
    
    class SimpleErrorHandler:
        def __init__(self):
            pass
    
    class SimplePerformanceMonitor:
        def __init__(self):
            pass
    
    StructuredLogger = lambda name, log_file: SimpleLogger()
    ErrorHandler = lambda logger: SimpleErrorHandler()
    PerformanceMonitor = SimplePerformanceMonitor
    performance_monitor = lambda name: lambda func: func

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
        
        # OAuth configuration with better error handling
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
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
        # Print environment status at initialization
        print("Environment variables at initialization:")
        for key in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "OPENAI_API_KEY"]:
            print(f"  {key}: {'Set' if os.getenv(key) else 'Not set'}")
        
        self.server = FastMCP("google-mcp-server")
        
        # Set up logging
        import os
        project_dir = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(project_dir, "google_mcp_server.log")
        self.logger = StructuredLogger("google-mcp-server", log_file)
        self.error_handler = ErrorHandler(self.logger)
        self.performance_monitor = PerformanceMonitor()
        
        # Initialize Google integration
        self.identity_manager = GoogleIdentityManager()
        self.service_factory = GoogleServiceFactory(self.identity_manager, self.logger)
        
        # Set up MCP tools
        self.setup_tools()
        
        # Log successful initialization
        self.logger.log("INFO", "Google MCP Server initialized")
        print("Google MCP Server initialized successfully")
    
    def setup_tools(self):
        """Set up all Google MCP tools"""
        self.setup_auth_tools()
        self.setup_sheets_tools()
        self.setup_apps_script_tools()
        self.setup_drive_tools()
        self.setup_test_tools()
    
    def setup_auth_tools(self):
        """Set up authentication tools"""
        @self.server.tool("get_google_auth_url")
        async def get_google_auth_url() -> Dict[str, Any]:
            """
            Get Google OAuth authorization URL for authentication.
            
            Returns:
                JSON with authorization URL and instructions
            """
            try:
                auth_url = self.identity_manager.get_authorization_url()
                return {
                    "status": "success",
                    "auth_url": auth_url,
                    "instructions": "Visit this URL and authorize the application, then copy the authorization code."
                }
            except Exception as e:
                error_msg = str(e)
                self.logger.log("ERROR", f"Error getting auth URL: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.server.tool("exchange_google_auth_code")
        async def exchange_google_auth_code(authorization_code: str) -> Dict[str, Any]:
            """
            Exchange authorization code for access token.
            
            Args:
                authorization_code: Authorization code from Google OAuth flow
                
            Returns:
                JSON with authentication status
            """
            try:
                credentials = self.identity_manager.exchange_code_for_token(authorization_code)
                return {
                    "status": "success",
                    "message": "Authentication successful",
                    "email": credentials.id_token.get('email') if credentials.id_token else "unknown",
                    "expires_in": credentials.expires_in if hasattr(credentials, 'expires_in') else "unknown",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                self.logger.log("ERROR", f"Error exchanging auth code: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.server.tool("check_google_auth_status")
        async def check_google_auth_status() -> Dict[str, Any]:
            """
            Check current Google authentication status.
            
            Returns:
                JSON with authentication status and service availability
            """
            credentials = self.identity_manager.get_valid_credentials()
            
            # Test each service
            drive_service = self.service_factory.create_drive_service()
            sheets_service = self.service_factory.create_sheets_service()
            script_service = self.service_factory.create_script_service()
            
            # Check the keys in our .env file
            env_status = {
                "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID") is not None,
                "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET") is not None
            }
            
            return {
                "status": "success",
                "authenticated": credentials is not None,
                "token_file_exists": os.path.exists(self.identity_manager.token_file),
                "token_file_size": os.path.getsize(self.identity_manager.token_file) if os.path.exists(self.identity_manager.token_file) else 0,
                "env_variables": env_status,
                "services": {
                    "drive": drive_service is not None,
                    "sheets": sheets_service is not None,
                    "script": script_service is not None
                },
                "timestamp": datetime.now().isoformat()
            }

    def setup_sheets_tools(self):
        """Set up Google Sheets tools"""
        @self.server.tool("create_google_sheet")
        async def create_google_sheet(title: str, identity: str = "sonny", folder_id: Optional[str] = None) -> Dict[str, Any]:
            """
            Create a new Google Sheet.
            
            Args:
                title: Title of the new Google Sheet
                identity: AI identity requesting the action (sonny, amy, marcus, ben)
                folder_id: Optional Google Drive folder ID to create sheet in
                
            Returns:
                JSON with sheet creation information
            """
            try:
                # Get the identity
                identity_info = self.identity_manager.get_identity(identity.lower())
                if not identity_info:
                    return {
                        "status": "error",
                        "message": f"Invalid identity: {identity}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Get the Drive service
                drive_service = self.service_factory.create_drive_service()
                if not drive_service:
                    return {
                        "status": "error",
                        "message": "Failed to create Drive service",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Create a new Google Sheet
                file_metadata = {
                    'name': title,
                    'mimeType': 'application/vnd.google-apps.spreadsheet'
                }
                
                # Add to folder if specified
                if folder_id:
                    file_metadata['parents'] = [folder_id]
                
                file = drive_service.files().create(
                    body=file_metadata,
                    fields='id, name, webViewLink'
                ).execute()
                
                return {
                    "status": "success",
                    "sheet_id": file.get('id'),
                    "sheet_name": file.get('name'),
                    "sheet_url": file.get('webViewLink'),
                    "created_by": identity_info.get('name'),
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                self.logger.log("ERROR", f"Error creating Google Sheet: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.server.tool("read_google_sheet")
        async def read_google_sheet(sheet_id: str, range: str = "A1:Z1000", identity: str = "sonny") -> Dict[str, Any]:
            """
            Read data from a Google Sheet.
            
            Args:
                sheet_id: Google Sheets spreadsheet ID
                range: Range to read (e.g., "A1:Z1000", "Sheet1!A1:C10")
                identity: AI identity requesting the action
                
            Returns:
                JSON with sheet data
            """
            try:
                # Get the identity
                identity_info = self.identity_manager.get_identity(identity.lower())
                if not identity_info:
                    return {
                        "status": "error",
                        "message": f"Invalid identity: {identity}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Get the Sheets service
                sheets_service = self.service_factory.create_sheets_service()
                if not sheets_service:
                    return {
                        "status": "error",
                        "message": "Failed to create Sheets service",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Read the sheet
                result = sheets_service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range=range
                ).execute()
                
                values = result.get('values', [])
                
                return {
                    "status": "success",
                    "sheet_id": sheet_id,
                    "range": range,
                    "values": values,
                    "row_count": len(values),
                    "col_count": len(values[0]) if values else 0,
                    "requested_by": identity_info.get('name'),
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                self.logger.log("ERROR", f"Error reading Google Sheet: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.server.tool("update_google_sheet")
        async def update_google_sheet(sheet_id: str, range: str, values: List[List[str]], identity: str = "sonny") -> Dict[str, Any]:
            """
            Update data in a Google Sheet.
            
            Args:
                sheet_id: Google Sheets spreadsheet ID
                range: Range to update (e.g., "A1:C3")
                values: 2D array of values to write
                identity: AI identity requesting the action
                
            Returns:
                JSON with update information
            """
            try:
                # Get the identity
                identity_info = self.identity_manager.get_identity(identity.lower())
                if not identity_info:
                    return {
                        "status": "error",
                        "message": f"Invalid identity: {identity}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Get the Sheets service
                sheets_service = self.service_factory.create_sheets_service()
                if not sheets_service:
                    return {
                        "status": "error",
                        "message": "Failed to create Sheets service",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Update the sheet
                body = {
                    'values': values
                }
                result = sheets_service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=range,
                    valueInputOption='RAW',
                    body=body
                ).execute()
                
                return {
                    "status": "success",
                    "sheet_id": sheet_id,
                    "range": range,
                    "updated_cells": result.get('updatedCells'),
                    "updated_rows": result.get('updatedRows'),
                    "updated_columns": result.get('updatedColumns'),
                    "updated_by": identity_info.get('name'),
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                self.logger.log("ERROR", f"Error updating Google Sheet: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.server.tool("append_to_google_sheet")
        async def append_to_google_sheet(sheet_id: str, range: str, values: List[List[str]], identity: str = "sonny") -> Dict[str, Any]:
            """
            Append data to a Google Sheet.
            
            Args:
                sheet_id: Google Sheets spreadsheet ID
                range: Range to append to (e.g., "A1:C")
                values: 2D array of values to append
                identity: AI identity requesting the action
                
            Returns:
                JSON with append information
            """
            try:
                # Get the identity
                identity_info = self.identity_manager.get_identity(identity.lower())
                if not identity_info:
                    return {
                        "status": "error",
                        "message": f"Invalid identity: {identity}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Get the Sheets service
                sheets_service = self.service_factory.create_sheets_service()
                if not sheets_service:
                    return {
                        "status": "error",
                        "message": "Failed to create Sheets service",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Append to the sheet
                body = {
                    'values': values
                }
                result = sheets_service.spreadsheets().values().append(
                    spreadsheetId=sheet_id,
                    range=range,
                    valueInputOption='RAW',
                    insertDataOption='INSERT_ROWS',
                    body=body
                ).execute()
                
                return {
                    "status": "success",
                    "sheet_id": sheet_id,
                    "range": range,
                    "updates": {
                        "updated_range": result.get('updates', {}).get('updatedRange'),
                        "updated_cells": result.get('updates', {}).get('updatedCells'),
                        "updated_rows": result.get('updates', {}).get('updatedRows'),
                        "updated_columns": result.get('updates', {}).get('updatedColumns')
                    },
                    "appended_by": identity_info.get('name'),
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                self.logger.log("ERROR", f"Error appending to Google Sheet: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }

    def setup_apps_script_tools(self):
        """Set up Google Apps Script tools"""
        @self.server.tool("create_apps_script")
        async def create_apps_script(title: str, code: str, identity: str = "sonny") -> Dict[str, Any]:
            """
            Create a new Google Apps Script project.
            
            Args:
                title: Title of the new Apps Script project
                code: JavaScript code for the Apps Script
                identity: AI identity requesting the action
                
            Returns:
                JSON with Apps Script creation information
            """
            try:
                # Get the identity
                identity_info = self.identity_manager.get_identity(identity.lower())
                if not identity_info:
                    return {
                        "status": "error",
                        "message": f"Invalid identity: {identity}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Get the Script service
                script_service = self.service_factory.create_script_service()
                if not script_service:
                    return {
                        "status": "error",
                        "message": "Failed to create Script service",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Create a new script project
                request = {
                    'title': title,
                    'files': [
                        {
                            'name': 'Code.gs',
                            'type': 'SERVER_JS',
                            'source': code
                        }
                    ]
                }
                
                response = script_service.projects().create(body=request).execute()
                
                return {
                    "status": "success",
                    "script_id": response.get('scriptId'),
                    "script_title": title,
                    "created_by": identity_info.get('name'),
                    "script_url": f"https://script.google.com/d/{response.get('scriptId')}/edit",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                self.logger.log("ERROR", f"Error creating Apps Script: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }

    def setup_drive_tools(self):
        """Set up Google Drive tools"""
        @self.server.tool("list_drive_files")
        async def list_drive_files(folder_id: Optional[str] = None, identity: str = "sonny") -> Dict[str, Any]:
            """
            List files in Google Drive.
            
            Args:
                folder_id: Optional Google Drive folder ID to list files from
                identity: AI identity requesting the action
                
            Returns:
                JSON with list of files
            """
            try:
                # Get the identity
                identity_info = self.identity_manager.get_identity(identity.lower())
                if not identity_info:
                    return {
                        "status": "error",
                        "message": f"Invalid identity: {identity}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Get the Drive service
                drive_service = self.service_factory.create_drive_service()
                if not drive_service:
                    return {
                        "status": "error",
                        "message": "Failed to create Drive service",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # List files
                query = f"'{folder_id}' in parents" if folder_id else None
                files = []
                page_token = None
                
                while True:
                    response = drive_service.files().list(
                        q=query,
                        spaces='drive',
                        fields='nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, webViewLink, iconLink, size)',
                        pageToken=page_token
                    ).execute()
                    
                    files.extend(response.get('files', []))
                    page_token = response.get('nextPageToken')
                    
                    if not page_token:
                        break
                
                # Format the files
                formatted_files = []
                for file in files:
                    formatted_files.append({
                        "id": file.get('id'),
                        "name": file.get('name'),
                        "type": file.get('mimeType'),
                        "created_time": file.get('createdTime'),
                        "modified_time": file.get('modifiedTime'),
                        "url": file.get('webViewLink'),
                        "icon": file.get('iconLink'),
                        "size": file.get('size')
                    })
                
                return {
                    "status": "success",
                    "files": formatted_files,
                    "file_count": len(formatted_files),
                    "folder_id": folder_id,
                    "requested_by": identity_info.get('name'),
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                self.logger.log("ERROR", f"Error listing Drive files: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.server.tool("read_drive_file")
        async def read_drive_file(file_id: str, identity: str = "sonny") -> Dict[str, Any]:
            """
            Read file from Google Drive.
            
            Args:
                file_id: Google Drive file ID
                identity: AI identity requesting the action
                
            Returns:
                JSON with file content
            """
            try:
                # Get the identity
                identity_info = self.identity_manager.get_identity(identity.lower())
                if not identity_info:
                    return {
                        "status": "error",
                        "message": f"Invalid identity: {identity}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Get the Drive service
                drive_service = self.service_factory.create_drive_service()
                if not drive_service:
                    return {
                        "status": "error",
                        "message": "Failed to create Drive service",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Get file metadata
                file = drive_service.files().get(
                    fileId=file_id,
                    fields='id, name, mimeType, size, webViewLink'
                ).execute()
                
                # For Google Docs, Sheets, and Slides, export the content
                mime_type = file.get('mimeType')
                content = None
                export_mime_type = None
                
                if mime_type == 'application/vnd.google-apps.document':
                    export_mime_type = 'text/plain'
                elif mime_type == 'application/vnd.google-apps.spreadsheet':
                    export_mime_type = 'text/csv'
                elif mime_type == 'application/vnd.google-apps.presentation':
                    export_mime_type = 'text/plain'
                
                if export_mime_type:
                    content = drive_service.files().export(
                        fileId=file_id,
                        mimeType=export_mime_type
                    ).execute()
                    
                    # Convert binary content to string
                    content = content.decode('utf-8') if isinstance(content, bytes) else content
                else:
                    # For regular files, download the content
                    request = drive_service.files().get_media(fileId=file_id)
                    content = request.execute()
                    
                    # Try to decode if it's text
                    try:
                        content = content.decode('utf-8') if isinstance(content, bytes) else content
                    except UnicodeDecodeError:
                        # It's binary data, return info but not content
                        content = f"Binary file: {file.get('name')} ({file.get('size')} bytes)"
                
                return {
                    "status": "success",
                    "file_id": file.get('id'),
                    "file_name": file.get('name'),
                    "file_type": file.get('mimeType'),
                    "file_url": file.get('webViewLink'),
                    "content": content,
                    "requested_by": identity_info.get('name'),
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                self.logger.log("ERROR", f"Error reading Drive file: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }

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
                    except:
                        pass
                    
                    try:
                        sheets_service = self.service_factory.create_sheets_service()
                    except:
                        pass
                    
                    try:
                        script_service = self.service_factory.create_script_service()
                    except:
                        pass
                
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
                    "credentials": {
                        "valid": credentials.valid if credentials else False,
                        "expired": credentials.expired if credentials else None,
                        "has_refresh_token": credentials.refresh_token is not None if credentials else False
                    } if credentials else None,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                error_msg = str(e)
                self.logger.log("ERROR", f"Error testing Google connection: {error_msg}")
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
