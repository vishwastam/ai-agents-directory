import pandas as pd
import os
import json
from models import Agent
from typing import List, Dict, Any
import logging
from intelligent_search import IntelligentSearch
from rating_system import RatingSystem

class DataLoader:
    """Class to handle loading and processing agent data from CSV"""
    
    def __init__(self, csv_path: str = "combined_ai_agents_directory.csv"):
        self.csv_path = csv_path
        self.user_agents_path = "user_agents.json"
        self.agents = []
        self.intelligent_search = IntelligentSearch()
        self.rating_system = RatingSystem()
        self._load_data()
    
    def _load_data(self):
        """Load agent data from CSV file"""
        try:
            if not os.path.exists(self.csv_path):
                logging.error(f"CSV file not found: {self.csv_path}")
                return
            
            df = pd.read_csv(self.csv_path)
            logging.info(f"Loaded {len(df)} agents from CSV")
            
            # Convert DataFrame rows to Agent objects
            for _, row in df.iterrows():
                try:
                    agent = Agent(
                        name=str(row.get('Agent Name', '')),
                        domains=str(row.get('Domains', '')),
                        use_cases=str(row.get('Use Cases', '')),
                        short_desc=str(row.get('Short Desc', '')),
                        long_desc=str(row.get('Long Desc', '')),
                        creator=str(row.get('Creator', '')), 
                        url=str(row.get('URL', '')),
                        platform=str(row.get('Platform', '')),
                        pricing=str(row.get('Pricing', '')),
                        underlying_model=str(row.get('Underlying Model', '')),
                        deployment=str(row.get('Deployment', '')),
                        legitimacy=str(row.get('Legitimacy', '')),
                        what_users_think=str(row.get('What Users Think', ''))
                    )
                    self.agents.append(agent)
                except Exception as e:
                    logging.error(f"Error creating agent from row: {e}")
                    continue
            
            # Load user-submitted agents
            self._load_user_agents()
                    
        except Exception as e:
            logging.error(f"Error loading CSV data: {e}")
    
    def _load_user_agents(self):
        """Load user-submitted agents from JSON file"""
        try:
            if os.path.exists(self.user_agents_path):
                with open(self.user_agents_path, 'r') as f:
                    user_agents_data = json.load(f)
                
                for agent_data in user_agents_data:
                    # Convert dict back to Agent object
                    agent = Agent(
                        name=agent_data['name'],
                        domains=agent_data.get('domains', ''),
                        use_cases=agent_data.get('use_cases', ''),
                        short_desc=agent_data['short_desc'],
                        long_desc=agent_data.get('long_desc', ''),
                        creator=agent_data.get('creator', 'User Submitted'),
                        url=agent_data.get('url', ''),
                        platform=agent_data.get('platform', 'Web'),
                        pricing=agent_data.get('pricing', 'Unknown'),
                        underlying_model=agent_data.get('underlying_model', ''),
                        deployment=agent_data.get('deployment', ''),
                        legitimacy=agent_data.get('legitimacy', 'User Submitted')
                    )
                    self.agents.append(agent)
                
                if user_agents_data:
                    logging.info(f"Loaded {len(user_agents_data)} user-submitted agents")
        except Exception as e:
            logging.error(f"Error loading user agents: {e}")
    
    def add_user_agent(self, agent_data: Dict[str, str]) -> bool:
        """Add a new user-submitted agent"""
        try:
            # Create Agent object with validation
            agent = Agent(
                name=agent_data['name'],
                domains=agent_data.get('domains', ''),
                use_cases=agent_data.get('use_cases', ''),
                short_desc=agent_data['short_desc'],
                long_desc=agent_data.get('long_desc', ''),
                creator=agent_data.get('creator', 'User Submitted'),
                url=agent_data.get('url', ''),
                platform=agent_data.get('platform', 'Web'),
                pricing=agent_data.get('pricing', 'Unknown'),
                underlying_model=agent_data.get('underlying_model', ''),
                deployment=agent_data.get('deployment', ''),
                legitimacy='User Submitted'
            )
            
            # Add to memory
            self.agents.append(agent)
            
            # Save to JSON file
            self._save_user_agents()
            
            logging.info(f"Added new user agent: {agent.name}")
            return True
            
        except Exception as e:
            logging.error(f"Error adding user agent: {e}")
            return False
    
    def _save_user_agents(self):
        """Save user-submitted agents to JSON file"""
        try:
            # Get only user-submitted agents
            user_agents = [agent for agent in self.agents if agent.legitimacy == 'User Submitted']
            
            # Convert to dictionaries for JSON serialization
            agents_data = []
            for agent in user_agents:
                agents_data.append({
                    'name': agent.name,
                    'domains': agent.domains,
                    'use_cases': agent.use_cases,
                    'short_desc': agent.short_desc,
                    'long_desc': agent.long_desc,
                    'creator': agent.creator,
                    'url': agent.url,
                    'platform': agent.platform,
                    'pricing': agent.pricing,
                    'underlying_model': agent.underlying_model,
                    'deployment': agent.deployment,
                    'legitimacy': agent.legitimacy
                })
            
            with open(self.user_agents_path, 'w') as f:
                json.dump(agents_data, f, indent=2)
                
        except Exception as e:
            logging.error(f"Error saving user agents: {e}")
    
    def get_all_agents(self) -> List[Agent]:
        """Get all loaded agents"""
        return self.agents
    
    def get_agent_by_slug(self, slug: str) -> Agent:
        """Get a specific agent by its slug"""
        for agent in self.agents:
            if agent.slug == slug:
                return agent
        raise ValueError(f"Agent with slug '{slug}' not found")
    
    def get_filter_options(self) -> Dict[str, Any]:
        """Get all available filter options for the UI"""
        if not self.agents:
            return {}
        
        # Collect all unique values for filters
        domains = set()
        use_cases = set()
        platforms = set()
        pricing_options = set()
        models = set()
        creators = set()
        
        for agent in self.agents:
            domains.update(agent.domain_list)
            use_cases.update(agent.use_case_list)
            platforms.update(agent.platform_list)
            pricing_options.add(agent.pricing_clean)
            if agent.underlying_model.strip():
                models.add(agent.underlying_model.strip())
            if agent.creator.strip():
                creators.add(agent.creator.strip())
        
        return {
            'domains': sorted(list(domains)),
            'use_cases': sorted(list(use_cases)),
            'platforms': sorted(list(platforms)),
            'pricing': sorted(list(pricing_options)),
            'models': sorted(list(models)),
            'creators': sorted(list(creators))
        }
    
    def search_agents(self, query: str = "", filters: Dict[str, Any] | None = None) -> List[Agent]:
        """Search and filter agents based on query and filters"""
        if filters is None:
            filters = {}
        
        results = self.agents.copy()
        
        # Apply intelligent search
        if query:
            results = self.intelligent_search.search(results, query)
        
        # Apply filters
        if filters.get('domain'):
            results = [
                agent for agent in results
                if filters['domain'] in agent.domain_list
            ]
        
        if filters.get('use_case'):
            results = [
                agent for agent in results
                if filters['use_case'] in agent.use_case_list
            ]
        
        if filters.get('platform'):
            results = [
                agent for agent in results
                if filters['platform'] in agent.platform_list
            ]
        

        
        if filters.get('model'):
            results = [
                agent for agent in results
                if filters['model'].lower() in agent.underlying_model.lower()
            ]
        
        if filters.get('creator'):
            results = [
                agent for agent in results
                if filters['creator'].lower() in agent.creator.lower()
            ]
        
        return results

# Global data loader instance
data_loader = DataLoader()
