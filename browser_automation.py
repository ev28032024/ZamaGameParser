"""
Browser Automation Module

Handles browser automation using Patchright with AdsPower CDP connection.
"""

from patchright.sync_api import sync_playwright, Page, Browser, BrowserContext
from typing import Optional, Dict
import re


class BrowserAutomation:
    """Browser automation for Zashapon game."""
    
    def __init__(self, config: dict):
        """
        Initialize browser automation.
        
        Args:
            config: Game configuration from config.yaml
        """
        self.config = config
        self.base_url = config.get("base_url", "https://www.zashapon.com/")
        self.collection_url = config.get("collection_url", "https://zashapon.com/collection")
        self.page_load_timeout = config.get("page_load_timeout", 60000)
        self.element_wait_timeout = config.get("element_wait_timeout", 30000)
        self.animation_max_wait = config.get("animation_max_wait", 120)
        
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
    
    def connect(self, cdp_endpoint: str) -> bool:
        """
        Connect to AdsPower browser via CDP.
        
        Args:
            cdp_endpoint: WebSocket URL from AdsPower API
            
        Returns:
            True if connection successful
        """
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.connect_over_cdp(cdp_endpoint)
            
            # Get existing context (AdsPower profile)
            contexts = self._browser.contexts
            if contexts:
                self._context = contexts[0]
            else:
                self._context = self._browser.new_context()
            
            # Get or create page
            pages = self._context.pages
            if pages:
                self._page = pages[0]
            else:
                self._page = self._context.new_page()
            
            return True
            
        except Exception as e:
            print(f"Failed to connect to browser: {e}")
            return False
    
    def close(self):
        """Close browser connection."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        finally:
            self._browser = None
            self._context = None
            self._page = None
            self._playwright = None
    
    def navigate_to_game(self) -> bool:
        """
        Navigate to the game page and wait for it to load.
        
        Returns:
            True if navigation successful
        """
        if not self._page:
            return False
        
        try:
            self._page.goto(
                self.base_url, 
                wait_until="networkidle",
                timeout=self.page_load_timeout
            )
            # Additional wait for dynamic content
            self._page.wait_for_timeout(2000)
            return True
            
        except Exception as e:
            print(f"Navigation failed: {e}")
            return False
    
    def get_ticket_count(self) -> int:
        """
        Get the current number of tickets.
        
        Returns:
            Number of tickets, 0 if not found or error
        """
        if not self._page:
            return 0
        
        try:
            # Wait for ticket element to be visible
            ticket_locator = self._page.locator("a[aria-label='Ticket'] span").first
            ticket_locator.wait_for(state="visible", timeout=self.element_wait_timeout)
            
            ticket_text = ticket_locator.inner_text()
            ticket_count = int(ticket_text.strip())
            return ticket_count
            
        except Exception as e:
            print(f"Could not get ticket count: {e}")
            return 0
    
    def is_play_button_visible(self) -> bool:
        """Check if Play button is visible and enabled."""
        if not self._page:
            return False
        
        try:
            play_button = self._page.locator("button:has-text('PLAY')")
            return play_button.is_visible() and play_button.is_enabled()
        except Exception:
            return False
    
    def click_play(self) -> bool:
        """
        Click the Play button.
        
        Returns:
            True if click successful
        """
        if not self._page:
            return False
        
        try:
            play_button = self._page.locator("button:has-text('PLAY')")
            play_button.wait_for(state="visible", timeout=self.element_wait_timeout)
            play_button.click()
            return True
            
        except Exception as e:
            print(f"Failed to click Play: {e}")
            return False
    
    def wait_for_add_to_collection(self) -> bool:
        """
        Wait for game animation to complete and "Add to collection" button to appear.
        
        Returns:
            True if button appeared, False on timeout
        """
        if not self._page:
            return False
        
        try:
            # Wait for "Add to collection" button to appear
            add_button = self._page.locator("button:has-text('Add to collection')")
            add_button.wait_for(
                state="visible", 
                timeout=self.animation_max_wait * 1000
            )
            return True
            
        except Exception as e:
            print(f"Add to collection button not found: {e}")
            return False
    
    def click_add_to_collection(self) -> bool:
        """
        Click the "Add to collection" button.
        
        Returns:
            True if click successful
        """
        if not self._page:
            return False
        
        try:
            add_button = self._page.locator("button:has-text('Add to collection')")
            add_button.wait_for(state="visible", timeout=self.element_wait_timeout)
            add_button.click()
            
            # Wait for animation after adding to collection
            self._page.wait_for_timeout(2000)
            return True
            
        except Exception as e:
            print(f"Failed to click Add to collection: {e}")
            return False
    
    def play_game_once(self) -> bool:
        """
        Play one round of the game (Play -> wait -> Add to collection).
        
        Returns:
            True if round completed successfully
        """
        if not self.click_play():
            return False
        
        if not self.wait_for_add_to_collection():
            return False
        
        if not self.click_add_to_collection():
            return False
        
        return True
    
    def navigate_to_collection(self) -> bool:
        """
        Navigate to the collection page.
        
        Returns:
            True if navigation successful
        """
        if not self._page:
            return False
        
        try:
            self._page.goto(
                self.collection_url,
                wait_until="networkidle",
                timeout=self.page_load_timeout
            )
            # Wait for collection cards to load
            self._page.wait_for_timeout(3000)
            return True
            
        except Exception as e:
            print(f"Navigation to collection failed: {e}")
            return False
    
    def get_collection_cards(self) -> Dict[str, bool]:
        """
        Parse collection page and determine which cards are owned.
        
        Cards with "xN" badge are owned, cards without are not.
        
        Returns:
            Dict mapping card name to ownership status
        """
        if not self._page:
            return {}
        
        cards = {
            "Daruma Zama": False,
            "Daruma Monk": False,
            "Daruma Wave": False,
            "Daruma Devil": False,
            "Daruma Fox": False,
            "Daruma Lantern": False,
            "Daruma Cat": False,
            "Daruma Kumo": False,
            "Daruma Sakura": False
        }
        
        try:
            # Find all card containers
            card_containers = self._page.locator("div.rounded-lg.text-card-foreground")
            count = card_containers.count()
            
            for i in range(count):
                card = card_containers.nth(i)
                
                try:
                    # Get card title
                    title_element = card.locator("h3")
                    if not title_element.count():
                        continue
                    
                    card_title = title_element.first.inner_text().strip()
                    
                    if card_title not in cards:
                        continue
                    
                    # Check for "xN" badge (indicates ownership)
                    # Badge contains text like "x1", "x2", etc.
                    badge_locator = card.locator("span[data-slot='badge']")
                    badge_count = badge_locator.count()
                    
                    for j in range(badge_count):
                        badge = badge_locator.nth(j)
                        badge_text = badge.inner_text().strip()
                        
                        # Check if badge matches pattern "xN" (e.g., x1, x2, x10)
                        if re.match(r'^x\d+$', badge_text, re.IGNORECASE):
                            cards[card_title] = True
                            break
                            
                except Exception:
                    continue
            
            return cards
            
        except Exception as e:
            print(f"Failed to parse collection: {e}")
            return cards
    
    @property
    def page(self) -> Optional[Page]:
        """Get current page object."""
        return self._page
