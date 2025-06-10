#!/usr/bin/env python3
"""
Simple Agent Directory Updater

A streamlined interface for running agent discovery and updates.
This script provides an easy way to expand your AI agents directory.
"""

import os
import subprocess
import sys
import json
from datetime import datetime
from pathlib import Path

class AgentUpdater:
    """Simple interface for updating the agent directory"""
    
    def __init__(self):
        self.current_file = "combined_ai_agents_directory.csv"
        self.backup_dir = "backups"
        Path(self.backup_dir).mkdir(exist_ok=True)
    
    def get_current_stats(self):
        """Get current directory statistics"""
        try:
            import pandas as pd
            if os.path.exists(self.current_file):
                df = pd.read_csv(self.current_file)
                return {
                    'total_agents': len(df),
                    'last_modified': datetime.fromtimestamp(
                        os.path.getmtime(self.current_file)
                    ).strftime("%Y-%m-%d %H:%M:%S")
                }
        except Exception:
            pass
        return {'total_agents': 0, 'last_modified': 'Unknown'}
    
    def run_manual_research(self):
        """Run manual research for new agents"""
        print("Running manual agent research...")
        
        try:
            # Run the research script we created earlier
            result = subprocess.run([
                sys.executable, "new_agents_research.py"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("Research completed successfully")
                return True
            else:
                print("Research failed:", result.stderr)
                return False
        except Exception as e:
            print(f"Error running research: {e}")
            return False
    
    def run_web_discovery(self):
        """Run automated web discovery"""
        print("Running web-based agent discovery...")
        
        try:
            result = subprocess.run([
                sys.executable, "agent_discovery_system.py"
            ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
            
            if result.returncode == 0:
                print("Web discovery completed")
                print(result.stdout)
                return True
            else:
                print("Discovery failed:", result.stderr)
                return False
        except subprocess.TimeoutExpired:
            print("Discovery timed out after 10 minutes")
            return False
        except Exception as e:
            print(f"Error running discovery: {e}")
            return False
    
    def merge_and_update(self):
        """Merge new findings and update directory"""
        print("Merging new agents...")
        
        try:
            result = subprocess.run([
                sys.executable, "merge_agents.py"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("Merge completed successfully")
                print(result.stdout)
                return True
            else:
                print("Merge failed:", result.stderr)
                return False
        except Exception as e:
            print(f"Error during merge: {e}")
            return False
    
    def create_backup(self):
        """Create backup of current directory"""
        if os.path.exists(self.current_file):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{self.backup_dir}/directory_backup_{timestamp}.csv"
            
            import shutil
            shutil.copy2(self.current_file, backup_file)
            print(f"Backup created: {backup_file}")
            return backup_file
        return None
    
    def quick_update(self):
        """Run a quick update cycle"""
        print("\n=== Quick Agent Directory Update ===")
        
        # Show current stats
        stats = self.get_current_stats()
        print(f"Current directory: {stats['total_agents']} agents")
        print(f"Last updated: {stats['last_modified']}")
        
        # Create backup
        backup = self.create_backup()
        if not backup:
            print("Warning: Could not create backup")
        
        # Run research
        if self.run_manual_research():
            # Try to merge results
            if self.run_merge_if_exists():
                new_stats = self.get_current_stats()
                added = new_stats['total_agents'] - stats['total_agents']
                print(f"\nUpdate complete! Added {added} new agents")
                print(f"Total agents: {new_stats['total_agents']}")
                return True
        
        print("\nUpdate failed or no new agents found")
        return False
    
    def run_merge_if_exists(self):
        """Run merge if new agents file exists"""
        if os.path.exists("new_authentic_agents.csv"):
            return self.merge_and_update()
        return False
    
    def full_discovery_update(self):
        """Run full discovery with web scraping"""
        print("\n=== Full Agent Discovery Update ===")
        print("This may take several minutes...")
        
        stats = self.get_current_stats()
        print(f"Starting with {stats['total_agents']} agents")
        
        # Create backup
        self.create_backup()
        
        # Run web discovery
        success = self.run_web_discovery()
        
        if success:
            new_stats = self.get_current_stats()
            added = new_stats['total_agents'] - stats['total_agents']
            print(f"\nFull discovery complete! Added {added} new agents")
            print(f"Total agents: {new_stats['total_agents']}")
        else:
            print("\nFull discovery failed")
        
        return success

def main():
    """Main interface"""
    updater = AgentUpdater()
    
    print("AI Agent Directory Updater")
    print("=" * 40)
    
    stats = updater.get_current_stats()
    print(f"Current directory: {stats['total_agents']} agents")
    print(f"Last updated: {stats['last_modified']}")
    print()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "quick":
            updater.quick_update()
        elif command == "full":
            updater.full_discovery_update()
        elif command == "research":
            updater.run_manual_research()
        elif command == "merge":
            updater.run_merge_if_exists()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: quick, full, research, merge")
    
    else:
        # Interactive mode
        print("Update options:")
        print("1. Quick update (manual research only)")
        print("2. Full discovery (includes web scraping)")
        print("3. Manual research only")
        print("4. Merge existing research")
        print("0. Exit")
        
        try:
            choice = input("\nSelect option (0-4): ").strip()
            
            if choice == "1":
                updater.quick_update()
            elif choice == "2":
                updater.full_discovery_update()
            elif choice == "3":
                updater.run_manual_research()
            elif choice == "4":
                updater.run_merge_if_exists()
            elif choice == "0":
                print("Goodbye!")
            else:
                print("Invalid option")
                
        except KeyboardInterrupt:
            print("\nOperation cancelled")

if __name__ == "__main__":
    main()