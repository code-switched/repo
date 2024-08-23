"""
This script will be a step by step guide to giving the user access to an existing private repo
It will assume the user does not have the gh-cli tool installed 
The permissions will be setup to allow the user to push to the repo
The logs directory and the style directory must be set up with the proper config files
Requirements:
- git
- ed25519 ssh key set up
- ssh key added to GitHub account
- added as collaborator to the repo
"""

from utils.style import ansi
from utils.cli import shell
import os
import glob

import logging
from logs.config import log_config
log_config(__file__)

# Check if the user has permissions for the repo
repo_permissions = input("Do you have permissions to access the repo? (y/n): ")
logging.info(f"User repo_permissions: {repo_permissions}")
if repo_permissions.lower() not in ["y", "yes"]:
    logging.warning("User does not have permissions for the repo")
    print("Please ask the repo owner to add you as a collaborator and try again")
    exit(1)

# Prompt user for git repo url
git_repo_url = input("Enter git repo url: ")
logging.info(f"Git repo URL: {git_repo_url}")

# Prompt user for git repo branch
git_repo_branch = input(f"Enter git repo branch: {ansi.grey}(default: main){ansi.reset} ")
if not git_repo_branch:
    git_repo_branch = "main"
logging.info(f"Git repo branch: {git_repo_branch}")

# Prompt user for name
name = input("Enter git name: ")
logging.info(f"Git name: {name}")

# Prompt user for email
email = input("Enter git email: ")
logging.info(f"Git email: {email}")

# Prompt user for the folder where the repo will live
print(f"Enter the folder where you want to create the repo (e.g. {ansi.blue}~/Documents{ansi.reset} or {ansi.blue}C:\\Users\\YourName\\Documents{ansi.reset}): ")
repo_parent_folder = input(" > ")
repo_parent_folder = os.path.expanduser(repo_parent_folder)
logging.info(f"Repo parent folder: {repo_parent_folder}")

# Process the git_repo_url to get the username/repo_name
username, repo_name = git_repo_url.split('/')[-2:]
logging.info(f"Username: {username}, Repo name: {repo_name}")

# Change directory and create repo folder
repo_path = os.path.join(repo_parent_folder, repo_name)
os.makedirs(repo_path, exist_ok=True)
os.chdir(repo_path)
logging.info(f"Changed directory to: {repo_path}")

# Initialize git and configure user
shell.run("git init")
shell.run(f'git config user.name "{name}"')
shell.run(f'git config user.email {email}')
logging.info(f'Git configured with name: "{name}" and email: {email}')

# Print all public SSH keys in ~/.ssh folder
ssh_folder = os.path.expanduser("~/.ssh")
public_keys = glob.glob(os.path.join(ssh_folder, "*.pub"))

if public_keys:
    print(f"Select the SSH public key for this account (e.g. {ansi.blue}id_ed25519_machine_{ansi.reset}{ansi.magenta}{username}{ansi.reset}.pub): ")
    default_key = next((key for key in public_keys if username in os.path.basename(key)), None)
    for i, key in enumerate(public_keys, 1):
        is_default = key == default_key
        print(f"{ansi.yellow}{i}.{ansi.reset} {os.path.basename(key)}{' (default)' if is_default else ''}")
    selection = input(f"Select a key number or enter a custom path {ansi.grey}(default: {os.path.basename(default_key) if default_key else 'None'}){ansi.reset}: ")
    if not selection and default_key:
        ssh_key = default_key
    elif selection.isdigit() and 1 <= int(selection) <= len(public_keys):
        ssh_key = public_keys[int(selection) - 1]
    elif os.path.exists(selection):
        ssh_key = selection
    else:
        print("Invalid selection. Make sure SSH keys are in the ~/.ssh folder.")
        exit(1)
    ssh_key = f"~/.ssh/{os.path.basename(ssh_key)}"
else:
    print("No public SSH keys found in ~/.ssh folder.")
    print(f"Enter the path to the SSH public key for this account (e.g. {ansi.blue}~/.ssh/id_ed25519_machine_{ansi.reset}{ansi.magenta}{username}{ansi.reset}.pub): ")
    ssh_key = input(" > ")
    ssh_key = f"~/.ssh/{os.path.basename(ssh_key)}"

logging.info(f'SSH key path: "{ssh_key}"')

# Prompt user for SSH host
print(f"Enter the SSH host for GitHub: {ansi.grey}(default: {username}.github.com){ansi.reset}")
ssh_host = input(f"{ansi.grey} > {ansi.reset}") or f"{username}.github.com"
logging.info(f"SSH host: {ssh_host}")

# Check if the user has added their SSH key to GitHub
key_added = input("Have you added your SSH key to GitHub? This is the last step. (y/n): ")
logging.info(f"User key_added: {key_added}")
if key_added.lower() not in ["y", "yes"]:
    print("Please add your SSH key to GitHub and try again")
    exit(1)

# Update git config for SSH key
shell.run(f'git config user.signingkey "{ssh_key}"')
shell.run("git config gpg.format ssh")
shell.run("git config commit.gpgsign true")

# Print instructions for commit signing
print("Add commit signing to any VSCodium based editor by adding the following to settings.json:")
print(f"{ansi.cyan}")
print('{')
print('    "git.enableCommitSigning": true')
print('}')
print(f"{ansi.reset}")
print(f"Alternatively, press {ansi.yellow}Cmd/Ctrl + Shift + P{ansi.reset}, search for {ansi.yellow}\"Preferences: Open Settings (UI)\"{ansi.reset}")
print(f"Under User Settings, search {ansi.yellow}\"Enable Commit Signing\"{ansi.reset} and turn it on")

# Test SSH connection
shell.run(f"ssh -T git@{ssh_host}")

# Set up remote and fetch
shell.run(f"git remote add origin git@{ssh_host}:{username}/{repo_name}.git")
shell.run("git fetch origin")

# Checkout branch and pull
shell.run(f"git checkout -b {git_repo_branch} origin/{git_repo_branch}")
update = shell.run("git pull")

if "error" in update[1].lower():
    logging.warning("Error pulling from remote")
    print(f"{ansi.red}Error pulling from remote{ansi.reset}")
    exit(1)

logging.info("Repository setup complete")
print(f"{ansi.green}Repository setup complete!{ansi.reset}")