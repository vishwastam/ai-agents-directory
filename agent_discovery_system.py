#!/usr/bin/env python3
"""
Automated AI Agent Discovery and Directory Update System

This system can be run periodically to discover new AI agents and update the directory.
It includes web scraping, data validation, duplicate detection, and automated integration.
"""

import json
import csv
import os
import time
import logging
import requests
import trafilatura
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_discovery.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class DiscoveredAgent:
    """Data structure for discovered AI agents"""
    name: str
    creator: str
    url: str
    description: str
    category: str = ""
    pricing: str = ""
    platform: str = ""
    confidence_score: float = 0.0
    source_url: str = ""
    discovered_date: str = ""

class AgentDiscoverySystem:
    """Main system for discovering and integrating new AI agents"""
    
    def __init__(self, config_file: str = "discovery_config.json"):
        self.config_file = config_file
        self.load_config()
        self.discovered_agents = []
        self.existing_agents_file = "combined_ai_agents_directory.csv"
        self.backup_dir = "backups"
        Path(self.backup_dir).mkdir(exist_ok=True)
    
    def load_config(self):
        """Load configuration for discovery sources and settings"""
        default_config = {
            "sources": {
                "ai_directories": [
                    "https://www.producthunt.com/topics/artificial-intelligence",
                    "https://www.futurepedia.io/",
                    "https://aitoolnet.com/",
                    "https://www.toolify.ai/",
                    "https://aitools.fyi/"
                ],
                "company_pages": [
                    "https://www.anthropic.com/",
                    "https://www.perplexity.ai/",
                    "https://www.cohere.com/",
                    "https://stability.ai/",
                    "https://runwayml.com/",
                    "https://replicate.com/",
                    "https://huggingface.co/",
                    "https://elevenlabs.io/",
                    "https://lumalabs.ai/"
                ],
                "github_orgs": [
                    "openai",
                    "anthropic-ai", 
                    "google-research",
                    "microsoft",
                    "meta-llama"
                ]
            },
            "discovery_settings": {
                "min_confidence_score": 0.6,
                "max_agents_per_run": 50,
                "request_delay": 2,
                "timeout": 30,
                "user_agent": "Mozilla/5.0 (compatible; AgentDiscovery/1.0)"
            },
            "validation_rules": {
                "required_fields": ["name", "creator", "url"],
                "min_description_length": 50,
                "max_description_length": 1000,
                "valid_pricing_types": ["Free", "Freemium", "Paid", "Subscription", "Usage-based", "Enterprise"]
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                logging.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logging.warning(f"Error loading config: {e}. Using defaults.")
                self.config = default_config
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """Save current configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logging.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logging.error(f"Error saving config: {e}")
    
    def scrape_with_retry(self, url: str, max_retries: int = 3) -> Optional[str]:
        """Scrape content from URL with retry logic"""
        for attempt in range(max_retries):
            try:
                logging.info(f"Scraping {url} (attempt {attempt + 1})")
                
                # Use custom headers to avoid blocking
                headers = {
                    'User-Agent': self.config['discovery_settings']['user_agent'],
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
                
                response = requests.get(
                    url, 
                    headers=headers,
                    timeout=self.config['discovery_settings']['timeout']
                )
                
                if response.status_code == 200:
                    # Use trafilatura for content extraction
                    text = trafilatura.extract(response.content)
                    if text:
                        logging.info(f"Successfully extracted content from {url}")
                        return text
                else:
                    logging.warning(f"HTTP {response.status_code} for {url}")
                
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.config['discovery_settings']['request_delay'] * (attempt + 1))
        
        logging.error(f"Failed to scrape {url} after {max_retries} attempts")
        return None
    
    def extract_agents_from_content(self, content: str, source_url: str) -> List[DiscoveredAgent]:
        """Extract potential AI agents from scraped content"""
        agents = []
        
        # Split content into potential agent entries
        lines = content.split('\n')
        current_agent = {}
        
        # Keywords that suggest AI tools/agents
        ai_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'ml', 'gpt', 
            'bot', 'assistant', 'generator', 'model', 'neural', 'llm',
            'automation', 'chatbot', 'voice', 'vision', 'nlp'
        ]
        
        # Company/product indicators
        company_indicators = [
            'inc', 'corp', 'llc', 'ltd', 'labs', 'ai', 'technologies',
            'systems', 'studio', 'platform', 'api', 'sdk'
        ]
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            line_lower = line.lower()
            
            # Look for AI-related content
            if any(keyword in line_lower for keyword in ai_keywords):
                # Try to extract structured information
                
                # Look for URLs in nearby lines
                url = self.extract_url_from_context(lines, i)
                
                # Look for company/creator names
                creator = self.extract_creator_from_context(lines, i, company_indicators)
                
                # Calculate confidence score
                confidence = self.calculate_confidence_score(line, url, creator)
                
                if confidence >= self.config['discovery_settings']['min_confidence_score']:
                    agent = DiscoveredAgent(
                        name=self.clean_agent_name(line),
                        creator=creator or "Unknown",
                        url=url or "",
                        description=line,
                        confidence_score=confidence,
                        source_url=source_url,
                        discovered_date=datetime.now().isoformat()
                    )
                    agents.append(agent)
        
        return agents[:self.config['discovery_settings']['max_agents_per_run']]
    
    def extract_url_from_context(self, lines: List[str], current_index: int, window: int = 3) -> Optional[str]:
        """Extract URL from nearby lines"""
        start = max(0, current_index - window)
        end = min(len(lines), current_index + window + 1)
        
        for line in lines[start:end]:
            # Simple URL extraction
            if 'http' in line.lower():
                import re
                urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', line)
                if urls:
                    return urls[0]
        return None
    
    def extract_creator_from_context(self, lines: List[str], current_index: int, indicators: List[str]) -> Optional[str]:
        """Extract creator/company name from context"""
        start = max(0, current_index - 2)
        end = min(len(lines), current_index + 3)
        
        for line in lines[start:end]:
            line_lower = line.lower()
            if any(indicator in line_lower for indicator in indicators):
                # Extract potential company name
                words = line.split()
                for i, word in enumerate(words):
                    if any(indicator in word.lower() for indicator in indicators):
                        # Take the word before the indicator as company name
                        if i > 0:
                            return words[i-1].strip('.,()[]{}')
        return None
    
    def calculate_confidence_score(self, text: str, url: Optional[str], creator: Optional[str]) -> float:
        """Calculate confidence score for discovered agent"""
        score = 0.0
        text_lower = text.lower()
        
        # Base score for AI-related keywords
        ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'gpt', 'model']
        keyword_matches = sum(1 for keyword in ai_keywords if keyword in text_lower)
        score += min(keyword_matches * 0.2, 0.6)
        
        # Bonus for having URL
        if url:
            score += 0.2
            if any(domain in url for domain in ['.ai', '.com', '.io', '.org']):
                score += 0.1
        
        # Bonus for having creator
        if creator and creator != "Unknown":
            score += 0.1
        
        # Bonus for length (indicates detailed description)
        if 50 <= len(text) <= 200:
            score += 0.1
        
        return min(score, 1.0)
    
    def clean_agent_name(self, text: str) -> str:
        """Clean and extract agent name from text"""
        # Take first sentence or up to first comma/period
        name = text.split('.')[0].split(',')[0].split(':')[0]
        
        # Remove common prefixes/suffixes
        prefixes = ['introducing', 'new', 'the', 'meet', 'try']
        suffixes = ['ai', 'tool', 'platform', 'app', 'software']
        
        words = name.split()
        if words and words[0].lower() in prefixes:
            words = words[1:]
        
        return ' '.join(words).strip()[:100]  # Limit length
    
    def validate_agent(self, agent: DiscoveredAgent) -> bool:
        """Validate discovered agent against rules"""
        rules = self.config['validation_rules']
        
        # Check required fields
        for field in rules['required_fields']:
            if not getattr(agent, field) or getattr(agent, field) == "Unknown":
                return False
        
        # Check description length
        desc_len = len(agent.description)
        if desc_len < rules['min_description_length'] or desc_len > rules['max_description_length']:
            return False
        
        return True
    
    def load_existing_agents(self) -> set:
        """Load existing agent names to avoid duplicates"""
        existing_names = set()
        try:
            if os.path.exists(self.existing_agents_file):
                df = pd.read_csv(self.existing_agents_file)
                existing_names = set(df['Agent Name'].str.lower())
        except Exception as e:
            logging.error(f"Error loading existing agents: {e}")
        
        return existing_names
    
    def filter_duplicates(self, agents: List[DiscoveredAgent]) -> List[DiscoveredAgent]:
        """Filter out duplicate agents"""
        existing_names = self.load_existing_agents()
        filtered_agents = []
        
        for agent in agents:
            if agent.name.lower() not in existing_names:
                filtered_agents.append(agent)
            else:
                logging.info(f"Filtered duplicate: {agent.name}")
        
        return filtered_agents
    
    def create_backup(self):
        """Create backup of current directory"""
        if os.path.exists(self.existing_agents_file):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{self.backup_dir}/agents_backup_{timestamp}.csv"
            
            import shutil
            shutil.copy2(self.existing_agents_file, backup_file)
            logging.info(f"Created backup: {backup_file}")
    
    def integrate_new_agents(self, agents: List[DiscoveredAgent]) -> bool:
        """Integrate new agents into the directory"""
        if not agents:
            logging.info("No new agents to integrate")
            return True
        
        try:
            # Create backup first
            self.create_backup()
            
            # Load existing data
            if os.path.exists(self.existing_agents_file):
                existing_df = pd.read_csv(self.existing_agents_file)
            else:
                # Create new file with headers
                existing_df = pd.DataFrame(columns=[
                    'Agent Name', 'Domains', 'Use Cases', 'Short Desc', 'Long Desc',
                    'Creator', 'URL', 'Platform', 'Pricing', 'Underlying Model',
                    'Deployment', 'Legitimacy'
                ])
            
            # Convert discovered agents to DataFrame format
            new_rows = []
            for agent in agents:
                row = {
                    'Agent Name': agent.name,
                    'Domains': agent.category or 'General AI',
                    'Use Cases': 'Discovered automatically - needs review',
                    'Short Desc': agent.description[:200] + '...' if len(agent.description) > 200 else agent.description,
                    'Long Desc': agent.description,
                    'Creator': agent.creator,
                    'URL': agent.url,
                    'Platform': agent.platform or 'Web',
                    'Pricing': agent.pricing or 'Unknown',
                    'Underlying Model': 'Unknown',
                    'Deployment': 'Cloud',
                    'Legitimacy': f'Auto-discovered (confidence: {agent.confidence_score:.2f})'
                }
                new_rows.append(row)
            
            # Combine and save
            new_df = pd.DataFrame(new_rows)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.to_csv(self.existing_agents_file, index=False)
            
            logging.info(f"Successfully integrated {len(agents)} new agents")
            return True
            
        except Exception as e:
            logging.error(f"Error integrating agents: {e}")
            return False
    
    def run_discovery(self) -> Dict[str, Any]:
        """Run the complete discovery process"""
        start_time = datetime.now()
        logging.info("Starting agent discovery process")
        
        all_discovered = []
        sources_processed = 0
        errors = []
        
        # Process all configured sources
        all_sources = (
            self.config['sources']['ai_directories'] + 
            self.config['sources']['company_pages']
        )
        
        for source_url in all_sources:
            try:
                content = self.scrape_with_retry(source_url)
                if content:
                    agents = self.extract_agents_from_content(content, source_url)
                    validated_agents = [agent for agent in agents if self.validate_agent(agent)]
                    all_discovered.extend(validated_agents)
                    sources_processed += 1
                    logging.info(f"Found {len(validated_agents)} valid agents from {source_url}")
                
                # Respectful delay between requests
                time.sleep(self.config['discovery_settings']['request_delay'])
                
            except Exception as e:
                error_msg = f"Error processing {source_url}: {e}"
                errors.append(error_msg)
                logging.error(error_msg)
        
        # Filter duplicates and integrate
        filtered_agents = self.filter_duplicates(all_discovered)
        integration_success = self.integrate_new_agents(filtered_agents)
        
        # Generate report
        end_time = datetime.now()
        duration = end_time - start_time
        
        report = {
            'discovery_date': start_time.isoformat(),
            'duration_seconds': duration.total_seconds(),
            'sources_processed': sources_processed,
            'total_sources': len(all_sources),
            'agents_discovered': len(all_discovered),
            'agents_after_dedup': len(filtered_agents),
            'integration_success': integration_success,
            'errors': errors
        }
        
        # Save report
        report_file = f"discovery_reports/report_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs('discovery_reports', exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logging.info(f"Discovery complete. Report saved to {report_file}")
        return report

def main():
    """Main function for running agent discovery"""
    system = AgentDiscoverySystem()
    
    print("🚀 AI Agent Discovery System")
    print("="*50)
    
    # Run discovery
    report = system.run_discovery()
    
    # Display summary
    print(f"\n📊 Discovery Summary:")
    print(f"Duration: {report['duration_seconds']:.1f} seconds")
    print(f"Sources processed: {report['sources_processed']}/{report['total_sources']}")
    print(f"Agents discovered: {report['agents_discovered']}")
    print(f"New agents added: {report['agents_after_dedup']}")
    print(f"Integration: {'✅ Success' if report['integration_success'] else '❌ Failed'}")
    
    if report['errors']:
        print(f"\n⚠️  Errors encountered: {len(report['errors'])}")
        for error in report['errors'][:3]:  # Show first 3 errors
            print(f"  - {error}")
    
    print(f"\n📁 Updated directory saved to: {system.existing_agents_file}")

if __name__ == "__main__":
    main()