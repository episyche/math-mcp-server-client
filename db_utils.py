#!/usr/bin/env python3
"""
Common Database Utilities
Centralized database connection and credential retrieval functions
"""

import os
import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager

# Database imports
import psycopg2
from psycopg2.extras import RealDictCursor

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration from .env
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'youtube_creds'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': os.getenv('DB_PORT', '5432')
}

# ---------------------------
# Database Connection
# ---------------------------

@contextmanager
def get_db_connection():
    """Get a PostgreSQL database connection with proper error handling."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise RuntimeError(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

# ---------------------------
# YouTube Credential Functions
# ---------------------------

def get_youtube_minion_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Get YouTube minion credentials for a user from the database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        ym.youtube_access_token,
                        ym.youtube_refresh_token,
                        ym.youtube_channel_id,
                        ym.connection_details,
                        i.client_id,
                        i.client_secret,
                        i.redirect_uri,
                        ma.name as agent_masteragent_name,
                        ym.name as minion_name,
                        ym.capabilities
                    FROM accounts_user u
                    JOIN agent_masteragent ma ON u.id = ma.user_id
                    JOIN agent_youtube_minion ym ON ma.id = ym.master_agent_id
                    LEFT JOIN agent_integration i ON ym.integration_app_id = i.id
                    WHERE u.id = %s AND ym.is_active = true
                    ORDER BY ym.id DESC
                    LIMIT 1
                """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
    except Exception as e:
        logger.error(f"Error getting YouTube minion credentials for user {user_id}: {e}")
        return None

def update_youtube_token_in_db(user_id: str, new_token: str) -> bool:
    """Update YouTube access token in database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE agent_youtube_minion 
                    SET youtube_access_token = %s, updated_at = NOW()
                    WHERE master_agent_id IN (
                        SELECT ma.id FROM agent_masteragent ma 
                        WHERE ma.user_id = %s
                    ) AND is_active = true
                """, (new_token, user_id))
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"Error updating YouTube token in database: {e}")
        return False

def update_youtube_tokens_in_db(user_id: str, access_token: str, refresh_token: str) -> bool:
    """Update both YouTube access token and refresh token in database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE agent_youtube_minion 
                    SET youtube_access_token = %s, youtube_refresh_token = %s, updated_at = NOW()
                    WHERE master_agent_id IN (
                        SELECT ma.id FROM agent_masteragent ma 
                        WHERE ma.user_id = %s
                    ) AND is_active = true
                """, (access_token, refresh_token, user_id))
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"Error updating YouTube tokens in database: {e}")
        return False

# ---------------------------
# X (Twitter) Credential Functions
# ---------------------------

def get_x_minion_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Get X minion credentials for a user from the database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        xm.x_token,
                        xm.x_refresh_token,
                        xm.x_bearer_token,
                        xm.connection_details,
                        i.client_id,
                        i.client_secret,
                        ma.name as agent_masteragent_name,
                        xm.name as minion_name,
                        xm.capabilities
                    FROM accounts_user u
                    JOIN agent_masteragent ma ON u.id = ma.user_id
                    JOIN agent_x_minion xm ON ma.id = xm.master_agent_id
                    LEFT JOIN agent_integration i ON xm.integration_app_id = i.id
                    WHERE u.id = %s AND xm.is_active = true
                    ORDER BY xm.id DESC
                    LIMIT 1
                """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
    except Exception as e:
        logger.error(f"Error getting X minion credentials for user {user_id}: {e}")
        return None

def update_x_tokens_in_db(user_id: str, access_token: str, refresh_token: str) -> bool:
    """Update X access token and refresh token in database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE agent_x_minion 
                    SET x_token = %s, x_refresh_token = %s, updated_at = NOW()
                    WHERE master_agent_id IN (
                        SELECT ma.id FROM agent_masteragent ma 
                        WHERE ma.user_id = %s
                    ) AND is_active = true
                """, (access_token, refresh_token, user_id))
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"Error updating X tokens in database: {e}")
        return False

# ---------------------------
# Generic Credential Functions
# ---------------------------

def get_user_credentials(user_id: str, service: str) -> Optional[Dict[str, Any]]:
    """Get credentials for a specific service and user."""
    if service.lower() == "youtube":
        return get_youtube_minion_credentials(user_id)
    elif service.lower() == "x":
        return get_x_minion_credentials(user_id)
    elif service.lower() == "facebook":
        return get_facebook_minion_credentials(user_id)
    elif service.lower() == "google_ads":
        return get_google_ads_minion_credentials(user_id)
    elif service.lower() == "shopify":
        return get_shopify_minion_credentials(user_id)
    else:
        logger.error(f"Unknown service: {service}")
        return None

def update_tokens_in_db(user_id: str, service: str, access_token: str, refresh_token: str = None) -> bool:
    """Update tokens for a specific service and user."""
    if service.lower() == "youtube":
        if refresh_token:
            return update_youtube_tokens_in_db(user_id, access_token, refresh_token)
        else:
            return update_youtube_token_in_db(user_id, access_token)
    elif service.lower() == "x":
        if refresh_token:
            return update_x_tokens_in_db(user_id, access_token, refresh_token)
        else:
            logger.error("X service requires both access and refresh tokens")
            return False
    elif service.lower() == "facebook":
        return update_facebook_token_in_db(user_id, access_token)
    elif service.lower() == "google_ads":
        if refresh_token:
            return update_google_ads_tokens_in_db(user_id, refresh_token)
        else:
            logger.error("Google Ads service requires refresh token")
            return False
    elif service.lower() == "shopify":
        return update_shopify_token_in_db(user_id, access_token)
    else:
        logger.error(f"Unknown service: {service}")
        return False

# ---------------------------
# Database Health Check
# ---------------------------

def test_database_connection() -> bool:
    """Test database connection."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def get_database_info() -> Dict[str, Any]:
    """Get database connection information."""
    return {
        "host": DB_CONFIG["host"],
        "database": DB_CONFIG["database"],
        "user": DB_CONFIG["user"],
        "port": DB_CONFIG["port"],
        "connected": test_database_connection()
    }

