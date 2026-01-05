"""
Google Sheets Manager

Handles reading profile numbers and writing collection data to Google Sheets.
Uses gspread with service account authentication.
"""

import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional


class SheetsManager:
    """Manager for Google Sheets operations."""
    
    # Required OAuth scopes for Google Sheets and Drive
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    def __init__(self, credentials_file: str, spreadsheet_id: str, sheet_name: str, columns_config: dict, data_start_row: int = 2):
        """
        Initialize Sheets manager.
        
        Args:
            credentials_file: Path to service account JSON credentials
            spreadsheet_id: Google Spreadsheet ID
            sheet_name: Name of the sheet to use
            columns_config: Dict mapping column names to column letters
            data_start_row: First row with data (after headers)
        """
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.columns_config = columns_config
        self.data_start_row = data_start_row
        
        # Authenticate and open spreadsheet
        credentials = Credentials.from_service_account_file(
            credentials_file, 
            scopes=self.SCOPES
        )
        self.client = gspread.authorize(credentials)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        self.worksheet = self.spreadsheet.worksheet(sheet_name)
        
        # Cache profile row mapping
        self._profile_row_cache: Dict[str, int] = {}
        self._refresh_profile_cache()
    
    def _column_letter_to_index(self, letter: str) -> int:
        """Convert column letter (A, B, AA, etc.) to 1-based index."""
        result = 0
        for char in letter.upper():
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result
    
    def _refresh_profile_cache(self):
        """Refresh cache of profile serial_numbers to row numbers."""
        self._profile_row_cache.clear()
        
        serial_col = self.columns_config.get("serial_number", "A")
        col_index = self._column_letter_to_index(serial_col)
        
        # Get all values from serial_number column
        all_values = self.worksheet.col_values(col_index)
        
        # Map serial_number to row (skip header, start from data_start_row)
        for i, value in enumerate(all_values):
            row_num = i + 1  # 1-based row index
            if row_num >= self.data_start_row and value:
                self._profile_row_cache[str(value).strip()] = row_num
    
    def get_profile_numbers(self) -> List[str]:
        """
        Get list of profile serial_numbers from the sheet.
        
        Returns:
            List of serial_number strings
        """
        # Refresh cache to get latest data
        self._refresh_profile_cache()
        return list(self._profile_row_cache.keys())
    
    def get_row_for_profile(self, serial_number: str) -> Optional[int]:
        """
        Get row number for a profile serial_number.
        
        Args:
            serial_number: Profile serial number
            
        Returns:
            Row number (1-based) or None if not found
        """
        serial_str = str(serial_number).strip()
        
        if serial_str not in self._profile_row_cache:
            # Refresh cache and try again
            self._refresh_profile_cache()
        
        return self._profile_row_cache.get(serial_str)
    
    def update_collection(self, serial_number: str, cards: Dict[str, bool]) -> bool:
        """
        Update collection data for a profile.
        
        Writes "ok" for cards that are present, leaves empty for missing.
        
        Args:
            serial_number: Profile serial number
            cards: Dict mapping card names to presence (True = has card)
            
        Returns:
            True if update successful, False otherwise
        """
        row = self.get_row_for_profile(serial_number)
        if row is None:
            return False
        
        # Card name to column key mapping
        card_column_map = {
            "Daruma Zama": "daruma_zama",
            "Daruma Monk": "daruma_monk",
            "Daruma Wave": "daruma_wave",
            "Daruma Devil": "daruma_devil",
            "Daruma Fox": "daruma_fox",
            "Daruma Lantern": "daruma_lantern",
            "Daruma Cat": "daruma_cat",
            "Daruma Kumo": "daruma_kumo",
            "Daruma Sakura": "daruma_sakura"
        }
        
        # Build list of cell updates
        updates = []
        for card_name, has_card in cards.items():
            column_key = card_column_map.get(card_name)
            if column_key and column_key in self.columns_config:
                col_letter = self.columns_config[column_key]
                cell = f"{col_letter}{row}"
                value = "ok" if has_card else ""
                updates.append({"range": cell, "values": [[value]]})
        
        if updates:
            # Batch update for efficiency
            self.worksheet.batch_update(updates)
        
        return True
    
    def update_status(self, serial_number: str, status: str) -> bool:
        """
        Update status/error column for a profile.
        
        Args:
            serial_number: Profile serial number
            status: Status message to write
            
        Returns:
            True if update successful, False otherwise
        """
        row = self.get_row_for_profile(serial_number)
        if row is None:
            return False
        
        status_col = self.columns_config.get("status_error", "N")
        cell = f"{status_col}{row}"
        
        self.worksheet.update_acell(cell, status)
        return True
    
    def batch_update_collections(self, results: Dict[str, Dict[str, bool]]) -> int:
        """
        Batch update collections for multiple profiles.
        
        Args:
            results: Dict mapping serial_number to cards dict
            
        Returns:
            Number of profiles successfully updated
        """
        success_count = 0
        for serial_number, cards in results.items():
            if self.update_collection(serial_number, cards):
                success_count += 1
        return success_count
