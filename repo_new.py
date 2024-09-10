"""
This script will be a step by step guide to creating a new repository on GitHub and cloning it to your local machine.
It will use the gh-cli tool to create the repo and clone it to your local machine.
gh auth login will be via ssh key
Requirements:
- gh-cli
- git
- ed25519 ssh key set up
- ssh key added to GitHub account
- added as collaborator to the repo
"""
from utils.style import ansi
from utils.cli import shell
import logging
import glob
import os

from logs.config import log_config
log_config(__file__)

# Prompt user for the folder where the repo will live
print(f"Enter the folder where you want to create the repo (e.g. {ansi.blue}~/Documents{ansi.reset} or {ansi.blue}C:\\Users\\YourName\\Documents{ansi.reset}): ")
repo_parent_folder = input(" > ")
repo_parent_folder = os.path.expanduser(repo_parent_folder)
logging.info(f"Repo parent folder: {repo_parent_folder}")

# Change directory and create repo folder
os.makedirs(repo_parent_folder, exist_ok=True)
os.chdir(repo_parent_folder)
logging.info(f"Changed directory to: {repo_parent_folder}")

# Ask the user for the repo name
repo_name = input("Enter the name of the new repo: ")
logging.info(f"Repo name: {repo_name}")

# Prompt user for git repo branch
git_repo_branch = input(f"Enter git repo branch: {ansi.grey}(default: main){ansi.reset} ")
if not git_repo_branch:
    git_repo_branch = "main"
logging.info(f"Git repo branch: {git_repo_branch}")

# Ask the user if this repo is for an organization or a username
repo_type = input(f"Is this repo for an organization or a username? ({ansi.cyan}user{ansi.reset} / {ansi.magenta}org{ansi.reset}): {ansi.grey}(default: user){ansi.reset} ").lower()
if not repo_type:
    repo_type = "user"
logging.info(f"Repo type: {repo_type}")

# Ask user if they want public or private repo
repo_visibility = input(f"Enter repo visibility ({ansi.cyan}public{ansi.reset} / {ansi.magenta}private{ansi.reset}): {ansi.grey}(default: private){ansi.reset}" ).lower()
if not repo_visibility:
    repo_visibility = "private"
elif repo_visibility not in ['public', 'private']:
    print(f"{ansi.red}Invalid input.{ansi.reset} Please enter 'public' or 'private'.")
    exit(1)
logging.info(f"Repository visibility: {repo_visibility}")

if repo_type.lower() in ["org", "organization"]:
    print(f"Note: {ansi.red}NEW organizations must be created via GitHub web interface.{ansi.reset}")
    username = input("Enter the name of the organization: ")
else:
    username = input("Enter your username: ")
logging.info(f"User/Organization: {username}")

# Prompt user for name
name = input("Enter git name: ")
logging.info(f"Git name: {name}")

# Prompt user for email
email = input("Enter git email: ")
logging.info(f"Git email: {email}")

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

# TODO: Determine a better way to get the SSH host if org belongs to a user that already has an SSH key created
# i.e. org belongs to user but org matching ssh key is not found in ~/.ssh folder, only user - how to know org belongs to user?
# remember to change code to use user for ssh_key and ssh_host even if org is selected
# instead of user or org change to user and org if user wants org
# if org input then gh api call to get orgs and list them for selection
# `gh api user/orgs`
# example response:
# [
#   {
#     "login": "github",
#     "id": 9919,
#     "node_id": "MDEyOk9yZ2FuaXphdGlvbjM0",
#     "url": "https://api.github.com/orgs/github",
#     "repos_url": "https://api.github.com/orgs/github/repos",
#     "events_url": "https://api.github.com/orgs/github/events",
#     "hooks_url": "https://api.github.com/orgs/github/hooks",
#     "issues_url": "https://api.github.com/orgs/github/issues",
#     "members_url": "https://api.github.com/orgs/github/members{/member}",
#     "public_members_url": "https://api.github.com/orgs/github/public_members{/member}",
#     "avatar_url": "https://github.com/images/error/octocat_happy.gif",
#     "description": "A great organization"
#   }
# ]


# Prompt user for SSH host
print(f"Enter the SSH host for GitHub: {ansi.grey}(default: {username}.github.com){ansi.reset}")
ssh_host = input(f"{ansi.grey} > {ansi.reset}") or f"{username}.github.com"
logging.info(f"SSH host: {ssh_host}")

# Prompt user to open browser profile associated with github account
input(f"Open the browser profile associated with this GitHub account and press Enter to continue...")

# Check gh auth status and log out if necessary
print("Checking auth status...")
auth_status = shell.run("gh auth status")
# # TODO: figure out how to get output of interactive shell commands
# if "Logged in to github.com as" in auth_status[0]:
#     logging.info("Logging out of existing gh auth session")
#     shell.run("gh auth logout --hostname github.com")

# Authorize gh-cli with ssh key
shell.run("gh auth login --git-protocol ssh --hostname github.com --web")
shell.run("gh auth status")
shell.run("gh repo list")

config_familiar = input("\nIs the above configuration familiar? (y/n): ")
logging.info(f"User config_familiar response: {config_familiar}")
if config_familiar.lower() not in ["y", "yes"]:
    logging.warning("User indicated unfamiliar configuration")
    print("Please adjust your config at ~/.ssh/config and run this script again.")
    exit(1)
# TODO: check if repo already exists

# Create the repo on GitHub
logging.info(f"Creating repository: {username}/{repo_name}")
print(f"\nCreating repository: {ansi.cyan}{username}/{repo_name}{ansi.reset}")
create_repo = shell.run(f"gh repo create {username}/{repo_name} --{repo_visibility} --clone")

# Check if repo was created successfully
if create_repo[1]:
    logging.error("Failed to create repository")
    print(f"{ansi.red}Failed to create repository.{ansi.reset} Please check the error message above and try again.")
    exit(1)

# Configure git for the new repository
os.chdir(repo_name)

# SSH Key
shell.execute(f'git config user.signingkey "{ssh_key}"')
shell.execute('git config gpg.format ssh')
shell.execute('git config commit.gpgsign true')

# User
shell.execute(f'git config user.name "{name}"')
shell.execute(f'git config user.email {email}')
logging.info(f'Git configured with name: "{name}" and email: {email}')

# Set up remote
shell.execute("git remote remove origin")
shell.execute(f"git remote add origin git@{ssh_host}:{username}/{repo_name}.git")

# Create initial commit
shell.execute(f'git checkout -b {git_repo_branch}')
shell.execute('type nul > README.md')
shell.execute('git add .')
shell.execute('git commit -m "Initial commit"')
shell.execute(f'git push -u origin {git_repo_branch}')

logging.info("Repository setup complete")
print(f"\n{ansi.green}Repository setup complete!{ansi.reset}")