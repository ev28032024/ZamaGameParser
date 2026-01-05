"""
Game Logic Module

Contains the main game automation logic for processing a single profile.
"""

import threading
from typing import Dict, Tuple
from adspower_client import AdsPowerClient
from browser_automation import BrowserAutomation
import time

# Global shutdown flag for graceful termination
shutdown_flag = threading.Event()


def process_profile(
    serial_number: str,
    adspower_client: AdsPowerClient,
    game_config: dict
) -> Tuple[bool, Dict[str, bool], str]:
    """
    Process a single AdsPower profile.
    
    Steps:
    1. Start AdsPower profile
    2. Connect Patchright via CDP
    3. Navigate to game
    4. Play game until tickets exhausted
    5. Navigate to collection
    6. Parse owned cards
    7. Close browser
    
    Args:
        serial_number: AdsPower profile serial number
        adspower_client: AdsPower API client
        game_config: Game configuration dict
        
    Returns:
        Tuple of (success, cards_dict, status_message)
    """
    automation = None
    cards = {}
    
    try:
        # Step 1: Start AdsPower profile
        print(f"[{serial_number}] Starting AdsPower profile...")
        result = adspower_client.start_profile(serial_number)
        
        if not result.get("success"):
            error_msg = result.get("error", "Failed to start profile")
            return False, {}, f"AdsPower error: {error_msg}"
        
        cdp_endpoint = result["ws_endpoint"]
        print(f"[{serial_number}] CDP endpoint: {cdp_endpoint}")
        
        # Wait for browser to be ready
        time.sleep(3)
        
        # Step 2: Connect Patchright
        print(f"[{serial_number}] Connecting Patchright...")
        automation = BrowserAutomation(game_config)
        
        if not automation.connect(cdp_endpoint):
            return False, {}, "Failed to connect Patchright to browser"
        
        # Step 3: Navigate to game
        print(f"[{serial_number}] Navigating to game...")
        if not automation.navigate_to_game():
            return False, {}, "Failed to navigate to game page"
        
        # Step 4: Check tickets and play
        ticket_count = automation.get_ticket_count()
        print(f"[{serial_number}] Tickets: {ticket_count}")
        
        games_played = 0
        while ticket_count > 0 and not shutdown_flag.is_set():
            print(f"[{serial_number}] Playing game (tickets remaining: {ticket_count})...")
            
            if not automation.play_game_once():
                print(f"[{serial_number}] Game round failed, stopping...")
                break
            
            games_played += 1
            
            # Check for shutdown
            if shutdown_flag.is_set():
                print(f"[{serial_number}] Shutdown requested, stopping...")
                break
            
            # Navigate back to main page for next game
            if not automation.navigate_to_game():
                break
            
            # Get updated ticket count
            ticket_count = automation.get_ticket_count()
        
        print(f"[{serial_number}] Played {games_played} games")
        
        # Step 5: Navigate to collection
        print(f"[{serial_number}] Navigating to collection...")
        if not automation.navigate_to_collection():
            return False, {}, "Failed to navigate to collection page"
        
        # Step 6: Parse collection
        print(f"[{serial_number}] Parsing collection...")
        cards = automation.get_collection_cards()
        
        owned_cards = [name for name, owned in cards.items() if owned]
        print(f"[{serial_number}] Owned cards: {owned_cards}")
        
        return True, cards, f"Success: played {games_played} games"
        
    except Exception as e:
        error_msg = str(e)
        print(f"[{serial_number}] Error: {error_msg}")
        return False, cards, f"Error: {error_msg}"
        
    finally:
        # Step 7: Cleanup
        if automation:
            automation.close()
        
        # Stop AdsPower profile
        try:
            adspower_client.stop_profile(serial_number)
            print(f"[{serial_number}] Profile stopped")
        except Exception:
            pass


def process_profile_safe(
    serial_number: str,
    adspower_client: AdsPowerClient,
    game_config: dict
) -> Tuple[str, bool, Dict[str, bool], str]:
    """
    Safe wrapper for process_profile that catches all exceptions.
    
    Returns serial_number as first element for easy result mapping.
    
    Args:
        serial_number: AdsPower profile serial number
        adspower_client: AdsPower API client
        game_config: Game configuration dict
        
    Returns:
        Tuple of (serial_number, success, cards_dict, status_message)
    """
    try:
        success, cards, status = process_profile(
            serial_number, adspower_client, game_config
        )
        return serial_number, success, cards, status
    except Exception as e:
        return serial_number, False, {}, f"Unexpected error: {str(e)}"
