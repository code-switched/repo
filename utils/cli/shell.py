import logging
import subprocess
from utils.style import ansi

# TODO: figure out how to get output of interactive shell commands
# if "Logged in to github.com as" in auth_status[0]:
#     logging.info("Logging out of existing gh auth session")
#     shell.run("gh auth logout --hostname github.com")
# Returns no output, no error
# Only execute works with stdout PIPE, run does not return output

def execute(command):
    """
    - Run a command and return the output and error
    - The command's output and error streams are connected to pipes.
    - Output is not displayed in real-time; it's collected and can be processed after the command finishes.
    - This means that the command will not block the parent process.
    - This is useful for commands that need to be run in the background, such as long-running commands.
    """
    logging.info(f"Executing command: {command}")
    print(f"\n{ansi.grey}{command}{ansi.reset}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output_bytes, error_bytes = process.communicate()

    output = output_bytes.decode('utf-8').strip()
    error = error_bytes.decode('utf-8').strip()

    if output:
        logging.info(output)
        print(f"{ansi.cyan}> {ansi.reset}{output}")
    if error:
        logging.error(error)
        print(f"{ansi.red}> {ansi.reset}{error}")
    return output, error


def run(command):
    """
    - Run a command and return the output and error
    - The command's output and error streams are connected directly to the parent process's streams.
    - Output is displayed in real-time as the command executes.
    - This means that the command will block the parent process until it finishes.
    - This is useful for commands that need to be run in the foreground, such as interactive commands.
    - The function allows for interactive use, where the user can see and potentially respond to output as it's generated.
    """
    logging.info(f"Executing command: {command}")
    print(f"\n{ansi.grey}{command}{ansi.reset}")
    process = subprocess.Popen(command, shell=True)
    output_bytes, error_bytes = process.communicate()

    output = output_bytes.decode('utf-8').strip() if output_bytes else ""
    error = error_bytes.decode('utf-8').strip() if error_bytes else ""

    if output:
        logging.info(output)
        print(f"{ansi.cyan}> {ansi.reset}{output}")
    if error:
        logging.error(error)
        print(f"{ansi.red}> {ansi.reset}{error}")
    return output, error
