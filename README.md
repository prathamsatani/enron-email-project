# Enron Email Extraction & Deduplication Pipeline

An AI-assisted end-to-end data engineering pipeline that processes the Enron Email Dataset to extract structured fields, detect duplicates, and send automated notifications via MCP.

## Overview

This project demonstrates leveraging AI tools (Claude Code) to build a production-grade data pipeline that:

1. **Parses raw RFC 2822 email files** with robust error handling
2. **Extracts and normalizes** 16 structured fields (mandatory + optional)
3. **Stores emails** in a normalized SQLite database
4. **Detects duplicate emails** using fuzzy matching (90%+ body similarity)
5. **Flags duplicates** and sends automated notifications via Gmail MCP
6. **Generates comprehensive reports** on extraction, duplicates, and notifications

## Dataset

**Source**: Enron Email Dataset (CMU)  
**Size**: 500,000+ emails across 150 employee mailboxes  
**Format**: Nested RFC 2822 plain-text files  
**Download**: https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz

For this project, only 5-10 employee mailboxes (minimum 10,000 emails) are required.

## Project Structure

```
├── src/
│   ├── __init__.py
│   ├── email_parser.py              # RFC 2822 parsing with field extraction
│   ├── database.py                  # SQLite schema and storage layer
│   ├── duplicate_detector.py        # Fuzzy duplicate detection
│   ├── notification_service.py      # MCP Gmail integration
│   └── pipeline.py                  # Pipeline orchestration
├── main.py                          # Entry point (single command execution)
├── schema.sql                       # Database schema
├── sample_queries.sql               # 10+ example queries
├── mcp_config.json.example          # MCP server configuration template
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
├── AI_USAGE.md                      # Detailed AI tool usage documentation
└── README.md                        # This file
```

## Installation

### Prerequisites

- Python 3.10+
- pip package manager
- Virtual environment (recommended)

### Setup Steps

1. **Clone repository and navigate to project**
   ```bash
   cd d:\Projects\enron-email-project
   ```

2. **Create and activate virtual environment** (if needed)
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # On Windows
   source .venv/bin/activate # On macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Prepare Enron dataset** (one-time)
   ```bash
   mkdir -p data
   wget https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz -O data/enron_mail_20150507.tar.gz
   tar -xzf data/enron_mail_20150507.tar.gz -C data/
   # or use a smaller subset for testing
   ```

   > **Windows note**: The Enron archive contains email files named with a trailing
   > period (e.g. `1.`, `21.`) — a valid Unix filename that Windows cannot open
   > through its normal path API.  The pipeline handles this automatically using the
   > `\\?\` extended-path prefix, so no manual renaming is needed.

5. **Configure Gmail MCP** (for email sending)
   - Copy `mcp_config.json.example` to `mcp_config.json`
   - Update Gmail credentials and server URL
   - For now, use dry-run mode (default) to generate draft emails

## Usage

### Basic Usage (Extract, Store, Detect Duplicates)

```bash
python main.py \
    --maildir-path ./data/enron_mail \
    --db-path ./data/output/database.db
```

This will:
- Parse all emails in maildir
- Store parsed data in SQLite database
- Detect duplicates using fuzzy matching
- Generate draft notification emails (no actual sending)
- Produce statistics and reports

### Advanced Usage (With Live Email Sending)

```bash
python main.py \
    --maildir-path ./data/enron_mail \
    --db-path ./data/output/database.db \
    --send-live
```

**Note**: The `--send-live` flag requires proper MCP Gmail server setup and credentials.

### Custom Error Log Path

```bash
python main.py \
    --maildir-path ./data/enron_mail \
    --db-path ./data/output/database.db \
    --error-log ./logs/parse_errors.txt
