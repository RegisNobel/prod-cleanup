# Production Backup Cleanup Script

This repository contains a Python script that removes environment-specific details from a production backup before it is shared or reused.

## Script

The main script is `sanitize_prod_backup.py`.

It performs the following cleanup steps for a selected customer:

1. Starts from the base folder:
   `C:\Users\koudouva\Documents\clocks-resources`
2. Prompts for a customer name, then works inside:
   `C:\Users\koudouva\Documents\clocks-resources\<customer-name>`
3. Deletes `controller\config\clocksettings.conf` if it exists
4. Processes `controller\data\0001\export`
5. Processes `controller\data\0001\import`

For each folder inside `export` and `import`, the script:

- Deletes a file named `lastrun` if it exists
- Finds every `def.conf` file
- Locates the `[host]` section in each `def.conf`
- Clears the value after `=` for each variable in that section

## Expected Folder Structure

```text
<base>
└── <customer-name>
    └── controller
        ├── config
        │   └── clocksettings.conf
        └── data
            └── 0001
                ├── export
                │   └── <subfolders>
                └── import
                    └── <subfolders>
```

## How To Run

Run the script with Python:

```powershell
python sanitize_prod_backup.py
```

The script will prompt you for the customer name:

```text
Enter customer name:
```

You can also pass the customer name directly:

```powershell
python sanitize_prod_backup.py CustomerName
```

## Update History

This section should be updated for each new request or change made to the script.

- 2026-04-08 14:10:58 -04:00: Added `README.md` with script overview, usage instructions, folder structure, and update log section.
