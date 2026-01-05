"""
AdsPower API Client

Provides interface for starting/stopping browser profiles via AdsPower Local API.
"""

import requests
from typing import Optional
import time


class AdsPowerClient:
    """Client for AdsPower Local API."""
    
    def __init__(self, base_url: str = "http://localhost:50325"):
        """
        Initialize AdsPower client.
        
        Args:
            base_url: AdsPower Local API base URL
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
    
    def start_profile(self, serial_number: str, headless: bool = False) -> dict:
        """
        Start browser profile and get connection details.
        
        Args:
            serial_number: Profile serial number from AdsPower
            headless: Run browser in headless mode
            
        Returns:
            dict with 'ws_endpoint' (CDP WebSocket URL) on success
            
        Raises:
            Exception: If API call fails
        """
        url = f"{self.base_url}/api/v1/browser/start"
        params = {
            "serial_number": serial_number,
            "headless": "1" if headless else "0"
        }
        
        try:
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                ws_endpoint = data["data"]["ws"]["puppeteer"]
                return {
                    "success": True,
                    "ws_endpoint": ws_endpoint,
                    "webdriver": data["data"].get("webdriver")
                }
            else:
                error_msg = data.get("msg", "Unknown error")
                return {
                    "success": False,
                    "error": f"AdsPower API error: {error_msg}"
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    def stop_profile(self, serial_number: str) -> dict:
        """
        Stop browser profile.
        
        Args:
            serial_number: Profile serial number from AdsPower
            
        Returns:
            dict with 'success' status
        """
        url = f"{self.base_url}/api/v1/browser/stop"
        params = {"serial_number": serial_number}
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                return {"success": True}
            else:
                return {
                    "success": False,
                    "error": data.get("msg", "Unknown error")
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    def check_profile_status(self, serial_number: str) -> dict:
        """
        Check if profile browser is running.
        
        Args:
            serial_number: Profile serial number from AdsPower
            
        Returns:
            dict with 'active' status
        """
        url = f"{self.base_url}/api/v1/browser/active"
        params = {"serial_number": serial_number}
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                return {
                    "success": True,
                    "active": data["data"].get("status") == "Active"
                }
            else:
                return {"success": True, "active": False}
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    def wait_for_browser_ready(self, serial_number: str, timeout: int = 30) -> bool:
        """
        Wait for browser to be ready after starting.
        
        Args:
            serial_number: Profile serial number
            timeout: Maximum wait time in seconds
            
        Returns:
            True if browser is ready, False on timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.check_profile_status(serial_number)
            if status.get("success") and status.get("active"):
                return True
            time.sleep(1)
        return False
