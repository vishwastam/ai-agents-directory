from flask import render_template, request, jsonify, abort, redirect, url_for, flash
from app import app
from data_loader import data_loader
import json
import logging

@app.route('/')
def index():
    """Main listing page with all agents and filters"""
    # Get filter parameters from URL
    query = request.args.get('q', '').strip()
    filters = {
        'domain': request.args.get('domain'),
        'use_case': request.args.get('use_case'),
        'platform': request.args.get('platform'),
        'model': request.args.get('model'),
        'creator': request.args.get('creator')
    }
    
    # Remove empty filters
    filters = {k: v for k, v in filters.items() if v}
    
    # Get filtered agents
    agents = data_loader.search_agents(query, filters)
    
    # Get filter options for the UI
    filter_options = data_loader.get_filter_options()
    
    return render_template('index.html', 
                         agents=agents,
                         filter_options=filter_options,
                         current_query=query,
                         current_filters=filters,
                         total_agents=len(data_loader.get_all_agents()),
                         show_success=request.args.get('success'))

@app.route('/agent/<slug>')
def agent_detail(slug):
    """Individual agent detail page"""
    agent = data_loader.get_agent_by_slug(slug)
    
    if not agent:
        abort(404)
    
    # Get related agents (same primary domain or use case)
    all_agents = data_loader.get_all_agents()
    related_agents = [
        a for a in all_agents 
        if a.slug != slug and (
            a.primary_domain == agent.primary_domain or 
            a.primary_use_case == agent.primary_use_case
        )
    ][:6]  # Limit to 6 related agents
    
    # Get rating data for this agent
    rating_data = data_loader.rating_system.get_agent_ratings(agent.slug)
    
    return render_template('agent_detail.html', 
                         agent=agent,
                         related_agents=related_agents,
                         rating_data=rating_data,
                         json_ld=json.dumps(agent.get_json_ld(), indent=2),
                         rating_success=request.args.get('rating_success'),
                         rating_error=request.args.get('error'))

@app.route('/api/search')
def api_search():
    """API endpoint for AJAX search (if needed for future enhancements)"""
    query = request.args.get('q', '').strip()
    filters = {
        'domain': request.args.get('domain'),
        'use_case': request.args.get('use_case'),  
        'platform': request.args.get('platform'),
        'pricing': request.args.get('pricing'),
        'model': request.args.get('model'),
        'creator': request.args.get('creator')
    }
    
    # Remove empty filters
    filters = {k: v for k, v in filters.items() if v}
    
    agents = data_loader.search_agents(query, filters)
    
    # Convert agents to JSON-serializable format
    results = []
    for agent in agents:
        results.append({
            'name': agent.name,
            'slug': agent.slug,
            'short_desc': agent.short_desc,
            'domains': agent.domain_list,
            'use_cases': agent.use_case_list,
            'pricing': agent.pricing_clean,
            'creator': agent.creator,
            'url': agent.url
        })
    
    return jsonify({
        'agents': results,
        'total': len(results)
    })

@app.route('/add-agent', methods=['POST'])
def add_agent():
    """Handle submission of new agent form"""
    try:
        # Get form data
        agent_data = {
            'name': request.form.get('name', '').strip(),
            'short_desc': request.form.get('short_desc', '').strip(),
            'url': request.form.get('url', '').strip(),
            'creator': request.form.get('creator', '').strip(),
            'domains': request.form.get('domains', '').strip(),
            'use_cases': request.form.get('use_cases', '').strip(),
            'platform': request.form.get('platform', 'Web').strip(),
            'pricing': request.form.get('pricing', 'Unknown').strip(),
            'long_desc': request.form.get('long_desc', '').strip(),
            'underlying_model': request.form.get('underlying_model', '').strip()
        }
        
        # Validate required fields
        required_fields = ['name', 'short_desc']
        missing_fields = [field for field in required_fields if not agent_data[field]]
        
        if missing_fields:
            return redirect(url_for('index', error='missing_fields'))
        
        # Add the agent
        success = data_loader.add_user_agent(agent_data)
        
        if success:
            return redirect(url_for('index', success='1'))
        else:
            return redirect(url_for('index', error='save_failed'))
            
    except Exception as e:
        logging.error(f"Error in add_agent route: {e}")
        return redirect(url_for('index', error='general'))

@app.route('/rate-agent', methods=['POST'])
def rate_agent():
    """Handle agent rating submission"""
    try:
        # Get form data
        agent_slug = request.form.get('agent_slug', '').strip()
        rating = request.form.get('rating', type=int)
        feedback = request.form.get('feedback', '').strip()
        
        # Validate data
        if not agent_slug or not rating or not (1 <= rating <= 5):
            return redirect(url_for('agent_detail', slug=agent_slug, error='invalid_rating'))
        
        # Check if agent exists
        try:
            agent = data_loader.get_agent_by_slug(agent_slug)
        except ValueError:
            return redirect(url_for('index', error='agent_not_found'))
        
        # Add rating
        success = data_loader.rating_system.add_rating(
            agent_slug=agent_slug,
            rating=rating,
            feedback=feedback,
            user_identifier=request.remote_addr or 'anonymous'  # Use IP as simple user identifier
        )
        
        if success:
            return redirect(url_for('agent_detail', slug=agent_slug, rating_success='1'))
        else:
            return redirect(url_for('agent_detail', slug=agent_slug, error='rating_failed'))
            
    except Exception as e:
        logging.error(f"Error in rate_agent route: {e}")
        return redirect(url_for('index', error='general'))

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logging.error(f"Internal server error: {error}")
    return render_template('500.html'), 500
