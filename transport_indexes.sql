-- Transport Module - Database Index Optimization Script
-- Generated: October 1, 2025
-- Execute this script during low-traffic periods
-- Estimated time: 5-30 minutes depending on data volume

-- ============================================
-- CRITICAL INDEXES (Phase 1)
-- ============================================

-- 1. Transport Leg - Run Sheet & Date Filtering
-- Used by: Plan allocation, leg queries
-- Impact: 10-50x faster
ALTER TABLE `tabTransport Leg` 
ADD INDEX IF NOT EXISTS idx_runsheet_date_status (run_sheet, date, docstatus);

-- 2. Transport Leg - Job Reference
-- Used by: Job leg lookups, reporting
-- Impact: 5-10x faster
ALTER TABLE `tabTransport Leg` 
ADD INDEX IF NOT EXISTS idx_transport_job (transport_job);

-- 3. Run Sheet - Status & Vehicle
-- Used by: Vehicle availability checks
-- Impact: 8-15x faster
ALTER TABLE `tabRun Sheet` 
ADD INDEX IF NOT EXISTS idx_status_vehicle (status, vehicle);

-- 4. Transport Vehicle - Telematics Lookup
-- Used by: Telematics data ingestion
-- Impact: 20-50x faster
ALTER TABLE `tabTransport Vehicle` 
ADD INDEX IF NOT EXISTS idx_telematics_lookup (telematics_provider, telematics_external_id);

-- ============================================
-- HIGH PRIORITY INDEXES (Phase 2)
-- ============================================

-- 5. Telematics Position - Vehicle & Timestamp
-- Used by: Latest position queries
-- Impact: 10-20x faster
ALTER TABLE `tabTelematics Position` 
ADD INDEX IF NOT EXISTS idx_vehicle_ts (vehicle, ts DESC);

-- 6. Transport Leg - Sales Invoice
-- Used by: Billing, invoice lookups
-- Impact: 5-8x faster
ALTER TABLE `tabTransport Leg` 
ADD INDEX IF NOT EXISTS idx_sales_invoice (sales_invoice);

-- 7. Run Sheet Leg - Transport Leg Reference
-- Used by: Run sheet rendering, joins
-- Impact: 5-10x faster  
ALTER TABLE `tabRun Sheet Leg` 
ADD INDEX IF NOT EXISTS idx_transport_leg (transport_leg);

-- 8. Transport Leg - Date Range with Priority
-- Used by: Plan allocation sorting
-- Impact: 15-30x faster
ALTER TABLE `tabTransport Leg` 
ADD INDEX IF NOT EXISTS idx_date_priority_order (date, priority, `order`);

-- ============================================
-- ADDITIONAL USEFUL INDEXES (Phase 3)
-- ============================================

-- 9. Transport Order - Status & Date
-- Used by: Order filtering and reporting
ALTER TABLE `tabTransport Order` 
ADD INDEX IF NOT EXISTS idx_status_date (status, transaction_date);

-- 10. Transport Job - Status & Date
-- Used by: Job filtering and dashboard
ALTER TABLE `tabTransport Job` 
ADD INDEX IF NOT EXISTS idx_status_date (status, date);

-- 11. Run Sheet - Date & Status
-- Used by: Daily operations dashboard
ALTER TABLE `tabRun Sheet` 
ADD INDEX IF NOT EXISTS idx_date_status (date, status);

-- 12. Telematics Event - Vehicle & Timestamp
-- Used by: Event history queries
ALTER TABLE `tabTelematics Event` 
ADD INDEX IF NOT EXISTS idx_vehicle_ts (vehicle, ts DESC);

-- 13. Transport Leg - Facility Lookups
-- Used by: Facility-based queries
ALTER TABLE `tabTransport Leg` 
ADD INDEX IF NOT EXISTS idx_facility_from (facility_type_from, facility_from);

ALTER TABLE `tabTransport Leg` 
ADD INDEX IF NOT EXISTS idx_facility_to (facility_type_to, facility_to);

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check index creation
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    COLUMN_NAME,
    SEQ_IN_INDEX,
    CARDINALITY
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME LIKE 'tabTransport%'
AND INDEX_NAME LIKE 'idx_%'
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

-- Check index sizes
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    ROUND(STAT_VALUE * @@innodb_page_size / 1024 / 1024, 2) AS size_mb
FROM mysql.innodb_index_stats
WHERE DATABASE_NAME = DATABASE()
AND TABLE_NAME LIKE 'tabTransport%'
AND INDEX_NAME LIKE 'idx_%'
GROUP BY TABLE_NAME, INDEX_NAME;

-- ============================================
-- NOTES
-- ============================================

/*
1. IF NOT EXISTS syntax requires MySQL 5.7.8+ / MariaDB 10.1.4+
   If your version doesn't support it, remove "IF NOT EXISTS"
   
2. Index creation is online in MySQL 5.6+ / MariaDB 10.0+
   But may still cause brief locks. Run during maintenance window.
   
3. Monitor index usage after 1 week:
   
   SELECT 
       TABLE_NAME,
       INDEX_NAME,
       ROWS_READ
   FROM performance_schema.table_statistics
   WHERE TABLE_NAME LIKE 'tabTransport%';
   
4. If an index shows zero usage after 2 weeks, consider dropping it:
   
   ALTER TABLE `tabTransport Leg` DROP INDEX idx_unused_index;
   
5. Keep original indexes - don't drop them unless they're truly redundant.

6. After adding indexes, analyze tables for optimal query planning:
   
   ANALYZE TABLE `tabTransport Leg`;
   ANALYZE TABLE `tabRun Sheet`;
   ANALYZE TABLE `tabTransport Vehicle`;
*/

