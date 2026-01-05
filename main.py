"""
Zashapon Testnet Automation

Main entry point for the automation software.
Processes AdsPower profiles with multithreading support.
"""

import yaml
import sys
import signal
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict

from adspower_client import AdsPowerClient
from sheets_manager import SheetsManager
from game_logic import process_profile_safe, shutdown_flag


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n[!] Получен сигнал остановки (Ctrl+C). Завершаем работу...")
    shutdown_flag.set()



def main():
    """Main entry point."""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 50)
    print("Zashapon Testnet Automation")
    print("=" * 50)
    print("[i] Нажмите Ctrl+C для остановки")
    
    # Load configuration
    try:
        config = load_config()
        print("[✓] Configuration loaded")
    except Exception as e:
        print(f"[✗] Failed to load config: {e}")
        sys.exit(1)
    
    # Initialize AdsPower client
    adspower_config = config.get("adspower", {})
    adspower_client = AdsPowerClient(
        base_url=adspower_config.get("base_url", "http://localhost:50325")
    )
    print("[✓] AdsPower client initialized")
    
    # Initialize Google Sheets manager
    try:
        sheets_config = config.get("google_sheets", {})
        sheets_manager = SheetsManager(
            credentials_file=sheets_config.get("credentials_file", "service_account.json"),
            spreadsheet_id=sheets_config.get("spreadsheet_id"),
            sheet_name=sheets_config.get("sheet_name", "Sheet1"),
            columns_config=sheets_config.get("columns", {}),
            data_start_row=sheets_config.get("data_start_row", 2)
        )
        print("[✓] Google Sheets manager initialized")
    except Exception as e:
        print(f"[✗] Failed to initialize Google Sheets: {e}")
        sys.exit(1)
    
    # Get profile numbers from sheet
    try:
        profile_numbers = sheets_manager.get_profile_numbers()
        print(f"[✓] Found {len(profile_numbers)} profiles to process")
        
        if not profile_numbers:
            print("[!] No profiles found in sheet")
            sys.exit(0)
    except Exception as e:
        print(f"[✗] Failed to get profiles: {e}")
        sys.exit(1)
    
    # Threading configuration
    threading_config = config.get("threading", {})
    max_workers = threading_config.get("max_workers", 3)
    
    # Game configuration
    game_config = config.get("game", {})
    
    print(f"\n[→] Starting processing with {max_workers} workers...")
    print("-" * 50)
    
    # Process profiles with thread pool
    results: Dict[str, dict] = {}
    executor = ThreadPoolExecutor(max_workers=max_workers)
    futures = {}
    
    try:
        # Submit all tasks
        for serial_number in profile_numbers:
            if shutdown_flag.is_set():
                print("[!] Shutdown requested, skipping remaining profiles...")
                break
            future = executor.submit(
                process_profile_safe,
                serial_number,
                adspower_client,
                game_config
            )
            futures[future] = serial_number
        
        # Process completed tasks
        for future in as_completed(futures):
            # Check for shutdown before processing result
            if shutdown_flag.is_set():
                print("[!] Shutdown requested, canceling pending tasks...")
                # Cancel all pending futures
                for f in futures:
                    f.cancel()
                break
            
            serial_number = futures[future]
            
            try:
                result_serial, success, cards, status = future.result(timeout=1)
                results[result_serial] = {
                    "success": success,
                    "cards": cards,
                    "status": status
                }
                
                status_icon = "✓" if success else "✗"
                print(f"[{status_icon}] {result_serial}: {status}")
                
                # Update Google Sheets immediately
                try:
                    if success:
                        sheets_manager.update_collection(result_serial, cards)
                    sheets_manager.update_status(result_serial, status)
                except Exception as e:
                    print(f"[!] Failed to update sheet for {result_serial}: {e}")
                    
            except Exception as e:
                print(f"[✗] {serial_number}: Exception - {e}")
                results[serial_number] = {
                    "success": False,
                    "cards": {},
                    "status": f"Exception: {e}"
                }
    
    except KeyboardInterrupt:
        print("\n[!] KeyboardInterrupt received, stopping...")
        shutdown_flag.set()
    
    finally:
        # Shutdown executor - cancel pending, don't wait
        print("[i] Shutting down executor...")
        executor.shutdown(wait=False, cancel_futures=True)
    
    # Summary
    print("-" * 50)
    success_count = sum(1 for r in results.values() if r["success"])
    print(f"\n[✓] Processing complete: {success_count}/{len(results)} successful")
    
    # Print failed profiles
    failed = [sn for sn, r in results.items() if not r["success"]]
    if failed:
        print(f"[!] Failed profiles: {', '.join(failed)}")


if __name__ == "__main__":
    main()

