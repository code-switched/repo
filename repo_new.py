"""
This script will be a step by step guide to creating a new repo and cloning it to the local machine.
It will use the gh-cli tool to create the repo and clone it to your local machine.
gh auth login will be via ssh key
Requirements:
- gh-cli
- git
- ed25519 ssh key set up
- ssh key added to GitHub account
- added as collaborator to the repo
"""
import json
import glob
import os
from utils.style import ansi
from utils.cli import shell

from logs.config import log_config
logger = log_config(__file__)

# Prompt user for the folder where the repo will live
print(f"Enter the local parent folder for the new repo (e.g. {ansi.cyan}~/Documents{ansi.reset} or {ansi.cyan}C:\\Users\\Name\\Documents{ansi.reset}): ")
repo_parent_folder = input(" > ")
repo_parent_folder = os.path.expanduser(repo_parent_folder)
logger.info("Repo parent folder: %s", repo_parent_folder)

# Change directory and create repo folder
os.makedirs(repo_parent_folder, exist_ok=True)
os.chdir(repo_parent_folder)
logger.info("Changed directory to: %s", repo_parent_folder)

# Ask the user for the repo name
repo_name = input("Enter the name of the new repo: ")
logger.info("Repo name: %s", repo_name)

# Prompt user for git repo branch
git_repo_branch = input(f"Enter git repo branch: {ansi.grey}(default: main){ansi.reset} ")
if not git_repo_branch:
    git_repo_branch = "main"
logger.info("Git repo branch: %s", git_repo_branch)

# Ask the user if this repo is for an organization or a username
repo_type = input(f"Is this repo for an organization or a user? ({ansi.cyan}user{ansi.reset} / {ansi.magenta}org{ansi.reset}): {ansi.grey}(default: user){ansi.reset} ").lower()
if not repo_type:
    repo_type = "user"
elif repo_type not in ["user", "org", "organization"]:
    logger.error("Invalid repo type input: %s", repo_type)
    print(f"{ansi.red}Invalid input.{ansi.reset} Please enter 'user' or 'org'.")
    exit(1)
logger.info("Repo type: %s", repo_type)

# Ask user if they want public or private repo
repo_visibility = input(f"Enter repo visibility ({ansi.cyan}public{ansi.reset} / {ansi.magenta}private{ansi.reset}): {ansi.grey}(default: private){ansi.reset} ").lower()
if not repo_visibility:
    repo_visibility = "private"
elif repo_visibility not in ['public', 'private']:
    logger.error("Invalid repo visibility input: %s", repo_visibility)
    print(f"{ansi.red}Invalid input.{ansi.reset} Please enter 'public' or 'private'.")
    exit(1)
logger.info("Repository visibility: %s", repo_visibility)

# Prompt user for GitHub username
username = input("Enter your GitHub username: ")
logger.info("Username: %s", username)

# Prompt user for git name
name = input("Enter git name: ")
logger.info("Git name: %s", name)

# Prompt user for git email
email = input("Enter git email: ")
logger.info("Git email: %s", email)

# Print all public SSH keys in ~/.ssh folder
ssh_folder = os.path.expanduser("~/.ssh")
public_keys = glob.glob(os.path.join(ssh_folder, "*.pub"))

if public_keys:
    print(f"Select the SSH public key for this account (e.g. {ansi.grey}id_ed25519_machine_{ansi.reset}{ansi.magenta}{username}{ansi.reset}.pub): ")
    default_key = next((key for key in public_keys if username in os.path.basename(key)), None)
    for i, key in enumerate(public_keys, 1):
        is_default = key == default_key
        print(f"{ansi.yellow}{i}.{ansi.reset} {os.path.basename(key)}{' (default)' if is_default else ''}")
    key_selection = input(f"Select a key number or enter a custom path: {ansi.grey}(default: {os.path.basename(default_key) if default_key else 'None'}){ansi.reset} ")
    if not key_selection and default_key:
        ssh_key = default_key
    elif key_selection.isdigit() and 1 <= int(key_selection) <= len(public_keys):
        ssh_key = public_keys[int(key_selection) - 1]
    elif os.path.exists(os.path.expanduser(key_selection)):
        ssh_key = os.path.expanduser(key_selection)
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

# Prompt user to open browser profile associated with github account
print("Open the browser profile associated with this GitHub account")
input(f"This will log you in. Press {ansi.green}Enter{ansi.reset} to continue...")

# Check gh auth status and log out if necessary
print("Checking auth status...")
auth_status = shell.run("gh auth status")

# Authorize gh-cli with ssh key
shell.run("gh auth login --git-protocol ssh --hostname github.com --web")
shell.run("gh auth status")
shell.run("gh repo list")

config_familiar = input("\nIs the above configuration familiar? (y/n): ")
logger.info("User config_familiar response: %s", config_familiar)
if config_familiar.lower() not in ["y", "yes"]:
    logger.warning("User indicated unfamiliar configuration")
    print("Please adjust your config at ~/.ssh/config and run this script again.")
    exit(1)

# Use organization if user selects org
if repo_type in ["org", "organization"]:
    print(f"\nNote: {ansi.red}NEW organizations must be created via GitHub web interface.{ansi.reset}")
    print("Select the organization you want to create the repo for:")
    orgs_call = shell.execute("gh api user/orgs --paginate")
    logger.info("orgs_call: %s", orgs_call)
    orgs = json.loads(orgs_call[0])
    org_names = [org['login'] for org in orgs]
    for i, org in enumerate(org_names, 1):
        print(f"{ansi.yellow}{i}.{ansi.reset} {org}")
    org_selection = input("Select the organization by number: ")
    if org_selection.isdigit() and 1 <= int(org_selection) <= len(orgs):
        organization = orgs[int(org_selection) - 1]['login']
    else:
        print("Invalid selection. Choose an organization from the list.")
        exit(1)
    logger.info("Organization: %s", organization)
    username = organization

# Create the repo on GitHub
logger.info("Creating repository: %s/%s", username, repo_name)
print(f"\nCreating repository: {ansi.cyan}{username}/{repo_name}{ansi.reset}")
create_repo = shell.run(f"gh repo create {username}/{repo_name} --{repo_visibility} --clone")

# Check if repo was created successfully
if create_repo[1]:
    logger.error("Failed to create repository")
    print(f"{ansi.red}Failed to create repository.{ansi.reset} Please check the error message above and try again.")
    exit(1)

# Configure git for the new repository
os.chdir(repo_name)

# SSH Key
shell.execute(f'git config user.signingkey "{ssh_key}"')
shell.execute('git config gpg.format ssh')
shell.execute('git config commit.gpgsign true')
shell.execute('git config pull.rebase true')

# User
shell.execute(f'git config user.name "{name}"')
shell.execute(f'git config user.email {email}')
logger.info('Git configured with name: "%s" and email: %s', name, email)

# Set up remote
shell.execute("git remote remove origin")
shell.execute(f"git remote add origin git@{ssh_host}:{username}/{repo_name}.git")

# Create initial commit
shell.execute(f'git checkout -b {git_repo_branch}')
shell.execute('type nul > README.md')
shell.execute('git add .')
shell.execute('git commit -m "chore: init"')
shell.execute(f'git push -u origin {git_repo_branch}')

logger.info("Repository setup complete")
print(f"\n{ansi.green}Repository setup complete!{ansi.reset}")
