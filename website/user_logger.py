# FILE: website/user_logger.py
import os
import glob
from datetime import datetime, timezone

# Create a 'user_logs' directory in the root of your project
LOGS_DIR = os.path.join(os.getcwd(), 'user_logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

def get_log_filename(username):
    """Finds the existing log file for the exact username."""
    files = glob.glob(os.path.join(LOGS_DIR, "*_log.txt"))
    for f in files:
        basename = os.path.basename(f)
        prefix = basename[:-8] # remove '_log.txt'
        
        if '_' in prefix:
            parts = prefix.rsplit('_', 1)
            if parts[0] == username:
                return f
    return None

def log_user_action(username, action, details=""):
    """Logs an action, creating the file if it doesn't exist."""
    if not username:
        return
        
    timestamp_now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    file_path = get_log_filename(username)
    
    if not file_path:
        file_timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        file_path = os.path.join(LOGS_DIR, f"{username}_{file_timestamp}_log.txt")
    
    log_entry = f"[{timestamp_now}] | ACTION: {action} | DETAILS: {details}\n"
    
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write log for {username}: {e}")

def rename_user_log(old_username, new_username):
    """Renames the log file when a user changes their username."""
    old_file = get_log_filename(old_username)
    if old_file:
        basename = os.path.basename(old_file)
        prefix = basename[:-8]
        parts = prefix.rsplit('_', 1)
        
        if len(parts) == 2:
            timestamp_part = parts[1]
            new_filename = f"{new_username}_{timestamp_part}_log.txt"
            new_file_path = os.path.join(LOGS_DIR, new_filename)
            try:
                os.rename(old_file, new_file_path)
                log_user_action(new_username, "USERNAME_UPDATE", f"Changed from {old_username} to {new_username}")
            except Exception as e:
                print(f"Failed to rename log file: {e}")

# 🚀 NEW: Log Cleanup Function
def cleanup_old_logs(max_lines=500):
    """
    Trims all log files to keep only the most recent 'max_lines'.
    Prevents infinite file growth on the server.
    """
    files = glob.glob(os.path.join(LOGS_DIR, "*_log.txt"))
    cleaned_count = 0
    
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # If the file is getting too long, slice it!
            if len(lines) > max_lines:
                with open(f, 'w', encoding='utf-8') as file:
                    # Write back only the last N lines
                    file.writelines(lines[-max_lines:])
                cleaned_count += 1
        except Exception as e:
            print(f"Error cleaning {f}: {e}")
            
    return cleaned_count