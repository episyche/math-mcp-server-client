from __future__ import annotations

import io
import logging
import os
import sys
import asyncio
import base64
from typing import List, Dict, Any, Optional
from email.message import EmailMessage
from email.header import decode_header
from base64 import urlsafe_b64decode
from email import message_from_bytes
import webbrowser

import requests
from dotenv import load_dotenv, set_key
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import database utilities
from db_utils import get_user_credentials, update_tokens_in_db, test_database_connection

mcp = FastMCP("GmailServer")

# Load environment variables at startup
load_dotenv()

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

logger = logging.getLogger("GmailServer")

# Global Gmail service instance
gmail_service = None

def sanitize_text(text: str) -> str:
    """Sanitize text to avoid encoding issues in MCP responses."""
    if not text:
        return ""
    try:
        # Convert to string and handle encoding gracefully
        sanitized = str(text)
        # Only allow basic ASCII characters (32-126) plus newlines and tabs
        sanitized = ''.join(char for char in sanitized if 32 <= ord(char) <= 126 or char in '\n\r\t')
        
        # Additional safety: replace any remaining problematic characters
        sanitized = sanitized.replace('\x00', '')  # Remove null bytes
        sanitized = sanitized.replace('\ufffd', '?')  # Replace replacement characters
        
        # Ensure the result is a valid string
        sanitized = sanitized.encode('ascii', errors='replace').decode('ascii')
        
        return sanitized
    except Exception:
        # Fallback: return a safe string
        safe_text = str(text)[:100] if len(str(text)) > 100 else str(text)
        return safe_text.encode('ascii', errors='replace').decode('ascii')

def safe_mcp_response(text: str) -> CallToolResult:
    """Create a safe MCP response that won't cause encoding issues."""
    try:
        # Convert to string first
        text_str = str(text) if text else ""
        
        # Completely strip all non-ASCII characters
        safe_text = ""
        for char in text_str:
            if 32 <= ord(char) <= 126 or char in '\n\r\t':
                safe_text += char
            else:
                safe_text += "?"  # Replace problematic characters with ?
        
        # Final safety: encode/decode to ensure complete compatibility
        safe_text = safe_text.encode('ascii', errors='replace').decode('ascii')
        
        # Remove any remaining problematic characters
        safe_text = ''.join(char for char in safe_text if ord(char) < 128)
        
        # Ensure we have a valid response
        if not safe_text.strip():
            safe_text = "No data available (encoding issues)"
        
        logger.info(f"Created safe MCP response: {len(safe_text)} characters")
        
        return CallToolResult(
            content=[TextContent(type="text", text=safe_text)]
        )
    except Exception as e:
        # Ultimate fallback: return a simple error message
        logger.error(f"Error creating safe MCP response: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text="Error processing response")]
        )

def decode_mime_header(header: str) -> str:
    """Helper function to decode encoded email headers"""
    try:
        decoded_parts = decode_header(header)
        decoded_string = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                # Decode bytes to string using the specified encoding
                decoded_string += part.decode(encoding or "utf-8")
            else:
                # Already a string
                decoded_string += part
        return decoded_string
    except Exception as e:
        logger.error(f"Error decoding MIME header: {e}")
        return str(header)

