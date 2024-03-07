import subprocess
import sys

def main():
    domain = "abc.com"

    # Run git config command to get the user email
    result = subprocess.run(["git", "config", "--list"], capture_output=True, text=True)
    git_config_output = result.stdout

    # Extract the email domain
    email_domain = None
    for line in git_config_output.split('\n'):
        if line.startswith("user.email"):
            email_domain = line.split('@')[1]
            break

    if email_domain == domain:
        print("You are using company domain as your email, proceeding with committing")
        exit(0)
    else:
        print("You are using a NON-Company domain as your email. This commit will not be recorded. Please change the email and then commit again")
        exit(1)

if __name__ == "__main__":
    sys.exit(main())
