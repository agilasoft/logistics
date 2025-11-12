-- Run this SQL directly on Frappe Cloud database
-- This will fix the Item deletion error immediately

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

