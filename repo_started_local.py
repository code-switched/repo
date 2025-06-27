"""
This script helps set up Git and GitHub for an existing local project.
It will initialize git, create a new GitHub repository, and push the existing code.
Requirements:
- gh-cli
- git
- ed25519 ssh key set up
- ssh key added to GitHub account
"""
import os
import json
import glob

from utils.style import ansi
from utils.cli import shell

from logs.config import log_config
logger = log_config(__file__)

def get_project_path():
    """Get the path to the project directory."""
    print(f"Enter the path to your existing project: {ansi.grey}(or press Enter for current directory){ansi.reset}")
    path = input(" > ").strip()

    if not path:
        path = os.getcwd()

    # Convert to absolute path
    path = os.path.abspath(os.path.expanduser(path))

    if not os.path.exists(path):
        logger.error("Path does not exist: %s", path)
        print(f"{ansi.red}Error:{ansi.reset} The specified path does not exist.")
        exit(1)

    if not os.path.isdir(path):
        logger.error("Path is not a directory: %s", path)
        print(f"{ansi.red}Error:{ansi.reset} The specified path is not a directory.")
        exit(1)

    return path

project_path = get_project_path()
logger.info("Project directory: %s", project_path)

# Change to the project directory
os.chdir(project_path)
current_dir = os.getcwd()
logger.info("Changed to directory: %s", current_dir)

repo_name = os.path.basename(current_dir)
logger.info("Repo name from directory: %s", repo_name)

# Confirm repo name or allow change
print(f"Current folder name will be used as repo name: {ansi.cyan}{repo_name}{ansi.reset}")
new_name = input(f"Press Enter to keep or type new name: {ansi.grey}(default: {repo_name}){ansi.reset} ")
if new_name:
    repo_name = new_name
logger.info("Final repo name: %s", repo_name)

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
    elif os.path.exists(key_selection):
        ssh_key = key_selection
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

# Initialize git if not already initialized
if not os.path.exists('.git'):
    shell.execute("git init")
    logger.info("Git repository initialized")

# Configure git
shell.execute(f'git config user.name "{name}"')
shell.execute(f'git config user.email {email}')
shell.execute(f'git config user.signingkey "{ssh_key}"')
shell.execute('git config gpg.format ssh')
shell.execute('git config commit.gpgsign true')
shell.execute('git config pull.rebase true')
logger.info("Git configuration complete")

# Add this section to ensure we're on main branch
shell.execute('git checkout -b main')  # Create and switch to main branch
logger.info("Switched to main branch")

# Handle organization repos
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
create_repo = shell.run(f"gh repo create {username}/{repo_name} --{repo_visibility} --source=.")

# Check if repo was created successfully
if create_repo[1]:
    logger.error("Failed to create repository")
    print(f"{ansi.red}Failed to create repository.{ansi.reset} Please check the error message above and try again.")
    exit(1)

# Set up remote with correct SSH URL
shell.execute("git remote remove origin")
shell.execute(f"git remote add origin git@{ssh_host}:{username}/{repo_name}.git")

# Create initial commit if needed
status = shell.execute("git status --porcelain")
if status[0]:
    shell.execute("git add .")
    shell.execute('git commit -m "chore: init"')

# Push to remote
shell.execute('git push -u origin main')

logger.info("Repository setup complete")
print(f"\n{ansi.green}Repository setup complete!{ansi.reset}")
