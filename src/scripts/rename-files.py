import os

def remove_trailing_dots(maildir_path: str, dry_run: bool = True):
    """
    Rename all files with trailing dots in the Enron maildir.
    
    Args:
        maildir_path: Path to the maildir folder
        dry_run: If True, only prints what would be renamed without doing it.
                 Set to False to actually rename.
    """
    renamed = 0
    skipped = 0

    for root, dirs, files in os.walk(maildir_path):
        for file in files:
            if file.endswith("."):
                old_path = os.path.join(root, file)
                new_name = file.rstrip(".")
                new_path = os.path.join(root, new_name)

                if dry_run:
                    print(f"[DRY RUN] {old_path}  ->  {new_path}")
                else:
                    os.rename(old_path, new_path)
                    print(f"Renamed: {old_path}  ->  {new_path}")
                renamed += 1

    print(f"\n{'Would rename' if dry_run else 'Renamed'}: {renamed} files")
    if dry_run:
        print("Run with dry_run=False to apply changes.")


if __name__ == "__main__":
    MAILDIR = r"D:\Projects\enron-email-project\data\data\enron_mail"

    # Step 1: preview changes first
    remove_trailing_dots(MAILDIR, dry_run=False)

    # Step 2: once happy, uncomment this to actually rename
    # remove_trailing_dots(MAILDIR, dry_run=False)