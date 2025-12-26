"""
Reader for Claude.ai conversations.

Fetches conversations from Claude.ai's internal API using direct HTTP requests.
"""

import logging
import os
from typing import Any, Dict, Iterator, List, Optional

import dlt  # Only used for reading secrets
import requests

logger = logging.getLogger(__name__)

# Claude.ai API base URL
CLAUDE_API_BASE = "https://claude.ai/api/organizations"


class ClaudeReader:
    """
    Reader for Claude.ai conversations.

    Fetches conversations from Claude.ai's internal API.
    Credentials can be provided via parameters, environment variables,
    or dlt secrets file (.dlt/secrets.toml).
    """

    def __init__(
        self,
        org_id: Optional[str] = None,
        session_cookie: Optional[str] = None,
    ):
        """
        Initialize Claude reader.

        Parameters
        ----
        org_id : str, optional
            Organization ID. If None, reads from dlt secrets or env var.
        session_cookie : str, optional
            Session cookie. If None, reads from dlt secrets or env var.
        """
        # Try to get credentials from: parameter > env var > dlt secrets
        self.org_id = org_id or os.getenv("CLAUDE_ORG_ID")
        self.session_cookie = session_cookie or os.getenv("CLAUDE_SESSION_COOKIE")

        # Fall back to dlt secrets if not found in env
        if not self.org_id or not self.session_cookie:
            try:
                secrets = dlt.secrets.get("sources.claude_conversations", {})
                if not self.org_id:
                    self.org_id = secrets.get("org_id")
                if not self.session_cookie:
                    self.session_cookie = secrets.get("session_cookie")
            except Exception:
                pass  # dlt secrets not available or misconfigured

        if not self.org_id:
            raise ValueError(
                "org_id must be provided via parameter, CLAUDE_ORG_ID env var, "
                "or dlt secrets"
            )
        if not self.session_cookie:
            raise ValueError(
                "session_cookie must be provided via parameter, CLAUDE_SESSION_COOKIE "
                "env var, or dlt secrets"
            )

        # Build headers for API requests (mimicking browser)
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": f"sessionKey={self.session_cookie}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    def _fetch_conversation_list(self) -> list:
        """Fetch list of all conversations from Claude.ai API."""
        url = f"{CLAUDE_API_BASE}/{self.org_id}/chat_conversations"

        response = requests.get(url, headers=self._headers)
        response.raise_for_status()

        conversations = response.json()
        if not isinstance(conversations, list):
            logger.warning("Unexpected response format from Claude API")
            return []

        return conversations
    
    def get_conversation_list(self) -> List[Dict[str, Any]]:
        """
        Fetch conversation metadata only (no details).
        
        Returns
        ----
        List[Dict[str, Any]]
            List of conversation metadata objects with uuid, name, updated_at, etc.
        """
        return self._fetch_conversation_list()

    def _fetch_conversation_detail(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full conversation details including messages."""
        url = (
            f"{CLAUDE_API_BASE}/{self.org_id}/chat_conversations/{conv_id}"
            "?tree=True&rendering_mode=messages&render_all_tools=true"
        )

        try:
            response = requests.get(url, headers=self._headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching conversation %s: %s", conv_id, e)
            return None

    def read_all_conversations(self) -> Iterator[Dict[str, Any]]:
        """
        Read all Claude conversations.

        Fetches the conversation list, then fetches full details for each.

        Yields
        ----
        Dict[str, Any]
            Full conversation objects with chat_messages array
        """
        logger.info("Fetching Claude conversation list...")

        try:
            conversations = self._fetch_conversation_list()
            logger.info("Found %d conversations", len(conversations))

            for i, conv_meta in enumerate(conversations, 1):
                conv_id = conv_meta.get("uuid")
                if not conv_id:
                    continue

                # Fetch full conversation details
                full_conv = self._fetch_conversation_detail(conv_id)
                if full_conv:
                    # Merge metadata with full details
                    full_conv.update(conv_meta)
                    yield full_conv
                else:
                    # Fall back to metadata only
                    yield conv_meta

                if i % 10 == 0:
                    logger.info("Fetched %d/%d conversations...", i, len(conversations))

            logger.info("Finished fetching %d conversations", len(conversations))

        except requests.exceptions.RequestException as e:
            logger.error("Error fetching Claude conversations: %s", e)
            raise

    def read_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Read a specific conversation by ID.

        Parameters
        ----
        conversation_id : str
            Conversation UUID

        Returns
        ----
        Dict[str, Any]
            Full conversation object, or None if not found
        """
        return self._fetch_conversation_detail(conversation_id)
