"""
Reader for Claude.ai conversations via dlt.

Uses dlt's state management for incremental sync while fetching data directly
from Claude.ai's internal API.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

import dlt
from dlt.sources.helpers import requests

logger = logging.getLogger(__name__)

# Claude.ai API base URL
CLAUDE_API_BASE = "https://claude.ai/api/organizations"


@dlt.source
def claude_conversations(
    org_id: str = dlt.secrets.value,
    session_cookie: str = dlt.secrets.value,
):
    """
    dlt source for Claude.ai conversations.
    
    Parameters
    ----
    org_id : str
        Claude.ai organization ID (from settings/account URL)
    session_cookie : str
        Session cookie value for authentication
        
    Returns
    ----
    dlt.Source
        dlt source with conversation resources
    """
    
    @dlt.resource(
        write_disposition="merge",
        primary_key="uuid",
        name="conversations_list"
    )
    def conversations_list(
        updated_at=dlt.sources.incremental(
            "updated_at",
            initial_value="2020-01-01T00:00:00Z"
        )
    ):
        """
        Fetch list of conversations, filtered by updated_at.
        
        Parameters
        ----
        updated_at : dlt.sources.incremental
            Incremental state for updated_at field
            
        Yields
        ----
        Dict[str, Any]
            Conversation metadata objects
        """
        url = f"{CLAUDE_API_BASE}/{org_id}/chat_conversations"
        
        headers = {
            "Accept": "application/json",
            "Cookie": f"sessionKey={session_cookie}",
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            conversations = response.json()
            
            if not isinstance(conversations, list):
                logger.warning("Unexpected response format from Claude API")
                return
            
            # Filter conversations by updated_at
            last_value = updated_at.last_value
            if last_value:
                # Parse last_value (ISO format string)
                try:
                    last_dt = datetime.fromisoformat(last_value.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    logger.warning("Could not parse last_value: %s", last_value)
                    last_dt = None
            else:
                last_dt = None
            
            for conv in conversations:
                # Parse updated_at from conversation
                conv_updated_at = conv.get("updated_at")
                if not conv_updated_at:
                    # If no updated_at, include it (might be old format)
                    yield conv
                    continue
                
                try:
                    conv_dt = datetime.fromisoformat(conv_updated_at.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    # If we can't parse, include it to be safe
                    yield conv
                    continue
                
                # Only yield if updated after last sync
                if last_dt is None or conv_dt >= last_dt:
                    yield conv
                    
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching conversations: %s", e)
            raise
    
    @dlt.transformer(
        data_from=conversations_list,
        write_disposition="merge",
        primary_key="uuid",
        name="conversation_details"
    )
    def conversation_details(conversation: Dict[str, Any]):
        """
        Fetch full conversation details including messages.
        
        Parameters
        ----
        conversation : Dict[str, Any]
            Conversation metadata from conversations_list
            
        Yields
        ----
        Dict[str, Any]
            Full conversation object with chat_messages
        """
        conv_id = conversation.get("uuid")
        if not conv_id:
            logger.warning("Conversation missing UUID, skipping")
            return
        
        url = (
            f"{CLAUDE_API_BASE}/{org_id}/chat_conversations/{conv_id}"
            "?tree=True&rendering_mode=messages&render_all_tools=true&consistency=eventual"
        )
        
        headers = {
            "Accept": "application/json",
            "Cookie": f"sessionKey={session_cookie}",
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            full_conversation = response.json()
            
            # Merge metadata from list with full details
            full_conversation.update(conversation)
            
            yield full_conversation
            
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching conversation %s: %s", conv_id, e)
            # Yield partial data (metadata only) so we don't lose it
            yield conversation
    
    return conversation_details


class ClaudeReader:
    """
    Reader for Claude.ai conversations using dlt.
    
    Provides an interface compatible with other readers (GlobalComposerReader)
    while leveraging dlt for REST API extraction and incremental sync.
    """
    
    def __init__(
        self,
        org_id: Optional[str] = None,
        session_cookie: Optional[str] = None,
        pipeline_name: str = "claude_conversations"
    ):
        """
        Initialize Claude reader.
        
        Parameters
        ----
        org_id : str, optional
            Organization ID. If None, reads from dlt secrets or env var.
        session_cookie : str, optional
            Session cookie. If None, reads from dlt secrets or env var.
        pipeline_name : str
            Name for dlt pipeline (used for state storage)
        """
        self.org_id = org_id or os.getenv("CLAUDE_ORG_ID")
        self.session_cookie = session_cookie or os.getenv("CLAUDE_SESSION_COOKIE")
        self.pipeline_name = pipeline_name
        
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
    
    def read_all_conversations(self) -> Iterator[Dict[str, Any]]:
        """
        Read all Claude conversations, respecting incremental state.
        
        Uses dlt pipeline to manage incremental sync state automatically.
        Only fetches conversations updated since last sync.
        
        Yields
        ----
        Dict[str, Any]
            Full conversation objects with chat_messages array
        """
        # Create dlt source
        source = claude_conversations(
            org_id=self.org_id,
            session_cookie=self.session_cookie
        )
        
        # Create pipeline for state management
        pipeline = dlt.pipeline(
            pipeline_name=self.pipeline_name,
            destination="filesystem",
            dataset_name="claude_conversations"
        )
        
        try:
            logger.info("Extracting Claude conversations...")
            
            # Run extraction - dlt handles incremental state
            # We'll read the output files to get the data
            load_info = pipeline.run(source)
            
            # Read extracted data from files
            count = 0
            for load_package in load_info.load_packages:
                for job in load_package.jobs:
                    # file_path is directly on job, not on job_file_info
                    file_path_str = job.file_path
                    if not file_path_str:
                        continue
                    
                    file_path = Path(file_path_str)
                    if not file_path.exists():
                        continue
                    
                    if file_path.suffix == '.jsonl':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    yield json.loads(line)
                                    count += 1
                    elif file_path.suffix == '.parquet':
                        import pandas as pd
                        df = pd.read_parquet(file_path)
                        for _, row in df.iterrows():
                            yield row.to_dict()
                            count += 1
            
            logger.info("Extracted %d Claude conversations", count)
                    
        except Exception as e:
            logger.error("Error extracting Claude conversations: %s", e)
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
        url = (
            f"{CLAUDE_API_BASE}/{self.org_id}/chat_conversations/{conversation_id}"
            "?tree=True&rendering_mode=messages&render_all_tools=true&consistency=eventual"
        )
        
        headers = {
            "Accept": "application/json",
            "Cookie": f"sessionKey={self.session_cookie}",
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching conversation %s: %s", conversation_id, e)
            return None

