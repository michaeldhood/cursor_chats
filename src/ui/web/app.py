"""
Flask web UI for browsing and searching aggregated chats.
"""
import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for
from pathlib import Path

from src.core.db import ChatDatabase, get_default_db_path
from src.services.search import ChatSearchService

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)


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
        
        # Get pagination params
        page = int(request.args.get('page', 1))
        limit = 50
        offset = (page - 1) * limit
        
        chats = search_service.list_chats(limit=limit, offset=offset)
        
        # Get total count (approximate)
        total_chats = len(search_service.list_chats(limit=10000))
        
        return render_template('index.html', 
                             chats=chats, 
                             page=page, 
                             total_chats=total_chats,
                             has_next=len(chats) == limit)
    finally:
        db.close()


@app.route('/search')
def search():
    """Search page."""
    query = request.args.get('q', '')
    
    if not query:
        return redirect(url_for('index'))
    
    db = get_db()
    try:
        search_service = ChatSearchService(db)
        
        page = int(request.args.get('page', 1))
        limit = 50
        offset = (page - 1) * limit
        
        results = search_service.search(query, limit=limit, offset=offset)
        
        return render_template('search.html', 
                             query=query, 
                             results=results,
                             page=page,
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
        
        chats = search_service.list_chats(limit=limit, offset=offset)
        
        return jsonify({
            'chats': chats,
            'page': page,
            'limit': limit
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


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

