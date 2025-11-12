-- Immediate fix for Item deletion error
-- Run this on the server with the error: atnph.s.frappe.cloud
-- Usage: bench --site atnph.s.frappe.cloud mariadb < fix_item_deletion_immediate.sql

-- Fix Customs Rate table
ALTER TABLE `tabCustoms Rate` 
ADD COLUMN IF NOT EXISTS `parent` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS `parentfield` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS `parenttype` VARCHAR(140) NULL DEFAULT NULL;

-- Add index if it doesn't exist
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics 
               WHERE table_schema = DATABASE() 
               AND table_name = 'tabCustoms Rate' 
               AND index_name = 'parent');
SET @sqlstmt := IF(@exist = 0, 
    'ALTER TABLE `tabCustoms Rate` ADD INDEX `parent` (`parent`)', 
    'SELECT ''Index already exists''');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Fix Sea Freight Rate table
ALTER TABLE `tabSea Freight Rate` 
ADD COLUMN IF NOT EXISTS `parent` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS `parentfield` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS `parenttype` VARCHAR(140) NULL DEFAULT NULL;

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics 
               WHERE table_schema = DATABASE() 
               AND table_name = 'tabSea Freight Rate' 
               AND index_name = 'parent');
SET @sqlstmt := IF(@exist = 0, 
    'ALTER TABLE `tabSea Freight Rate` ADD INDEX `parent` (`parent`)', 
    'SELECT ''Index already exists''');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Fix Air Freight Rate table
ALTER TABLE `tabAir Freight Rate` 
ADD COLUMN IF NOT EXISTS `parent` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS `parentfield` VARCHAR(140) NULL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS `parenttype` VARCHAR(140) NULL DEFAULT NULL;

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics 
               WHERE table_schema = DATABASE() 
               AND table_name = 'tabAir Freight Rate' 
               AND index_name = 'parent');
SET @sqlstmt := IF(@exist = 0, 
    'ALTER TABLE `tabAir Freight Rate` ADD INDEX `parent` (`parent`)', 
    'SELECT ''Index already exists''');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

