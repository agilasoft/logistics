#!/bin/bash

# Script to fix Item deletion error caused by missing parent columns in child tables
# Run this script on the server where the error is occurring
# Usage: ./fix_item_deletion_error.sh [site-name]
#        If no site name is provided, it will process all sites

echo "=== Fixing Item deletion error ==="
echo "This script will add missing parent columns to child table doctypes that link to Item"
echo ""

# Get the site name from command line argument or use 'all'
SITE=${1:-all}

fix_table() {
    local site=$1
    local table=$2
    
    echo "  Fixing $table..."
    bench --site $site mariadb -e "
        -- Check if parent column exists, if not add it
        SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
                          WHERE TABLE_SCHEMA = DATABASE() 
                          AND TABLE_NAME = '$table' 
                          AND COLUMN_NAME = 'parent');
        
        SET @sql = IF(@col_exists = 0,
            'ALTER TABLE \`$table\` 
             ADD COLUMN \`parent\` VARCHAR(140) NULL DEFAULT NULL,
             ADD COLUMN \`parentfield\` VARCHAR(140) NULL DEFAULT NULL,
             ADD COLUMN \`parenttype\` VARCHAR(140) NULL DEFAULT NULL,
             ADD INDEX \`parent\` (\`parent\`)',
            'SELECT ''Columns already exist in $table''');
        
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    " 2>&1 | grep -v "already exist" || true
}

if [ "$SITE" = "all" ]; then
    echo "Applying fix to all sites..."
    for site_dir in sites/*/; do
        site=$(basename "$site_dir")
        if [ -f "$site_dir/site_config.json" ]; then
            echo "Processing site: $site"
            fix_table "$site" "tabCustoms Rate"
            fix_table "$site" "tabSea Freight Rate"
            fix_table "$site" "tabAir Freight Rate"
            echo ""
        fi
    done
else
    echo "Applying fix to site: $SITE"
    fix_table "$SITE" "tabCustoms Rate"
    fix_table "$SITE" "tabSea Freight Rate"
    fix_table "$SITE" "tabAir Freight Rate"
fi

echo ""
echo "=== Verification ==="
if [ "$SITE" = "all" ]; then
    for site_dir in sites/*/; do
        site=$(basename "$site_dir")
        if [ -f "$site_dir/site_config.json" ]; then
            echo "Site: $site"
            bench --site $site mariadb -e "
                SELECT 
                    'Customs Rate' as table_name,
                    CASE WHEN COUNT(*) = 3 THEN '✓ OK' ELSE '✗ Missing columns' END as status
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'tabCustoms Rate' 
                AND COLUMN_NAME IN ('parent', 'parentfield', 'parenttype')
                UNION ALL
                SELECT 
                    'Sea Freight Rate' as table_name,
                    CASE WHEN COUNT(*) = 3 THEN '✓ OK' ELSE '✗ Missing columns' END as status
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'tabSea Freight Rate' 
                AND COLUMN_NAME IN ('parent', 'parentfield', 'parenttype')
                UNION ALL
                SELECT 
                    'Air Freight Rate' as table_name,
                    CASE WHEN COUNT(*) = 3 THEN '✓ OK' ELSE '✗ Missing columns' END as status
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'tabAir Freight Rate' 
                AND COLUMN_NAME IN ('parent', 'parentfield', 'parenttype');
            " 2>&1 | tail -3
            echo ""
        fi
    done
else
    echo "Verifying fix for site: $SITE"
    bench --site $SITE mariadb -e "
        SELECT 
            TABLE_NAME,
            CASE WHEN COUNT(*) = 3 THEN '✓ OK' ELSE '✗ Missing columns' END as status
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME IN ('tabCustoms Rate', 'tabSea Freight Rate', 'tabAir Freight Rate')
        AND COLUMN_NAME IN ('parent', 'parentfield', 'parenttype')
        GROUP BY TABLE_NAME;
    " 2>&1 | tail -3
fi

echo ""
echo "=== Fix completed ==="
echo "You may need to restart the bench: bench restart"