# ---------------------------
# Facebook Credential Functions
# ---------------------------

def get_facebook_minion_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Get Facebook minion credentials for a user from the database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        fm.app_access_token as facebook_access_token,
                        fm.app_id,
                        fm.app_secret,
                        fm.webhook_verification,
                        fm.subscribe_to_events,
                        i.client_id,
                        i.client_secret,
                        ma.name as agent_masteragent_name,
                        fm.name as minion_name,
                        fm.capabilities
                    FROM accounts_user u
                    JOIN agent_masteragent ma ON u.id = ma.user_id
                    JOIN agent_facebook_minion fm ON ma.id = fm.master_agent_id
                    LEFT JOIN agent_integration i ON fm.integration_app_id = i.id
                    WHERE u.id = %s AND fm.is_active = true
                    ORDER BY fm.id DESC
                    LIMIT 1
                """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
    except Exception as e:
        logger.error(f"Error getting Facebook minion credentials for user {user_id}: {e}")
        return None

def update_facebook_token_in_db(user_id: str, new_token: str) -> bool:
    """Update Facebook access token in database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE agent_facebook_minion 
                    SET app_access_token = %s, updated_at = NOW()
                    WHERE master_agent_id IN (
                        SELECT ma.id FROM agent_masteragent ma 
                        WHERE ma.user_id = %s
                    ) AND is_active = true
                """, (new_token, user_id))
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"Error updating Facebook token in database: {e}")
        return False

# ---------------------------
# Shopify Credential Functions
# ---------------------------

def get_shopify_minion_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Get Shopify minion credentials for a user from the database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        sm.shopify_access_token,
                        sm.shopify_store_url as shopify_store_domain,
                        sm.shopify_api_version,
                        sm.connection_details,
                        i.client_id as shopify_client_id,
                        i.client_secret as shopify_client_secret,
                        ma.name as agent_masteragent_name,
                        sm.name as minion_name,
                        sm.capabilities
                    FROM accounts_user u
                    JOIN agent_masteragent ma ON u.id = ma.user_id
                    JOIN agent_shopify_minion sm ON ma.id = sm.master_agent_id
                    LEFT JOIN agent_integration i ON sm.integration_app_id = i.id
                    WHERE u.id = %s AND sm.is_active = true
                    ORDER BY sm.id DESC
                    LIMIT 1
                """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
    except Exception as e:
        logger.error(f"Error getting Shopify minion credentials for user {user_id}: {e}")
        return None

def update_shopify_token_in_db(user_id: str, new_token: str) -> bool:
    """Update Shopify access token in database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE agent_shopify_minion 
                    SET shopify_access_token = %s, updated_at = NOW()
                    WHERE master_agent_id IN (
                        SELECT ma.id FROM agent_masteragent ma 
                        WHERE ma.user_id = %s
                    ) AND is_active = true
                """, (new_token, user_id))
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"Error updating Shopify token in database: {e}")
        return False

# ---------------------------
# Google Ads Credential Functions
# ---------------------------

def get_google_ads_minion_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Get Google Ads minion credentials for a user from the database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        ga.google_ads_developer_token,
                        ga.google_ads_refresh_token,
                        ga.google_ads_login_customer_id,
                        ga.connection_details,
                        i.client_id as google_ads_client_id,
                        i.client_secret as google_ads_client_secret,
                        ma.name as agent_masteragent_name,
                        ga.name as minion_name,
                        ga.capabilities
                    FROM accounts_user u
                    JOIN agent_masteragent ma ON u.id = ma.user_id
                    JOIN agent_googleads_minion ga ON ma.id = ga.master_agent_id
                    LEFT JOIN agent_integration i ON ga.integration_app_id = i.id
                    WHERE u.id = %s AND ga.is_active = true
                    ORDER BY ga.id DESC
                    LIMIT 1
                """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
    except Exception as e:
        logger.error(f"Error getting Google Ads minion credentials for user {user_id}: {e}")
        return None

def update_google_ads_tokens_in_db(user_id: str, refresh_token: str) -> bool:
    """Update Google Ads refresh token in database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE agent_googleads_minion 
                    SET google_ads_refresh_token = %s, updated_at = NOW()
                    WHERE master_agent_id IN (
                        SELECT ma.id FROM agent_masteragent ma 
                        WHERE ma.user_id = %s
                    ) AND is_active = true
                """, (refresh_token, user_id))
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"Error updating Google Ads tokens in database: {e}")
        return False
