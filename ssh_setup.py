from utils.style import ansi
from utils.cli import shell
import os

import logging
from logs.config import log_config
log_config(__file__)

def display_tips():
    print(
    f"""{ansi.cyan}Tips:{ansi.reset}
    - Generate a new ssh key per machine per account
    - Use the ed25519 algorithm
    - Determine the format of the key file name
        - id_ed25519_<machine>_<account>
    - Create new ssh key
    - Add the key to GitHub under Authentication keys and Signing keys
    - Set up ssh config file (~/.ssh/config) using ssh_config.txt as a reference
    - Test ssh connection to GitHub
    """
    )

def check_ed25519_key():
    """Verify that an ed25519 key is set up"""
    print("\nVerifying that your ED25519 exists...")
    key_path = os.path.expanduser("~/.ssh/id_ed25519")
    if os.path.exists(key_path):
        logging.info("ED25519 key found")
        print(f"{ansi.green}ED25519 key found.{ansi.reset}")
        return True
    logging.warning("ED25519 key not found")
    print(f"{ansi.red}ED25519 key not found.{ansi.reset}")
    print("Generate a new key using the following command:")
    print(f"{ansi.cyan}ssh-keygen -t ed25519 -C 'your_email@example.com'{ansi.reset}")
    return False

def check_github_key():
    """Verify that the key is added to GitHub"""
    print("\nTo verify if your key is added to GitHub:")
    print(f"1. Go to {ansi.blue}https://github.com/settings/keys{ansi.reset}")
    print("2. Check if your ED25519 key is listed")
    print("3. If not, add your public (.pub) key to:")
    print(f"- Authentication keys")
    print(f"- Signing keys")

    public_key_path = os.path.expanduser('~/.ssh/id_ed25519.pub')
    print(f"(You can find your public key at path: {ansi.cyan}{public_key_path}{ansi.reset})")
    if os.path.exists(public_key_path):
        with open(public_key_path, 'r') as file:
            public_key = file.read().strip()
        print(f"Your public key is:\n{ansi.cyan}{public_key}{ansi.reset}\n")
        logging.info(f"Public key: {public_key}\n")

    key_added = input("Is your key added to GitHub? (y/n): ")
    if key_added.lower() not in ['y', 'yes']:
        logging.warning("User indicated key is not added to GitHub")
        return False
    github_login = shell.run(f"ssh -T git@github.com")
    if "successfully authenticated" in github_login[1]:
        logging.info("GitHub SSH access authenticated")
        return True


def main():
    logging.info("Starting SSH setup verification")
    ed25519_ok = check_ed25519_key()
    github_ok = check_github_key()

    if ed25519_ok and github_ok:
        logging.info("All checks passed. SSH setup looks good")
        print(f"{ansi.green}All checks passed. Your SSH setup looks good!{ansi.reset}")

    if not ed25519_ok or not github_ok:
        logging.error("At least one check failed")
        print(f"{ansi.red}At least one check failed. Please address the issues mentioned above.{ansi.reset}")
        exit(1)

    print(f"Repeat this process for any machine that needs access to this repository.")
    logging.info("SSH setup verification completed")


if __name__ == "__main__":
    main()