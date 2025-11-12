# Fix Item Deletion Error on Frappe Cloud

The patch hasn't run yet. You need to apply the fix manually on Frappe Cloud.

## Quick Fix - Run SQL Directly

1. **Go to Frappe Cloud Dashboard** → Your Site → Database
2. **Open Database Console** or use any SQL tool
3. **Run this SQL:**

```sql
ALTER TABLE `tabCustoms Rate` 
ADD COLUMN `parent` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parentfield` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parenttype` VARCHAR(140) NULL DEFAULT NULL,
ADD INDEX `parent` (`parent`);

ALTER TABLE `tabSea Freight Rate` 
ADD COLUMN `parent` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parentfield` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parenttype` VARCHAR(140) NULL DEFAULT NULL,
ADD INDEX `parent` (`parent`);

ALTER TABLE `tabAir Freight Rate` 
ADD COLUMN `parent` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parentfield` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN `parenttype` VARCHAR(140) NULL DEFAULT NULL,
ADD INDEX `parent` (`parent`);
```

**Note:** If you get "Duplicate column name" errors, ignore them - it means those columns already exist. The command will add the missing ones.

## Alternative: Via Console (if available)

If you have console/SSH access:

```bash
bench --site your-site-name execute logistics.patches.fix_item_deletion_parent_columns.execute
```

## After Running the Fix

1. **No restart needed** - takes effect immediately
2. **Try deleting the Item again** - it should work now
3. The patch will also run automatically on future migrations to prevent this on other sites

## Verify the Fix

Check if columns were added:

```sql
SELECT 
    TABLE_NAME,
    CASE WHEN COUNT(*) = 3 THEN '✓ OK' ELSE '✗ Missing' END as status
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME IN ('tabCustoms Rate', 'tabSea Freight Rate', 'tabAir Freight Rate')
AND COLUMN_NAME IN ('parent', 'parentfield', 'parenttype')
GROUP BY TABLE_NAME;
```

All three tables should show "✓ OK".