class GmailService:
    def __init__(
        self,
        user_id: str,
        scopes: list[str] = ["https://www.googleapis.com/auth/gmail.modify"],
    ):
        logger.info(f"Initializing GmailService for user: {user_id}")
        self.user_id = user_id
        self.scopes = scopes
        self._token = None
        self._service = None
        self._user_email = None
        self._credentials = None
        logger.info("Gmail service configuration ready (lazy initialization - no authentication yet)")

    def _ensure_authenticated(self):
        """Ensure the service is authenticated, initialize if needed"""
        if self._service is None:
            try:
                logger.info("Initializing Gmail authentication...")
                self._credentials = self._get_credentials_from_db()
                self._token = self._get_token()
                self._service = self._get_service()
                self._user_email = self._get_user_email()
                logger.info(f"Gmail service initialized for user: {self._user_email}")
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                # Don't raise here, just log the error
                # The tools will handle this gracefully
                pass

    def _get_credentials_from_db(self) -> Dict[str, Any]:
        """Get Gmail credentials from database"""
        try:
            # Get Gmail credentials from database
            credentials = get_user_credentials(self.user_id, "gmail")
            if not credentials:
                raise ValueError("No Gmail credentials found in database for this user")
            
            logger.info("Gmail credentials retrieved from database")
            return credentials
        except Exception as e:
            logger.error(f"Error getting Gmail credentials from database: {e}")
            raise ValueError(f"Failed to get Gmail credentials: {e}")

    @property
    def service(self):
        """Get the Gmail service, initializing if needed"""
        self._ensure_authenticated()
        if self._service is None:
            raise ValueError("Gmail service not authenticated. Please check your credentials in the database.")
        return self._service

    @property
    def user_email(self):
        """Get the user email, initializing if needed"""
        self._ensure_authenticated()
        if self._user_email is None:
            raise ValueError("Gmail service not authenticated. Please check your credentials in the database.")
        return self._user_email

    def _get_token(self) -> Credentials:
        """Get or refresh Google API token from database credentials"""
        try:
            # Create credentials object from database data
            token_data = {
                "token": self._credentials.get("gmail_access_token"),
                "refresh_token": self._credentials.get("gmail_refresh_token"),
                "client_id": self._credentials.get("client_id"),
                "client_secret": self._credentials.get("client_secret"),
                "scopes": self.scopes
            }
            
            # Check if we have required credentials
            if not token_data["client_id"] or not token_data["client_secret"]:
                raise ValueError("Missing OAuth client credentials in database")
            
            if not token_data["token"]:
                raise ValueError("No Gmail access token found in database")
            
            # Create credentials object
            token = Credentials.from_authorized_user_info(token_data, self.scopes)
            
            # If token is invalid or expired, try to refresh
            if not token.valid:
                if token.expired and token.refresh_token:
                    logger.info("Refreshing expired token")
                    token.refresh(Request())
                    
                    # Update the token in database
                    update_tokens_in_db(
                        self.user_id, 
                        "gmail", 
                        token.token, 
                        token.refresh_token
                    )
                    logger.info("Token refreshed and updated in database")
                else:
                    logger.error("Token is invalid and cannot be refreshed")
                    raise ValueError("Gmail token is invalid and cannot be refreshed. Please re-authenticate.")
            
            return token
            
        except Exception as e:
            logger.error(f"Error getting token: {e}")
            if "invalid_scope" in str(e).lower():
                logger.error("❌ Invalid OAuth scope. Please check your OAuth credentials in database.")
            elif "invalid_client" in str(e).lower():
                logger.error("❌ Invalid client credentials. Please check your OAuth credentials in database.")
            else:
                logger.error(f"❌ Authentication error: {e}")
            raise ValueError(f"Failed to authenticate with Gmail API: {e}")

    def _get_service(self) -> Any:
        """Initialize Gmail API service"""
        try:
            service = build("gmail", "v1", credentials=self._token)
            return service
        except HttpError as error:
            logger.error(f"An error occurred building Gmail service: {error}")
            raise ValueError(f"An error occurred: {error}")

    def _get_user_email(self) -> str:
        """Get user email address"""
        profile = self._service.users().getProfile(userId="me").execute()
        user_email = profile.get("emailAddress", "")
        return user_email

    async def send_email(
        self,
        recipient_id: str,
        subject: str,
        message: str,
    ) -> dict:
        """Creates and sends an email message"""
        try:
            message_obj = EmailMessage()
            message_obj.set_content(message)

            message_obj["To"] = recipient_id
            message_obj["From"] = self.user_email
            message_obj["Subject"] = subject

            encoded_message = base64.urlsafe_b64encode(message_obj.as_bytes()).decode()
            create_message = {"raw": encoded_message}

            send_message = await asyncio.to_thread(
                self.service.users().messages().send(userId="me", body=create_message).execute
            )
            logger.info(f"Message sent: {send_message['id']}")
            return {"status": "success", "message_id": send_message["id"]}
        except HttpError as error:
            return {"status": "error", "error_message": str(error)}

    async def open_email(self, email_id: str) -> str:
        """Opens email in browser given ID."""
        try:
            url = f"https://mail.google.com/#all/{email_id}"
            webbrowser.open(url, new=0, autoraise=True)
            return "Email opened in browser successfully."
        except Exception as error:
            return f"An error occurred: {str(error)}"

    async def get_unread_emails(self) -> list[dict[str, str]] | str:
        """Retrieves unread messages from mailbox."""
        try:
            user_id = "me"
            query = "in:inbox is:unread category:primary"

            response = self.service.users().messages().list(userId=user_id, q=query).execute()
            messages = []
            if "messages" in response:
                messages.extend(response["messages"])

            while "nextPageToken" in response:
                page_token = response["nextPageToken"]
                response = self.service.users().messages().list(userId=user_id, q=query, pageToken=page_token).execute()
                messages.extend(response["messages"])
            return messages

        except HttpError as error:
            return f"An HttpError occurred: {str(error)}"

    async def read_email(self, email_id: str) -> dict[str, str] | str:
        """Retrieves email contents including to, from, subject, and contents."""
        try:
            msg = self.service.users().messages().get(userId="me", id=email_id, format="raw").execute()
            email_metadata = {}

            # Decode the base64URL encoded raw content
            raw_data = msg["raw"]
            decoded_data = urlsafe_b64decode(raw_data)

            # Parse the RFC 2822 email
            mime_message = message_from_bytes(decoded_data)

            # Extract the email body
            body = None
            if mime_message.is_multipart():
                for part in mime_message.walk():
                    # Extract the text/plain part
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                # For non-multipart messages
                body = mime_message.get_payload(decode=True).decode()
            email_metadata["content"] = body

            # Extract metadata
            email_metadata["subject"] = decode_mime_header(mime_message.get("subject", ""))
            email_metadata["from"] = mime_message.get("from", "")
            email_metadata["to"] = mime_message.get("to", "")
            email_metadata["date"] = mime_message.get("date", "")

            logger.info(f"Email read: {email_id}")

            # We want to mark email as read once we read it
            await self.mark_email_as_read(email_id)

            return email_metadata
        except HttpError as error:
            return f"An HttpError occurred: {str(error)}"

    async def trash_email(self, email_id: str) -> str:
        """Moves email to trash given ID."""
        try:
            self.service.users().messages().trash(userId="me", id=email_id).execute()
            logger.info(f"Email moved to trash: {email_id}")
            return "Email moved to trash successfully."
        except HttpError as error:
            return f"An HttpError occurred: {str(error)}"

    async def mark_email_as_read(self, email_id: str) -> str:
        """Marks email as read given ID."""
        try:
            self.service.users().messages().modify(
                userId="me", id=email_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            logger.info(f"Email marked as read: {email_id}")
            return "Email marked as read."
        except HttpError as error:
            return f"An HttpError occurred: {str(error)}"

def initialize_gmail_service(user_id: str):
    """Initialize Gmail service with credentials from database"""
    global gmail_service
    
    # Test database connection first
    if not test_database_connection():
        logger.error("❌ Database connection failed")
        return False
    
    try:
        # Create the service object without trying to authenticate
        gmail_service = GmailService(user_id)
        logger.info("✅ Gmail service configuration ready (authentication will happen on first use)")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gmail service: {e}")
        return False

def ensure_gmail_service_initialized(user_id: str):
    """Ensure Gmail service is initialized for the given user"""
    global gmail_service
    
    if gmail_service is None or gmail_service.user_id != user_id:
        return initialize_gmail_service(user_id)
    return True

# ---------------------------
# Gmail Tools
# ---------------------------

@mcp.tool()
def send_email(recipient_id: str, subject: str, message: str, user_id: str = None) -> CallToolResult:
    """Sends email to recipient. Do not use if user only asked to draft email."""
    try:
        # Initialize service if user_id provided
        if user_id and not ensure_gmail_service_initialized(user_id):
            return safe_mcp_response("❌ Failed to initialize Gmail service. Please check your credentials.")
        
        if not gmail_service:
            return safe_mcp_response("❌ Gmail service not initialized. Please check your credentials.")
        
        # Extract subject and message content
        email_lines = message.split("\n")
        if email_lines[0].startswith("Subject:"):
            subject = email_lines[0][8:].strip()
            message_content = "\n".join(email_lines[1:]).strip()
        else:
            message_content = message

        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            send_response = loop.run_until_complete(
                gmail_service.send_email(recipient_id, subject, message_content)
            )
        finally:
            loop.close()

        if send_response["status"] == "success":
            response_text = f"✅ Email sent successfully. Message ID: {send_response['message_id']}"
        else:
            response_text = f"❌ Failed to send email: {send_response['error_message']}"
        
        return safe_mcp_response(response_text)
    except ValueError as e:
        if "not authenticated" in str(e):
            return safe_mcp_response("❌ Gmail authentication failed. Please check your credentials in the database.")
        elif "No Gmail credentials found" in str(e):
            return safe_mcp_response("❌ No Gmail credentials found in database. Please set up your Gmail integration.")
        elif "Token is invalid" in str(e):
            return safe_mcp_response("❌ Gmail token is invalid. Please re-authenticate your Gmail account.")
        else:
            return safe_mcp_response(f"❌ Authentication error: {str(e)}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return safe_mcp_response(f"❌ Error sending email: {str(e)}")

@mcp.tool()
def get_unread_emails() -> CallToolResult:
    """Retrieve unread emails"""
    try:
        if not gmail_service:
            return safe_mcp_response("❌ Gmail service not initialized. Please check your credentials.")
        
        try:
            # Run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                unread_emails = loop.run_until_complete(gmail_service.get_unread_emails())
            finally:
                loop.close()

            if isinstance(unread_emails, str):
                return safe_mcp_response(f"❌ Error retrieving emails: {unread_emails}")
            
            # Format the response
            if not unread_emails:
                return safe_mcp_response("📧 No unread emails found.")
            
            email_list = []
            for email in unread_emails[:10]:  # Limit to first 10 emails
                email_list.append(f"Email ID: {email.get('id', 'N/A')}")
            
            response_text = f"📧 Found {len(unread_emails)} unread emails:\n" + "\n".join(email_list)
            if len(unread_emails) > 10:
                response_text += f"\n... and {len(unread_emails) - 10} more emails"
            
            return safe_mcp_response(response_text)
            
        except ValueError as e:
            if "not authenticated" in str(e):
                return safe_mcp_response("❌ Gmail authentication failed. Please check your credentials in the database.")
            elif "No Gmail credentials found" in str(e):
                return safe_mcp_response("❌ No Gmail credentials found in database. Please set up your Gmail integration.")
            elif "Token is invalid" in str(e):
                return safe_mcp_response("❌ Gmail token is invalid. Please re-authenticate your Gmail account.")
            else:
                return safe_mcp_response(f"❌ Authentication error: {str(e)}")
        except Exception as e:
            return safe_mcp_response(f"❌ Error retrieving emails: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error getting unread emails: {e}")
        return safe_mcp_response(f"❌ Error retrieving emails: {str(e)}")

@mcp.tool()
def read_email(email_id: str) -> CallToolResult:
    """Retrieves given email content"""
    try:
        if not gmail_service:
            return safe_mcp_response("❌ Gmail service not initialized. Please check your credentials.")
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            retrieved_email = loop.run_until_complete(gmail_service.read_email(email_id))
        finally:
            loop.close()

        if isinstance(retrieved_email, str):
            return safe_mcp_response(f"❌ Error reading email: {retrieved_email}")
        
        # Format the response
        response_text = f"""📧 Email Details:
From: {retrieved_email.get('from', 'N/A')}
To: {retrieved_email.get('to', 'N/A')}
Subject: {retrieved_email.get('subject', 'N/A')}
Date: {retrieved_email.get('date', 'N/A')}

Content:
{retrieved_email.get('content', 'No content available')}"""
        
        return safe_mcp_response(response_text)
    except Exception as e:
        logger.error(f"Error reading email: {e}")
        return safe_mcp_response(f"❌ Error reading email: {str(e)}")

@mcp.tool()
def trash_email(email_id: str) -> CallToolResult:
    """Moves email to trash. Confirm before moving email to trash."""
    try:
        if not gmail_service:
            return safe_mcp_response("❌ Gmail service not initialized. Please check your credentials.")
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            msg = loop.run_until_complete(gmail_service.trash_email(email_id))
        finally:
            loop.close()

        return safe_mcp_response(msg)
    except Exception as e:
        logger.error(f"Error trashing email: {e}")
        return safe_mcp_response(f"❌ Error moving email to trash: {str(e)}")

@mcp.tool()
def mark_email_as_read(email_id: str) -> CallToolResult:
    """Marks given email as read"""
    try:
        if not gmail_service:
            return safe_mcp_response("❌ Gmail service not initialized. Please check your credentials.")
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            msg = loop.run_until_complete(gmail_service.mark_email_as_read(email_id))
        finally:
            loop.close()

        return safe_mcp_response(msg)
    except Exception as e:
        logger.error(f"Error marking email as read: {e}")
        return safe_mcp_response(f"❌ Error marking email as read: {str(e)}")

@mcp.tool()
def open_email(email_id: str) -> CallToolResult:
    """Open email in browser"""
    try:
        if not gmail_service:
            return safe_mcp_response("❌ Gmail service not initialized. Please check your credentials.")
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            msg = loop.run_until_complete(gmail_service.open_email(email_id))
        finally:
            loop.close()

        return safe_mcp_response(msg)
    except Exception as e:
        logger.error(f"Error opening email: {e}")
        return safe_mcp_response(f"❌ Error opening email: {str(e)}")

# ---------------------------
# Initialize service on startup
# ---------------------------

if __name__ == "__main__":
    logger.info("🚀 Starting Gmail MCP Server...")
    
    # Get user ID from environment variable or command line argument
    user_id = os.getenv("USER_ID")
    if not user_id:
        if len(sys.argv) > 1:
            user_id = sys.argv[1]
        else:
            logger.error("❌ USER_ID not provided. Please set USER_ID environment variable or pass as argument.")
            logger.info("💡 Usage: python gmail_mcp_server.py <user_id>")
            sys.exit(1)
    
    # Initialize Gmail service
    if initialize_gmail_service(user_id):
        logger.info("✅ Gmail MCP Server ready!")
    else:
        logger.warning("⚠️  Gmail service not initialized - tools will return error messages")
        logger.info("💡 Please check your credentials in the database")
    
    # Run the server even if service initialization failed
    mcp.run()
