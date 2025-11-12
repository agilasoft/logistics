# Immediate Fix for Item Deletion Error

The patch didn't run automatically. Use one of these methods to fix it immediately:

## Method 1: Direct SQL (Fastest - Recommended)

Run this command on the server with the error (`atnph.s.frappe.cloud`):

```bash
bench --site atnph.s.frappe.cloud mariadb -e "
ALTER TABLE \`tabCustoms Rate\` 
ADD COLUMN \`parent\` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN \`parentfield\` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN \`parenttype\` VARCHAR(140) NULL DEFAULT NULL,
ADD INDEX \`parent\` (\`parent\`);

ALTER TABLE \`tabSea Freight Rate\` 
ADD COLUMN \`parent\` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN \`parentfield\` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN \`parenttype\` VARCHAR(140) NULL DEFAULT NULL,
ADD INDEX \`parent\` (\`parent\`);

ALTER TABLE \`tabAir Freight Rate\` 
ADD COLUMN \`parent\` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN \`parentfield\` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN \`parenttype\` VARCHAR(140) NULL DEFAULT NULL,
ADD INDEX \`parent\` (\`parent\`);
"
```

**Note:** If you get "Duplicate column name" errors, that's okay - it means some columns already exist. The command will add the missing ones.

## Method 2: Run Patch Manually

```bash
bench --site atnph.s.frappe.cloud execute logistics.patches.fix_item_deletion_parent_columns.execute
```

## Method 3: Use the Shell Script

Copy `fix_item_deletion_error.sh` to the server and run:

```bash
./fix_item_deletion_error.sh atnph.s.frappe.cloud
```

## After Running the Fix

1. **No restart needed** - the fix takes effect immediately
2. **Test deleting an Item** - it should work now
3. If it still doesn't work, check for other doctypes that might have the same issue

## Verify the Fix

Check if columns were added:

```bash
bench --site atnph.s.frappe.cloud mariadb -e "
SELECT 
    TABLE_NAME,
    CASE WHEN COUNT(*) = 3 THEN '✓ OK' ELSE '✗ Missing columns' END as status
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME IN ('tabCustoms Rate', 'tabSea Freight Rate', 'tabAir Freight Rate')
AND COLUMN_NAME IN ('parent', 'parentfield', 'parenttype')
GROUP BY TABLE_NAME;
"
```

