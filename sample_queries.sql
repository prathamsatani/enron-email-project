-- Enron Email Dataset - Sample Queries
-- Demonstrates key database functionality

-- ============================================================================
-- Sample Query 1: Count emails per sender (Top 10)
-- Purpose: Identify most active email senders
-- ============================================================================
SELECT
    from_address,
    COUNT(*) as email_count,
    COUNT(CASE WHEN is_duplicate = TRUE THEN 1 END) as duplicate_count
FROM emails
GROUP BY from_address
ORDER BY email_count DESC
LIMIT 10;


-- ============================================================================
-- Sample Query 2: Find emails in a date range
-- Purpose: Query emails within a specific time period
-- ============================================================================
SELECT
    message_id,
    date,
    from_address,
    subject,
    is_duplicate
FROM emails
WHERE date BETWEEN '2000-01-01' AND '2002-12-31'
ORDER BY date DESC
LIMIT 20;


-- ============================================================================
-- Sample Query 3: Find emails with CC recipients
-- Purpose: Identify emails that were CC'd to multiple parties
-- ============================================================================
SELECT
    e.message_id,
    e.from_address,
    e.subject,
    e.date,
    GROUP_CONCAT(r.email_address, '; ') as cc_recipients
FROM emails e
JOIN recipients r ON e.message_id = r.message_id
WHERE r.recipient_type = 'cc'
GROUP BY e.message_id
ORDER BY e.date DESC
LIMIT 20;


-- ============================================================================
-- Sample Query 4: Find duplicate groups (clusters)
-- Purpose: Show all emails flagged as duplicates and their originals
-- ============================================================================
SELECT
    e.message_id as duplicate_msg_id,
    orig.message_id as original_msg_id,
    e.from_address,
    e.subject,
    e.date as duplicate_date,
    orig.date as original_date,
    (julianday(e.date) - julianday(orig.date)) as days_apart
FROM emails e
LEFT JOIN emails orig ON e.duplicate_of = orig.id
WHERE e.is_duplicate = TRUE
ORDER BY e.date DESC
LIMIT 25;


-- ============================================================================
-- Sample Query 5: Statistics by domain
-- Purpose: Count emails per email domain
-- ============================================================================
SELECT
    SUBSTR(from_address, INSTR(from_address, '@') + 1) as domain,
    COUNT(*) as email_count,
    COUNT(DISTINCT from_address) as unique_senders
FROM emails
WHERE from_address IS NOT NULL
GROUP BY domain
ORDER BY email_count DESC
LIMIT 15;


-- ============================================================================
-- Sample Query 6: Find emails with attachments
-- Purpose: Identify emails containing attachments
-- ============================================================================
SELECT
    message_id,
    from_address,
    subject,
    date,
    content_type
FROM emails
WHERE has_attachment = TRUE
ORDER BY date DESC
LIMIT 20;


-- ============================================================================
-- Sample Query 7: Recipients distribution
-- Purpose: See how many emails each recipient received
-- ============================================================================
SELECT
    r.email_address,
    r.recipient_type,
    COUNT(*) as received_count
FROM recipients r
GROUP BY r.email_address, r.recipient_type
ORDER BY received_count DESC
LIMIT 15;


-- ============================================================================
-- Sample Query 8: Track notifications sent
-- Purpose: See which duplicates had notifications sent
-- ============================================================================
SELECT
    ns.duplicate_message_id,
    e.from_address,
    e.subject,
    ns.recipient_email,
    ns.status,
    ns.sent_at
FROM notification_sent ns
LEFT JOIN emails e ON ns.duplicate_message_id = e.message_id
ORDER BY ns.sent_at DESC
LIMIT 20;


-- ============================================================================
-- Sample Query 9: Forwarded vs Original emails
-- Purpose: Count forwarded messages
-- ============================================================================
SELECT
    COUNT(*) as total_emails,
    SUM(CASE WHEN forwarded_content IS NOT NULL THEN 1 ELSE 0 END) as forwarded_emails,
    SUM(CASE WHEN quoted_content IS NOT NULL THEN 1 ELSE 0 END) as quoted_emails,
    SUM(CASE WHEN has_attachment = TRUE THEN 1 ELSE 0 END) as emails_with_attachments
FROM emails;


-- ============================================================================
-- Sample Query 10: Subject line analysis (common subjects)
-- Purpose: Find most common email subjects
-- ============================================================================
SELECT
    subject,
    COUNT(*) as frequency,
    COUNT(DISTINCT from_address) as unique_senders
FROM emails
WHERE subject IS NOT NULL AND subject != ''
GROUP BY subject
ORDER BY frequency DESC
LIMIT 20;
