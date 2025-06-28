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

import os
import sys
import glob

from utils.cli import shell
from utils.style import ansi

from logs.config import log_config
logger = log_config(__file__)

# Prompt user for GitHub username
username = input("Enter your GitHub username: ")
logger.info("GitHub username: %s", username)

# Prompt user for git repo url
git_repo_url = input("Enter git repo url: ")
logger.info("Git repo URL: %s", git_repo_url)
git_repo_url = git_repo_url.rstrip('/')

# Prompt user for git repo branch
git_repo_branch = input(f"Enter git repo branch: {ansi.grey}(default: main){ansi.reset} ")
if not git_repo_branch:
    git_repo_branch = "main"
logger.info("Git repo branch: %s", git_repo_branch)

# Prompt user for name
name = input("Enter git name: ")
logger.info("Git name: %s", name)

# Prompt user for email
email = input("Enter git email: ")
logger.info("Git email: %s", email)

# Prompt user for the folder where the repo will live
print(f"Enter the folder where you want to create the repo (e.g. {ansi.cyan}~/Documents{ansi.reset} or {ansi.cyan}C:\\Users\\YourName\\Documents{ansi.reset}): ")
repo_parent_folder = input(" > ")
repo_parent_folder = os.path.expanduser(repo_parent_folder)
logger.info("Repo parent folder: %s", repo_parent_folder)

# Process the git_repo_url to get the organization/repo_name
organization, repo_name = git_repo_url.split('/')[-2:]
logger.info("Organization: %s, Repo name: %s", organization, repo_name)

if username != organization:
    # Check if the user has permissions for the repo
    repo_permissions = input(f"Do you have permissions as {ansi.cyan}{username}{ansi.reset} to access the {ansi.red}{organization}{ansi.reset} repo? (y/n): ")
    logger.info("User repo_permissions: %s", repo_permissions)
    if repo_permissions.lower() not in ["y", "yes"]:
        logger.warning("Repo permissions: %s", repo_permissions)
        print("Please ask the repo owner to add you as a collaborator and try again.")
        exit(1)

# Change directory and create repo folder
repo_path = os.path.join(repo_parent_folder, repo_name)
os.makedirs(repo_path, exist_ok=True)
os.chdir(repo_path)
logger.info("Changed directory to: %s", repo_path)

# Initialize git and configure user
shell.execute("git init")
shell.execute(f'git config user.name "{name}"')
shell.execute(f'git config user.email {email}')
logger.info('Git configured with name: "%s" and email: %s', name, email)

# Print all public SSH keys in ~/.ssh folder
ssh_folder = os.path.expanduser("~/.ssh")
public_keys = glob.glob(os.path.join(ssh_folder, "*.pub"))

if public_keys:
    print(f"Select the SSH public key for this account (e.g. {ansi.grey}id_ed25519_machine_{ansi.reset}{ansi.magenta}{username}{ansi.reset}.pub): ")
    default_key = next((key for key in public_keys if username.lower() in os.path.basename(key).lower()), None)
    for i, key in enumerate(public_keys, 1):
        is_default = key == default_key
        print(f"{ansi.yellow}{i}.{ansi.reset} {os.path.basename(key)}{' (default)' if is_default else ''}")
    selection = input(f"Select a key number or enter a custom path {ansi.grey}(default: {os.path.basename(default_key) if default_key else 'None'}){ansi.reset}: ")
    if not selection and default_key:
        ssh_key = default_key
    elif selection.isdigit() and 1 <= int(selection) <= len(public_keys):
        ssh_key = public_keys[int(selection) - 1]
    elif os.path.exists(os.path.expanduser(selection)):
        ssh_key = os.path.expanduser(selection)
    else:
        print("Invalid selection. Make sure SSH keys are in the ~/.ssh folder.")
        exit(1)
    ssh_key = f"~/.ssh/{os.path.basename(ssh_key)}"
else:
    print("No public SSH keys found in ~/.ssh folder.")
    print(f"Enter the path to the SSH public key for this account (e.g. {ansi.blue}~/.ssh/id_ed25519_machine_{ansi.reset}{ansi.magenta}{username}{ansi.reset}.pub): ")
    ssh_key = input(" > ")
    ssh_key = f"~/.ssh/{os.path.basename(ssh_key)}"

logger.info('SSH key path: "%s"', ssh_key)

# Prompt user for SSH host
print(f"Enter the SSH host for GitHub: {ansi.grey}(default: {username}.github.com){ansi.reset}")
ssh_host = input(f"{ansi.grey} > {ansi.reset}") or f"{username}.github.com"
logger.info("SSH host: %s", ssh_host)

# Check if the user has added their SSH key to GitHub
key_added = input(f"Have you added your SSH key to GitHub? {ansi.yellow}This is the last step.{ansi.reset} (y/n): ")
logger.info("User key_added: %s", key_added)
if key_added.lower() not in ["y", "yes"]:
    print("Please add your SSH key to GitHub and try again")
    exit(1)

# Update git config for SSH key
shell.execute(f'git config user.signingkey "{ssh_key}"')
shell.execute("git config gpg.format ssh")
shell.execute("git config commit.gpgsign true")
shell.execute("git config pull.rebase true")

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
shell.execute(f"ssh -T git@{ssh_host}")

# Set up remote and fetch
shell.execute(f"git remote add origin git@{ssh_host}:{organization}/{repo_name}.git")
shell.execute("git fetch origin")

# Checkout branch and pull
shell.execute(f"git checkout -b {git_repo_branch} origin/{git_repo_branch}")
update = shell.execute("git pull")

if "error" in update[1].lower():
    logger.warning("Error pulling from remote")
    print(f"{ansi.red}Error pulling from remote{ansi.reset}")
    sys.exit(1)

logger.info("Repository setup complete")
print(f"{ansi.green}Repository setup complete!{ansi.reset}")
