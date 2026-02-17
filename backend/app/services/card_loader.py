"""
Card Loader Module

Responsibility: Load and parse debate character cards from JSON files.
This module is independent and decoupled from other modules.
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class DebateRole(Enum):
    """Debate role enumeration."""
    PRO = "pro"
    CON = "con"


@dataclass
class DebateCard:
    """Debate character card data structure."""
    id: str
    name: str
    description: str
    personality: str
    scenario: str
    response_rules: list[str]
    system_prompt_template: str
    opening_statements: list[str]
    tags: list[str]
    character_book_description: str = ""
    avatar: str = ""
    difficulty: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "personality": self.personality,
            "scenario": self.scenario,
            "response_rules": self.response_rules,
            "system_prompt_template": self.system_prompt_template,
            "opening_statements": self.opening_statements,
            "tags": self.tags,
            "character_book_description": self.character_book_description,
            "avatar": self.avatar,
            "difficulty": self.difficulty,
        }


class CardLoaderError(Exception):
    """Custom exception for card loading errors."""
    pass


class CardLoader:
    """
    Load debate character cards from JSON files.

    Usage:
        loader = CardLoader()
        card = loader.load_card("philosophical_dreamer")
        print(card.name)  # "Philosophical Dreamer"

        # List all available cards
        cards = loader.list_cards()
        print(cards)  # [{"id": "philosopher", "name": "..."}]
    """

    def __init__(self, cards_dir: Optional[str] = None):
        """
        Initialize card loader.

        Args:
            cards_dir: Directory containing card JSON files.
        """
        self.cards_dir = cards_dir

    def _get_card_path(self, card_id: str) -> str:
        """Get the file path for a card by ID."""
        if self.cards_dir:
            return os.path.join(self.cards_dir, f"{card_id}.json")
        return os.path.join("app", "data", "debate", "cards", f"{card_id}.json")

    def _get_all_card_files(self) -> list[str]:
        """Get all JSON file names (without extension) in cards directory."""
        search_dirs = []
        if self.cards_dir:
            search_dirs.append(self.cards_dir)
        search_dirs.extend([
            "app/data/debate/cards",
            os.path.join("backend", "app", "data", "debate", "cards"),
        ])

        card_ids = set()
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for filename in os.listdir(search_dir):
                    if filename.endswith(".json"):
                        card_id = filename.replace(".json", "")
                        card_ids.add(card_id)

        return list(card_ids)

    def load_card(self, card_id: str) -> DebateCard:
        """
        Load a character card by ID.

        Args:
            card_id: Card ID (e.g., "philosophical_dreamer", "pro", "con")

        Returns:
            DebateCard instance

        Raises:
            CardLoaderError: If card file not found or invalid
        """
        card_path = self._get_card_path(card_id)

        if not os.path.exists(card_path):
            raise CardLoaderError(f"Card file not found: {card_path}")

        try:
            with open(card_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CardLoaderError(f"Invalid JSON in card file: {e}")

        required_fields = ["id", "name", "description", "personality_prompt",
                         "scenario", "response_rules", "system_prompt_template",
                         "opening_statements", "tags"]

        for field in required_fields:
            if field not in data:
                raise CardLoaderError(f"Missing required field '{field}' in card: {card_path}")

        character_book_desc = data.get("character_book_description", "")
        avatar = data.get("avatar", "")
        difficulty = data.get("difficulty", 1)

        return DebateCard(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            personality=data["personality_prompt"],
            scenario=data["scenario"],
            response_rules=data["response_rules"],
            system_prompt_template=data["system_prompt_template"],
            opening_statements=data["opening_statements"],
            tags=data["tags"],
            character_book_description=character_book_desc,
            avatar=avatar,
            difficulty=difficulty,
        )

    def list_cards(self) -> list[dict]:
        """
        List all available card summaries (basic info only).

        Returns:
            List of card summaries with: id, name, avatar, difficulty, description
        """
        cards = []
        for card_id in self._get_all_card_files():
            try:
                card = self.load_card(card_id)
                cards.append({
                    "id": card.id,
                    "name": card.name,
                    "avatar": card.avatar if hasattr(card, 'avatar') else "",
                    "difficulty": card.difficulty if hasattr(card, 'difficulty') else 1,
                    "description": card.description,
                    "tags": card.tags,
                })
            except CardLoaderError:
                continue

        return cards


# Convenience function
def load_card(role: str) -> DebateCard:
    """
    Convenience function to load a card.
    
    Args:
        role: Role name ("pro" or "con")
    
    Returns:
        DebateCard instance
    """
    loader = CardLoader()
    return loader.load_card(role)


if __name__ == "__main__":
    # Test the card loader
    print("=== Testing Card Loader ===\n")
    
    loader = CardLoader()
    
    # List available cards
    cards = loader.list_cards()
    print(f"Available cards: {cards}\n")
    
    # Load pro card
    try:
        pro_card = loader.load_card("pro")
        print(f"Loaded pro card:")
        print(f"  ID: {pro_card.id}")
        print(f"  Name: {pro_card.name}")
        print(f"  Description: {pro_card.description}")
        print(f"  Personality: {pro_card.personality}")
        print(f"  Opening statements: {len(pro_card.opening_statements)}")
        print(f"  Tags: {pro_card.tags}")
    except CardLoaderError as e:
        print(f"Error loading pro card: {e}")
    
    # Load con card
    try:
        con_card = loader.load_card("con")
        print(f"\nLoaded con card:")
        print(f"  ID: {con_card.id}")
        print(f"  Name: {con_card.name}")
        print(f"  Description: {con_card.description}")
    except CardLoaderError as e:
        print(f"Error loading con card: {e}")
    
    # Test invalid role
    try:
        loader.load_card("invalid")
    except CardLoaderError as e:
        print(f"\nInvalid role test passed: {e}")
    
    print("\n=== All tests passed ===")
