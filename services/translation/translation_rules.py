# -*- coding: utf-8 -*-
import os

RULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "translation_rules")

def get_available_rules() -> list[str]:
    """Returns a list of translation rule names (without .md extension) sorted, with 'Standard' first if present."""
    if not os.path.exists(RULES_DIR):
        return ["Standard"]
    
    rules = []
    for filename in os.listdir(RULES_DIR):
        if filename.endswith(".md"):
            rules.append(filename[:-3])
            
    rules.sort()
    
    # Ensure 'Standard' is first
    if "Standard" in rules:
        rules.remove("Standard")
        rules.insert(0, "Standard")
        
    return rules if rules else ["Standard"]

def load_translation_rule(rule_name: str) -> str:
    """Loads the content of the specified translation rule .md file."""
    if rule_name == "Raw - Direct":
        return ""
        
    filepath = os.path.join(RULES_DIR, f"{rule_name}.md")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    
    return ""
