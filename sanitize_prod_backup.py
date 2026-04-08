#!/usr/bin/env python3
r"""
Remove environment-specific DB and host details from a customer backup.

Default base directory:
    C:\Users\koudouva\Documents\clocks-resources

Expected customer structure:
    <base>\<customer>\controller\config
    <base>\<customer>\controller\data\0001\export
    <base>\<customer>\controller\data\0001\import

Usage:
    python sanitize_prod_backup.py
    python sanitize_prod_backup.py CUSTOMER_NAME
    python sanitize_prod_backup.py CUSTOMER_NAME --base-dir "C:\path\to\clocks-resources"
"""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_BASE_DIR = Path(r"C:\Users\koudouva\Documents\clocks-resources")


def clear_host_section(conf_path: Path) -> bool:
    """Blank values in the [host] section for every key=value line."""
    # Open the config file as text.
    # `errors="ignore"` helps the script keep going even if the file contains
    # a few unusual characters.
    original_text = conf_path.read_text(encoding="utf-8", errors="ignore")

    # Split the file into lines, but keep the original line endings.
    # This lets us rewrite the file without changing its general format too much.
    lines = original_text.splitlines(keepends=True)

    # We will build a new version of the file line by line.
    updated_lines: list[str] = []

    # This flag tells us whether we are currently inside the [host] section.
    in_host_section = False

    # This flag helps us decide whether the file needs to be written back to disk.
    changed = False

    for line in lines:
        # `strip()` removes spaces/newlines from the start and end of the line,
        # which makes it easier to compare section names like [host].
        stripped = line.strip()

        # INI-style config files use [section-name] headers.
        # If we see one, we check whether it is the [host] section.
        # Any new section means we are leaving the previous one.
        if stripped.startswith("[") and stripped.endswith("]"):
            in_host_section = stripped.lower() == "[host]"
            updated_lines.append(line)
            continue

        # While we are inside the [host] section, we want to blank out values.
        # Example:
        #     server=my-db-host
        # becomes:
        #     server=
        #
        # `partition("=")` splits the line into:
        #   1. text before "="
        #   2. the "=" itself
        #   3. text after "="
        if in_host_section and "=" in line:
            key, _, _ = line.partition("=")

            # Preserve whether the original line ended with a newline character.
            # That way the file formatting stays neat after rewriting.
            newline = "\n" if line.endswith("\n") else ""
            new_line = f"{key}={newline}"
            if new_line != line:
                changed = True
            updated_lines.append(new_line)
            continue

        # For all other lines, keep them exactly as they are.
        updated_lines.append(line)

    # Only write the file back if something changed.
    # This avoids unnecessary file updates.
    if changed:
        conf_path.write_text("".join(updated_lines), encoding="utf-8")

    # Return True/False so the caller can count how many files were updated.
    return changed


def delete_if_exists(file_path: Path) -> bool:
    # This helper keeps the "delete if present" logic in one place.
    # It returns True if a file was deleted, otherwise False.
    if file_path.exists():
        file_path.unlink()
        return True
    return False


def process_area(area_path: Path) -> tuple[int, int]:
    """Process each immediate child folder in an area such as export/import."""
    # These counters help us produce a summary at the end of the script.
    # The first number counts deleted `lastrun` files.
    # The second number counts updated `def.conf` files.
    lastrun_deleted = 0
    defconf_updated = 0

    # If the folder does not exist, there is nothing to process.
    # We simply return zero counts instead of crashing.
    if not area_path.is_dir():
        return lastrun_deleted, defconf_updated

    # Look at each item directly inside the area.
    # We only care about folders, because the instructions say to process each folder.
    for child in area_path.iterdir():
        if not child.is_dir():
            continue

        # Try to delete a file named `lastrun` inside that folder.
        # If it existed and was deleted, increase the counter.
        if delete_if_exists(child / "lastrun"):
            lastrun_deleted += 1

        # Search through this folder and all nested folders for files named `def.conf`.
        # `rglob("def.conf")` means "recursive glob" for that file name.
        for conf_path in child.rglob("def.conf"):
            if conf_path.is_file() and clear_host_section(conf_path):
                defconf_updated += 1

    # Return both counters to the caller.
    return lastrun_deleted, defconf_updated


def main() -> int:
    # Set up command-line options.
    # The customer name is optional here because we can ask for it interactively.
    parser = argparse.ArgumentParser(
        description="Remove DB details from a prod backup for a customer."
    )
    parser.add_argument(
        "customer_name",
        nargs="?",
        help="Customer folder name under the base directory.",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=DEFAULT_BASE_DIR,
        help=f"Base clocks-resources directory (default: {DEFAULT_BASE_DIR})",
    )
    args = parser.parse_args()

    # First try to get the customer name from the command line.
    customer_name = args.customer_name
    if not customer_name:
        # If it was not supplied, ask the user to type it in.
        # `.strip()` removes extra spaces before/after the typed value.
        customer_name = input("Enter customer name: ").strip()

    # Stop early if the customer name is still empty.
    if not customer_name:
        raise SystemExit("Customer name is required.")

    # Build the main paths we need using the base directory and customer name.
    # Path objects are safer and easier to work with than manually joining strings.
    home_dir = args.base_dir / customer_name
    controller_dir = home_dir / "controller"

    # Make sure the customer folder actually exists before continuing.
    if not home_dir.is_dir():
        raise SystemExit(f"Customer directory not found: {home_dir}")

    # Step 3:
    # Go to controller\config and remove clockSetting.conf if it exists.
    clocksettings_path = controller_dir / "config" / "clockSetting.conf"
    clocksettings_deleted = delete_if_exists(clocksettings_path)

    # Steps 4 and 5:
    # The import and export folders live under controller\data\0001.
    # We save that root once so we do not repeat the long path multiple times.
    data_root = controller_dir / "data" / "0001"

    # Clean the export side.
    export_lastrun_deleted, export_defconf_updated = process_area(
        data_root / "export"
    )

    # Clean the import side.
    import_lastrun_deleted, import_defconf_updated = process_area(
        data_root / "import"
    )

    # Print a readable summary so the person running the script can confirm
    # what happened without opening every folder manually.
    print(f"Customer directory: {home_dir}")
    print(f"Deleted clockSetting.conf: {'yes' if clocksettings_deleted else 'no'}")
    print(
        "Export cleanup: "
        f"{export_lastrun_deleted} lastrun deleted, "
        f"{export_defconf_updated} def.conf updated"
    )
    print(
        "Import cleanup: "
        f"{import_lastrun_deleted} lastrun deleted, "
        f"{import_defconf_updated} def.conf updated"
    )

    return 0


if __name__ == "__main__":
    # This is the standard Python entry point.
    # It makes sure `main()` runs only when this file is executed directly.
    raise SystemExit(main())
