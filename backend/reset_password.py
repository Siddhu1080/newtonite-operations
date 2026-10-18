
from getpass import getpass

from pwdlib import PasswordHash
from sqlalchemy import text

from app.database import engine


def main():
    email = "testuser@example.com"

    new_password = getpass("Enter your new password: ")
    confirm_password = getpass("Confirm your new password: ")

    if len(new_password) < 8:
        print("Password must be at least 8 characters.")
        return

    if new_password != confirm_password:
        print("Passwords do not match.")
        return

    password_hash = PasswordHash.recommended().hash(new_password)

    with engine.begin() as connection:
        result = connection.execute(
            text("""
                UPDATE users
                SET password_hash = :password_hash
                WHERE email = :email
            """),
            {
                "password_hash": password_hash,
                "email": email,
            },
        )

        if result.rowcount == 0:
            print(f"No account found for {email}.")
            return

    print(f"Password reset successfully for {email}.")


if __name__ == "__main__":
    main()
