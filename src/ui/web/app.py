"""
Flask web UI for browsing and searching aggregated chats.
"""
import os
import logging
import queue
import threading
import time
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from pathlib import Path

from src.core.db import ChatDatabase
from src.core.config import get_default_db_path
from src.services.search import ChatSearchService

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Global queue management for SSE client connections
update_queues: list[queue.Queue] = []
update_queues_lock = threading.Lock()


def broadcast_update():
    """
    Broadcast an update event to all connected SSE clients.
    
    Called when database changes are detected (via polling in /stream endpoint).
    """
    with update_queues_lock:
        for q in update_queues:
            try:
                q.put({'type': 'update', 'timestamp': time.time()})
            except Exception as e:
                logger.debug("Error broadcasting to client: %s", e)


def get_db():
    """Get database instance."""
    db_path = os.getenv('CURSOR_CHATS_DB_PATH') or str(get_default_db_path())
    return ChatDatabase(db_path)


@app.route('/')
def index():
    """Home page - list all chats."""
    db = get_db()
    try:
        search_service = ChatSearchService(db)
        
        # Get pagination and filter params
        page = int(request.args.get('page', 1))
        limit = 50
        offset = (page - 1) * limit
        empty_filter = request.args.get('filter', None)  # 'empty', 'non_empty', or None
        tag_filter = request.args.get('tag', None)  # Single tag or comma-separated tags
        
        # Parse tag filter
        tags_filter = None
        if tag_filter:
            tags_filter = [t.strip() for t in tag_filter.split(',') if t.strip()]
        
        chats = search_service.list_chats(limit=limit, offset=offset, empty_filter=empty_filter, 
                                          tags_filter=tags_filter)
        
        # Get total count using COUNT query with filter
        total_chats = search_service.count_chats(empty_filter=empty_filter, tags_filter=tags_filter)
        
        # Get all available tags for the filter dropdown
        all_tags = db.get_all_tags()
        
        return render_template('index.html', 
                             chats=chats, 
                             page=page, 
                             total_chats=total_chats,
                             has_next=len(chats) == limit,
                             current_filter=empty_filter,
                             current_tag=tag_filter,
                             all_tags=all_tags)
    finally:
        db.close()


@app.route('/search')
def search():
    """Search page."""
    query = request.args.get('q', '')
    
    if not query:
        return redirect(url_for('index'))
    
    # Check for tag: prefix in query
    if query.startswith('tag:'):
        # Extract tag and redirect to index with tag filter
        tag = query[4:].strip()
        return redirect(url_for('index', tag=tag))
    
    db = get_db()
    try:
        search_service = ChatSearchService(db)
        
        page = int(request.args.get('page', 1))
        limit = 50
        offset = (page - 1) * limit
        
        results = search_service.search(query, limit=limit, offset=offset)
        total_results = search_service.count_search(query)
        
        return render_template('search.html', 
                             query=query, 
                             results=results,
                             page=page,
                             total_results=total_results,
                             has_next=len(results) == limit)
    finally:
        db.close()


@app.route('/chat/<int:chat_id>')
def chat_detail(chat_id):
    """Chat detail page."""
    db = get_db()
    try:
        search_service = ChatSearchService(db)
        chat = search_service.get_chat(chat_id)
        
        if not chat:
            return "Chat not found", 404
        
        # Process messages to group tool calls and filter empty
        processed_messages = []
        tool_call_group = []
        
        for msg in chat.get('messages', []):
            msg_type = msg.get('message_type', 'response')
            
            if msg_type == 'empty':
                # Skip empty messages
                continue
            elif msg_type == 'tool_call':
                # Accumulate tool calls
                tool_call_group.append(msg)
            else:
                # Flush any accumulated tool calls before this message
                if tool_call_group:
                    processed_messages.append({
                        'type': 'tool_call_group',
                        'tool_calls': tool_call_group.copy()
                    })
                    tool_call_group = []
                # Add the regular message
                processed_messages.append({
                    'type': 'message',
                    'data': msg
                })
        
        # Flush any remaining tool calls at the end
        if tool_call_group:
            processed_messages.append({
                'type': 'tool_call_group',
                'tool_calls': tool_call_group
            })
        
        chat['processed_messages'] = processed_messages
        
        return render_template('chat_detail.html', chat=chat)
    finally:
        db.close()


@app.route('/api/chats')
def api_chats():
    """API endpoint for chats list."""
    db = get_db()
    try:
        search_service = ChatSearchService(db)
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        empty_filter = request.args.get('filter', None)
        tag_filter = request.args.get('tag', None)
        
        # Parse tag filter
        tags_filter = None
        if tag_filter:
            tags_filter = [t.strip() for t in tag_filter.split(',') if t.strip()]
        
        chats = search_service.list_chats(limit=limit, offset=offset, empty_filter=empty_filter,
                                          tags_filter=tags_filter)
        total_chats = search_service.count_chats(empty_filter=empty_filter, tags_filter=tags_filter)
        
        return jsonify({
            'chats': chats,
            'page': page,
            'limit': limit,
            'filter': empty_filter,
            'tag': tag_filter,
            'total': total_chats
        })
    finally:
        db.close()


@app.route('/api/search')
def api_search():
    """API endpoint for search."""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': 'Query required'}), 400
    
    db = get_db()
    try:
        search_service = ChatSearchService(db)
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        results = search_service.search(query, limit=limit, offset=offset)
        
        return jsonify({
            'query': query,
            'results': results,
            'page': page,
            'limit': limit
        })
    finally:
        db.close()


@app.route('/stream')
def stream():
    """
    Server-Sent Events endpoint for live updates.
    
    Polls the database every 2 seconds for changes and pushes updates to connected clients.
    """
    def event_stream():
        """Generator function for SSE stream."""
        q = queue.Queue()
        
        # Register this client's queue
        with update_queues_lock:
            update_queues.append(q)
        
        try:
            # Send initial connection message
            yield "data: {}\n\n".format(json.dumps({'type': 'connected'}))
            
            # Poll database for changes
            db = get_db()
            try:
                last_seen = db.get_last_updated_at()
                
                while True:
                    time.sleep(2)  # Check every 2 seconds
                    
                    # Check database for updates
                    current = db.get_last_updated_at()
                    if current and current != last_seen:
                        last_seen = current
                        # Send update event
                        yield "data: {}\n\n".format(json.dumps({
                            'type': 'update',
                            'timestamp': current
                        }))
                    
                    # Also check queue for manual broadcasts (future use)
                    try:
                        data = q.get(timeout=0.1)
                        yield "data: {}\n\n".format(json.dumps(data))
                    except queue.Empty:
                        pass
                        
            finally:
                db.close()
        finally:
            # Unregister this client's queue
            with update_queues_lock:
                if q in update_queues:
                    update_queues.remove(q)
    
    return Response(event_stream(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

