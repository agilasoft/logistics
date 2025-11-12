# Fix for Item Deletion Error

## Problem
When trying to delete an Item, you get the error:
```
pymysql.err.OperationalError: (1054, "Unknown column 'parent' in 'SELECT'")
```

## Root Cause
Some child table doctypes that link to Item are missing the required `parent`, `parentfield`, and `parenttype` columns in the database, even though they are marked as `istable: 1` in their JSON definitions.

## Solution

### ✅ Automatic Fix (Recommended)

**The fix is now built into the app!** When you update the logistics app, the patch will automatically run and fix the issue on all sites.

To apply the fix:
```bash
# Update the app (this will automatically run the patch)
bench update

# Or if you want to run patches manually
bench --site all migrate
```

The patch (`fix_item_deletion_parent_columns`) will:
- Check all sites automatically
- Add missing `parent`, `parentfield`, and `parenttype` columns to affected tables
- Add the required indexes
- Skip tables that already have the columns
- Log any errors for review

### Manual Fix Options

### Option 1: Use the provided script (Recommended)

1. Copy the script `fix_item_deletion_error.sh` to your other server
2. Navigate to your bench directory
3. Run the script:

```bash
# For all sites
./fix_item_deletion_error.sh

# For a specific site
./fix_item_deletion_error.sh your-site-name
```

### Option 2: Manual SQL commands

Run these SQL commands for each site that has the issue:

```sql
-- Fix Customs Rate table
ALTER TABLE `tabCustoms Rate` 
ADD COLUMN `parent` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parentfield` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parenttype` VARCHAR(140) NULL DEFAULT NULL,
ADD INDEX `parent` (`parent`);

-- Fix Sea Freight Rate table
ALTER TABLE `tabSea Freight Rate` 
ADD COLUMN `parent` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parentfield` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parenttype` VARCHAR(140) NULL DEFAULT NULL,
ADD INDEX `parent` (`parent`);

-- Fix Air Freight Rate table
ALTER TABLE `tabAir Freight Rate` 
ADD COLUMN `parent` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parentfield` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parenttype` VARCHAR(140) NULL DEFAULT NULL,
ADD INDEX `parent` (`parent`);
```

Using bench command:
```bash
bench --site your-site-name mariadb -e "ALTER TABLE \`tabCustoms Rate\` ADD COLUMN \`parent\` VARCHAR(140) NULL DEFAULT NULL, ADD COLUMN \`parentfield\` VARCHAR(140) NULL DEFAULT NULL, ADD COLUMN \`parenttype\` VARCHAR(140) NULL DEFAULT NULL, ADD INDEX \`parent\` (\`parent\`);"
```

### Option 3: Check which doctypes need fixing

Run this to check which tables are missing the parent columns:

```bash
bench --site your-site-name mariadb -e "
SELECT 
    TABLE_NAME,
    CASE 
        WHEN COUNT(CASE WHEN COLUMN_NAME = 'parent' THEN 1 END) = 0 THEN 'Missing parent column'
        WHEN COUNT(CASE WHEN COLUMN_NAME = 'parentfield' THEN 1 END) = 0 THEN 'Missing parentfield column'
        WHEN COUNT(CASE WHEN COLUMN_NAME = 'parenttype' THEN 1 END) = 0 THEN 'Missing parenttype column'
        ELSE 'OK'
    END as status
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME IN ('tabCustoms Rate', 'tabSea Freight Rate', 'tabAir Freight Rate')
AND COLUMN_NAME IN ('parent', 'parentfield', 'parenttype')
GROUP BY TABLE_NAME;
"
```

## After applying the fix

1. If you used the automatic patch (recommended), no restart is needed - the patch runs during app update
2. If you used manual SQL commands, restart the bench:
   ```bash
   bench restart
   ```

3. Test deleting an Item to verify the fix works

## Patch Details

The automatic patch is located at:
- `logistics/patches/fix_item_deletion_parent_columns.py`
- Registered in `logistics/patches.txt`

The patch will run automatically when:
- You update the app with `bench update`
- You run migrations with `bench --site all migrate`
- The app is installed/updated on a new server

## Affected Doctypes

The following doctypes were found to have this issue:
- `Customs Rate` (istable: 1, links to Item)
- `Sea Freight Rate` (istable: 1, links to Item)
- `Air Freight Rate` (istable: 1, links to Item)

## Note

No changes are needed in the JSON files. The doctypes are correctly configured with `istable: 1`. The issue was only in the database schema where the parent columns were missing.

