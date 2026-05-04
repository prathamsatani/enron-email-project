-- Enron Email Dataset - SQLite Schema
-- Normalized design for email storage with support for duplicate detection

-- Main emails table
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    date DATETIME,
    from_address TEXT NOT NULL,
    subject TEXT,
    body TEXT,
    source_file TEXT NOT NULL,
    content_type TEXT,
    has_attachment BOOLEAN DEFAULT FALSE,
    forwarded_content TEXT,
    quoted_content TEXT,
    headings TEXT,
    x_folder TEXT,
    x_origin TEXT,
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of TEXT REFERENCES emails(message_id),
    similarity_score REAL,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Recipients table (normalized for to/cc/bcc)
CREATE TABLE IF NOT EXISTS recipients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL,
    email_address TEXT NOT NULL,
    recipient_type TEXT NOT NULL CHECK(recipient_type IN ('to', 'cc', 'bcc')),
    FOREIGN KEY (message_id) REFERENCES emails(message_id),
    UNIQUE(message_id, email_address, recipient_type)
);

-- Notification send log
CREATE TABLE IF NOT EXISTS notification_sent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    duplicate_message_id TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    sent_at DATETIME,
    status TEXT CHECK(status IN ('sent', 'failed', 'pending')),
    error_message TEXT,
    FOREIGN KEY (duplicate_message_id) REFERENCES emails(message_id)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_email_date ON emails(date);
CREATE INDEX IF NOT EXISTS idx_email_from ON emails(from_address);
CREATE INDEX IF NOT EXISTS idx_email_subject ON emails(subject);
CREATE INDEX IF NOT EXISTS idx_email_message_id ON emails(message_id);
CREATE INDEX IF NOT EXISTS idx_email_is_duplicate ON emails(is_duplicate);
CREATE INDEX IF NOT EXISTS idx_email_duplicate_of ON emails(duplicate_of);
CREATE INDEX IF NOT EXISTS idx_email_notification_sent ON emails(notification_sent);

CREATE INDEX IF NOT EXISTS idx_recipients_message_id ON recipients(message_id);
CREATE INDEX IF NOT EXISTS idx_recipients_email ON recipients(email_address);
CREATE INDEX IF NOT EXISTS idx_recipients_type ON recipients(recipient_type);

CREATE INDEX IF NOT EXISTS idx_notification_duplicate_msg ON notification_sent(duplicate_message_id);
CREATE INDEX IF NOT EXISTS idx_notification_status ON notification_sent(status);