```

## Output Files

After running the pipeline, generated files appear in `data/output/`:

| File | Description |
|------|-------------|
| `database.db` | SQLite database with all extracted emails and metadata |
| `error_log.txt` | List of parsing failures with reasons |
| `duplicates_report.csv` | CSV report of all detected duplicates with similarity scores |
| `send_log.csv` | Log of notification emails (send status, timestamps) |
| `replies/` | Draft notification emails (one .eml per duplicate) |

## Database Queries

Run sample queries to explore the data:

```bash
sqlite3 data/output/database.db < sample_queries.sql
```

Example queries included:
- Top 10 email senders by frequency
- Emails within a date range
- Emails with CC recipients
- Duplicate group analysis
- Domain distribution
- Forwarded vs. original emails
- And more...

## Field Definitions

### Mandatory Fields (Must Extract)

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | STRING (unique) | RFC 2822 Message-ID header |
| `date` | DATETIME | Sent timestamp (normalized to UTC) |
| `from_address` | STRING | Sender email address |
| `to_addresses` | LIST[STRING] | Recipients (To field) |
| `subject` | STRING | Subject line |
| `body` | TEXT | Email body content |
| `source_file` | STRING | Relative path to original file |

### Optional Fields (Extract If Present)

| Field | Type | Description |
|-------|------|-------------|
| `cc_addresses` | LIST[STRING] | CC recipients |
| `bcc_addresses` | LIST[STRING] | BCC recipients |
| `x_from` | STRING | X-From display name |
| `x_to` | STRING | X-To header value |
| `x_cc` | STRING | X-Cc header value |
| `x_bcc` | STRING | X-Bcc header value |
| `x_folder` | STRING | Mailbox folder indicator |
| `x_origin` | STRING | Message origin |
| `content_type` | STRING | MIME content type |
| `has_attachment` | BOOLEAN | Indicates attachments |
| `forwarded_content` | TEXT | Extracted forwarded message section |
| `quoted_content` | TEXT | Extracted quoted reply section |
| `headings` | TEXT | Email body headings |

## Duplicate Detection Algorithm

Duplicates are identified by:

1. **Matching sender** (`from_address`)
2. **Matching subject** (after normalizing Re:/Fwd: prefixes)
3. **90%+ body content similarity** (using `difflib.SequenceMatcher`)

Within a duplicate group:
- **Earliest email** by timestamp = original (kept)
- **Latest email(s)** = duplicate(s) (flagged)
- Database column `is_duplicate=TRUE` and `duplicate_of=<original_id>`

## Architecture Decisions

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Email Parsing | Python `email` stdlib | RFC 2822 compliant, no external dependencies |
| Date Normalization | `dateutil.parser` | Handles diverse timezone formats |
| Fuzzy Matching | `difflib.SequenceMatcher` | Fast, accurate similarity scoring |
| Database | SQLite | Portable, single-file, no server setup |
| MCP Integration | Gmail MCP Server | Standardized protocol for external services |
| Normalization | Separate recipients table | Proper 3NF design for to/cc/bcc |

## Error Handling

The pipeline is designed to be **resilient to malformed input**:

- ✅ Skips emails with unparseable headers
- ✅ Handles encoding errors gracefully
- ✅ Recovers from missing optional fields
- ✅ Logs all failures with specific reasons
- ✅ Never crashes on individual email errors
- ✅ Continues processing remaining emails
- ✅ Opens files with trailing-period names on Windows (e.g. `21.`) via `\\?\` extended-path prefix

All parse failures are logged to `error_log.txt` with:
- File path
- Specific error reason
- Field causing the issue (if applicable)

## Testing the Pipeline

### Quick Test (Small Dataset)

```bash
# Select 1-2 employee mailboxes for testing (~5k emails)
mkdir -p data/test_data/maildir

# Copy a few mailbox directories from extracted enron data
cp -r data/enron_mail/maildir/user1 data/test_data/maildir/
cp -r data/enron_mail/maildir/user2 data/test_data/maildir/

# Run pipeline on test data
python main.py \
    --maildir-path ./data/test_data/maildir \
    --db-path ./data/test_output/database.db

# Verify outputs
ls -lh data/test_output/
sqlite3 data/test_output/database.db "SELECT COUNT(*) as email_count FROM emails;"
```

### Integration Tests

Check that:
1. Database is created with correct schema
2. All emails are parsed and stored (check counts)
3. Duplicates are detected correctly
4. Field completeness is above 80% for mandatory fields
5. Reports are generated in correct format

## Performance Notes

- **Parsing**: ~100-200 emails/second (depends on disk I/O)
- **Full Dataset**: 500,000 emails ≈ 30-50 minutes
- **Duplicate Detection**: O(n²) complexity, scales with email count
- **Database**: Indexes optimize common queries

## Reproducibility

The pipeline is fully reproducible with a single command:

```bash
# This produces identical results on any system with the same input data
python main.py --maildir-path ./data/enron_mail --db-path ./data/output/database.db
```

All randomness is eliminated; results are deterministic.

## Dependencies

See `requirements.txt` for complete list. Key packages:

- `python-dateutil` - Timezone-aware date parsing
- `fuzzywuzzy` - Fuzzy string matching (optional enhancement)
- `email-validator` - Email address validation

Standard library modules used:
- `email` (RFC 2822 parsing)
- `sqlite3` (database)
- `difflib` (similarity scoring)
- `re` (pattern matching)
- `argparse` (CLI)
- `logging` (diagnostics)

## Troubleshooting

### Database Lock Error
```
sqlite3.OperationalError: database is locked
```
**Solution**: Close any other processes accessing the database; wait a few seconds and retry.

### Memory Issues with Large Datasets
**Solution**: Process in batches or increase available RAM.

### Encoding Errors
**Solution**: Pipeline handles UTF-8/Latin1 encoding automatically; check error log for specific files.

### Gmail MCP Connection Failed
**Solution**: Verify MCP server is running on correct port; check credentials in mcp_config.json.

### All emails fail with "No such file or directory" on Windows

```text
Failed to parse ...\21.: [Errno 2] No such file or directory: '...\21.'
```

**Cause**: The Enron archive stores email files with trailing periods (e.g. `21.`).
Windows silently strips trailing periods from paths in its normal file API, making
the file unreachable.  
**Solution**: Already handled — `email_parser.py` detects this condition at runtime
and re-opens the file using the `\\?\` extended-path prefix, which bypasses Windows
path normalization and reaches the file as-is.  No user action is required.

## Future Enhancements

- [ ] Parallel email parsing for faster processing
- [ ] Advanced ML-based duplicate detection
- [ ] Web UI for exploring results
- [ ] Incremental processing (append new emails)
- [ ] Export to CSV/JSON formats
- [ ] Automated scheduled runs

## License & Attribution

This project is part of an academic assignment demonstrating AI-assisted development using Claude Code.

Dataset: Enron Email Dataset (CMU Computer Science Department)

## Contact & Support

For issues or questions, refer to the detailed AI tool usage documentation in `AI_USAGE.md`.

---

**Last Updated**: 2026-04-27  
**Status**: Ready for testing and evaluation
