"""
Intelligent search functionality using fuzzy matching and semantic understanding
"""
from fuzzywuzzy import fuzz, process
from typing import List, Dict, Any
import re

class IntelligentSearch:
    """Enhanced search with fuzzy matching and natural language understanding"""
    
    def __init__(self):
        # Keywords for different categories to understand user intent
        self.domain_keywords = {
            'Software Development': ['code', 'coding', 'programming', 'developer', 'development', 'software', 'github', 'copilot', 'ide', 'autocomplete'],
            'Writing': ['writing', 'content', 'text', 'article', 'blog', 'copywriting', 'grammar', 'editing', 'documentation'],
            'Marketing': ['marketing', 'ads', 'advertising', 'campaign', 'social media', 'email', 'mailchimp', 'hubspot', 'sales'],
            'Productivity': ['productivity', 'organize', 'schedule', 'task', 'meeting', 'notes', 'calendar', 'workflow', 'automation'],
            'Image Generation': ['image', 'picture', 'photo', 'visual', 'art', 'design', 'dall-e', 'midjourney', 'stable diffusion'],
            'Audio Generation': ['audio', 'voice', 'speech', 'sound', 'music', 'podcast', 'tts', 'text-to-speech'],
            'Video Generation': ['video', 'animation', 'movie', 'clip', 'motion', 'multimedia'],
            'Education': ['learn', 'education', 'teaching', 'tutor', 'study', 'academic', 'student', 'homework'],
            'Research': ['research', 'analysis', 'data', 'information', 'study', 'investigation', 'academic'],
            'Healthcare': ['health', 'medical', 'doctor', 'patient', 'diagnosis', 'treatment', 'medicine'],
            'Finance': ['finance', 'money', 'investment', 'trading', 'banking', 'accounting', 'budget'],
            'Customer Service': ['customer', 'support', 'service', 'help', 'chat', 'ticket', 'assistance']
        }
        
        self.platform_keywords = {
            'Web': ['web', 'browser', 'online', 'website'],
            'API': ['api', 'integration', 'development', 'programmatic'],
            'iOS': ['ios', 'iphone', 'ipad', 'mobile', 'app store'],
            'Android': ['android', 'mobile', 'google play'],
            'Desktop': ['desktop', 'computer', 'pc', 'mac'],
            'Chrome Extension': ['chrome', 'extension', 'browser'],
            'VS Code Extension': ['vscode', 'vs code', 'editor', 'ide']
        }
        
        self.pricing_keywords = {
            'Free': ['free', 'no cost', 'gratis', 'zero cost'],
            'Freemium': ['freemium', 'free tier', 'limited free'],
            'Paid': ['paid', 'subscription', 'premium', 'cost', 'price']
        }

    def extract_intent(self, query: str) -> Dict[str, List[str]]:
        """Extract user intent from natural language query"""
        query_lower = query.lower()
        intent = {
            'domains': [],
            'platforms': [],
            'pricing': [],
            'keywords': []
        }
        
        # Extract domain intent
        for domain, keywords in self.domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                intent['domains'].append(domain)
        
        # Extract platform intent
        for platform, keywords in self.platform_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                intent['platforms'].append(platform)
                
        # Extract pricing intent
        for pricing, keywords in self.pricing_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                intent['pricing'].append(pricing)
        
        # Extract important keywords (remove common words)
        stop_words = {'for', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'is', 'are', 'was', 'were', 'a', 'an', 'that', 'this', 'with', 'i', 'me', 'my', 'we', 'our', 'you', 'your'}
        words = re.findall(r'\w+', query_lower)
        intent['keywords'] = [word for word in words if word not in stop_words and len(word) > 2]
        
        return intent

    def calculate_relevance_score(self, agent: Any, query: str, intent: Dict[str, List[str]]) -> float:
        """Calculate relevance score for an agent based on query and intent"""
        score = 0.0
        
        # Direct text matching with fuzzy search
        agent_text = f"{agent.name} {agent.short_desc} {agent.long_desc} {agent.domains} {agent.use_cases} {agent.creator}"
        
        # Fuzzy match on agent text
        fuzzy_score = fuzz.partial_ratio(query.lower(), agent_text.lower()) / 100.0
        score += fuzzy_score * 0.4
        
        # Domain matching
        if intent['domains']:
            agent_domains = getattr(agent, 'domain_list', [])
            for domain in intent['domains']:
                if any(fuzz.ratio(domain.lower(), ad.lower()) > 80 for ad in agent_domains):
                    score += 0.3
        
        # Platform matching
        if intent['platforms']:
            agent_platforms = getattr(agent, 'platform_list', [])
            for platform in intent['platforms']:
                if any(fuzz.ratio(platform.lower(), ap.lower()) > 80 for ap in agent_platforms):
                    score += 0.2
        
        # Pricing matching
        if intent['pricing']:
            agent_pricing = getattr(agent, 'pricing_clean', '')
            for pricing in intent['pricing']:
                if fuzz.ratio(pricing.lower(), agent_pricing.lower()) > 80:
                    score += 0.1
        
        # Keyword matching in name and description (higher weight)
        for keyword in intent['keywords']:
            if keyword in agent.name.lower():
                score += 0.3
            if keyword in agent.short_desc.lower():
                score += 0.2
            if keyword in agent.long_desc.lower():
                score += 0.1
        
        # Creator matching
        if any(keyword in agent.creator.lower() for keyword in intent['keywords']):
            score += 0.15
            
        # Use case matching
        agent_use_cases = getattr(agent, 'use_case_list', [])
        for keyword in intent['keywords']:
            for use_case in agent_use_cases:
                if fuzz.partial_ratio(keyword, use_case.lower()) > 70:
                    score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0

    def search(self, agents: List[Any], query: str, threshold: float = 0.1) -> List[Any]:
        """Perform intelligent search on agents"""
        if not query or not query.strip():
            return agents
        
        query = query.strip()
        intent = self.extract_intent(query)
        
        # Calculate relevance scores
        scored_agents = []
        for agent in agents:
            score = self.calculate_relevance_score(agent, query, intent)
            if score >= threshold:
                scored_agents.append((agent, score))
        
        # Sort by relevance score (highest first)
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        
        # Return agents only (without scores)
        return [agent for agent, score in scored_agents]