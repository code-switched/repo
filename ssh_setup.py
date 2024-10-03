"""
This script guides the user through the process of setting up SSH keys for GitHub authentication for new machines.
It handles both generating new SSH keys and using existing ones, updates the SSH config file,
and tests the connection to GitHub.

Requirements:
- ssh-keygen
- git
- GitHub account

The script will:
1. Check for existing SSH keys
2. Generate a new key or use an existing one
3. Update the SSH config file
4. Guide the user to add the public key to their GitHub account
5. Test the SSH connection to GitHub

Note: This script assumes the user has a GitHub account and basic understanding of SSH keys.
"""

import getpass
import socket
import os
import re
import glob
from utils.style import ansi
from utils.cli import shell

from logs.config import log_config
logger = log_config(__file__)

def generate_ssh_key():
    """Generate a new SSH key"""
    print("\nGenerating a new SSH key...")
    account_name = input("Enter your git account name (e.g., personal, user_name): ")
    user = getpass.getuser()
    hostname = socket.gethostname().replace('.local', '')
    user_hostname = f"{user}@{hostname}.local"
    email = input(f"Enter your email: {ansi.grey}(default: {user_hostname}){ansi.reset} ")
    if not email:
        email = user_hostname
    default_machine_name = re.sub(r'[^a-z0-9]', '', hostname.lower())
    machine_name = input(f"Enter your machine name (e.g., desktop, laptop): {ansi.grey}(default: {default_machine_name}){ansi.reset} ")
    if not machine_name:
        machine_name = default_machine_name
    
    key_name = f"id_ed25519_{machine_name}_{account_name}"
    key_path = os.path.expanduser(f"~/.ssh/{key_name}")
    
    shell.execute(f'ssh-keygen -t ed25519 -f {key_path} -C "{email}" -N ""')
    logger.info(f"Generated new SSH key: {key_path}")
    
    return key_path, account_name, email

def update_ssh_config(key_path, account_name, email):
    """Update SSH config file"""
    config_path = os.path.expanduser("~/.ssh/config")
    host = f"{account_name}.github.com"
    
    config_entry = f"""
Host {host}
  HostName github.com
  PreferredAuthentications publickey
  IdentityFile ~/.ssh/{os.path.basename(key_path)}

## Commands
  ### cd ~/.ssh
  ### ssh-keygen -t ed25519 -f {key_path} -C "{email}" -N '""'
  ### cat {key_path}.pub
  ### ssh -T git@{host}
  ### git clone git@{host}:username/repo.git
"""
    
    with open(config_path, "a") as f:
        f.write(config_entry)
    
    logger.info(f"Updated SSH config for {host}")

def test_github_connection(account_name):
    """Test SSH connection to GitHub"""
    host = f"{account_name}.github.com"
    result = shell.execute(f"ssh -T git@{host}")
    if "successfully authenticated" in result[1]:
        logger.info(f"Successfully authenticated with {host}")
        return True
    logger.warning(f"Failed to authenticate with {host}")
    return False

def handle_existing_keys(public_keys):
    print("Existing SSH keys found:")
    for i, key in enumerate(public_keys, 1):
        print(f"{ansi.yellow}{i}.{ansi.reset} {os.path.basename(key)}")
    
    if input("Do you want to make a new key? (y/n): ").lower() == 'y':
        return generate_ssh_key()

    selection = input("Enter the number of the key you want to use: ")
    if selection.isdigit() and 1 <= int(selection) <= len(public_keys):
        key_path = public_keys[int(selection) - 1]
        return process_selected_key(key_path.replace('.pub', ''))
    else:
        print("Invalid selection. Exiting.")
        exit(1)

def process_selected_key(key_path):
    account_name = re.search(r"id_ed25519_\w+_(\w+)", key_path)
    if account_name:
        return key_path, account_name.group(1), None

    account_name = input("Enter your GitHub account name: ")
    user_hostname = f"{getpass.getuser()}@{socket.gethostname().rstrip('.local')}.local"
    email = input(f"Enter your ssh key email: {ansi.grey}(default: {user_hostname}){ansi.reset} ") or user_hostname
    return key_path, account_name, email

def main():
    logger.info("Starting SSH setup verification")
    
    # Check for existing keys
    ssh_folder = os.path.expanduser("~/.ssh")
    public_keys = glob.glob(os.path.join(ssh_folder, "*.pub"))
    
    if public_keys:
        key_path, account_name, email = handle_existing_keys(public_keys)
    else:
        print("No existing SSH keys found. Generating a new key.")
        key_path, account_name, email = generate_ssh_key()

    # Correctly expand the tilde to the user's home directory
    key_path = os.path.expanduser(key_path)

    # Always add .pub when reading the public key
    with open(f"{key_path}.pub", "r") as f:
        public_key = f.read().strip()
    
    update_ssh_config(key_path, account_name, email)
    
    print(f"\nPlease add your public key to GitHub:")
    print(f"{ansi.cyan}{public_key}{ansi.reset}")
    
    input(f"\nPress {ansi.green}Enter{ansi.reset} when you've added the key to GitHub...")
    
    if test_github_connection(account_name):
        print(f"{ansi.green}SSH setup completed successfully!{ansi.reset}")
    else:
        print(f"{ansi.red}SSH setup failed. Please check your configuration and try again.{ansi.reset}")
    
    logger.info("SSH setup completed")
    
    print(f"\n{ansi.yellow}Reminder:{ansi.reset} Please reorganize your ~/.ssh/config file as needed.")
    logger.info("Reminder: Please reorganize your ~/.ssh/config file as needed.")

if __name__ == "__main__":
    main()