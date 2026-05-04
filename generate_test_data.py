#!/usr/bin/env python3
"""
Generate synthetic Enron-style test emails for pipeline demonstration.

Creates 5 user mailboxes with 60+ emails total, including intentional duplicates,
CC/BCC examples, forwarded messages, and various edge cases.

Usage:
    python generate_test_data.py [--output-dir ./data/test_maildir]
"""

import os
import argparse
from pathlib import Path

# ── Email templates ────────────────────────────────────────────────────────────

USERS = [
    {
        "name": "lay-k",
        "email": "kenneth.lay@enron.com",
        "display": "Kenneth Lay",
    },
    {
        "name": "skilling-j",
        "email": "jeffrey.skilling@enron.com",
        "display": "Jeffrey Skilling",
    },
    {
        "name": "kaminski-v",
        "email": "vince.kaminski@enron.com",
        "display": "Vince Kaminski",
    },
    {
        "name": "dasovich-j",
        "email": "jeff.dasovich@enron.com",
        "display": "Jeff Dasovich",
    },
    {
        "name": "allen-p",
        "email": "phillip.allen@enron.com",
        "display": "Phillip Allen",
    },
]

EMAILS = [
    # ── lay-k emails ──────────────────────────────────────────────────────────
    {
        "user": "lay-k", "folder": "inbox", "id": 1,
        "msg_id": "<A001@enron.com>",
        "date": "Mon, 15 Jan 2001 09:30:00 -0600",
        "from": "kenneth.lay@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "subject": "Q4 Results Overview",
        "body": "Jeff,\n\nPlease review the Q4 results before the board meeting on Thursday.\nThe numbers look strong across all divisions.\n\nKen",
    },
    {
        "user": "lay-k", "folder": "inbox", "id": 2,
        "msg_id": "<A002@enron.com>",
        "date": "Mon, 15 Jan 2001 10:15:00 -0600",
        "from": "jeffrey.skilling@enron.com",
        "to": "kenneth.lay@enron.com, vince.kaminski@enron.com",
        "cc": "phillip.allen@enron.com",
        "subject": "Re: Q4 Results Overview",
        "body": "Ken,\n\nI have reviewed the Q4 numbers. The trading division is particularly strong.\nI will present the full breakdown at Thursday's meeting.\n\nJeff",
    },
    {
        "user": "lay-k", "folder": "inbox", "id": 3,
        "msg_id": "<A003@enron.com>",
        "date": "Tue, 16 Jan 2001 08:00:00 -0600",
        "from": "kenneth.lay@enron.com",
        "to": "all-employees@enron.com",
        "subject": "Company Update - January 2001",
        "body": "Dear Enron Employees,\n\nI am pleased to share that our company continues to perform exceptionally well.\nOur energy trading business has exceeded all expectations for the quarter.\n\nWe remain committed to our core values of respect, integrity, communication, and excellence.\n\nThank you for your continued dedication.\n\nKenneth Lay\nChairman and CEO",
    },
    # DUPLICATE of A003 (same sender, same subject, very similar body, later date)
    {
        "user": "lay-k", "folder": "sent", "id": 4,
        "msg_id": "<A003B@enron.com>",
        "date": "Tue, 16 Jan 2001 08:05:00 -0600",
        "from": "kenneth.lay@enron.com",
        "to": "all-employees@enron.com",
        "subject": "Company Update - January 2001",
        "body": "Dear Enron Employees,\n\nI am pleased to share that our company continues to perform exceptionally well.\nOur energy trading business has exceeded all expectations for the quarter.\n\nWe remain committed to our core values of respect, integrity, communication, and excellence.\n\nThank you for your continued dedication.\n\nKenneth Lay\nChairman and CEO",
    },
    {
        "user": "lay-k", "folder": "inbox", "id": 5,
        "msg_id": "<A004@enron.com>",
        "date": "Wed, 17 Jan 2001 14:00:00 -0600",
        "from": "board@enron.com",
        "to": "kenneth.lay@enron.com",
        "subject": "Board Meeting Agenda - January 18",
        "body": "Ken,\n\nAgenda for tomorrow's board meeting:\n1. Q4 financial review\n2. Strategic initiatives for 2001\n3. Executive compensation review\n4. Shareholder communication strategy\n\nPlease confirm your attendance.\n\nBoard Secretary",
    },
    {
        "user": "lay-k", "folder": "inbox", "id": 6,
        "msg_id": "<A005@enron.com>",
        "date": "Thu, 18 Jan 2001 09:00:00 -0600",
        "from": "pr@enron.com",
        "to": "kenneth.lay@enron.com",
        "subject": "Media Briefing Materials",
        "body": "Ken,\n\nAttached are the talking points for tomorrow's analyst call.\nKey messages:\n- Record revenue growth\n- Expanding into new markets\n- Strong balance sheet\n\nLet me know if you'd like any changes.\n\nCommunications Team",
    },
    {
        "user": "lay-k", "folder": "inbox", "id": 7,
        "msg_id": "<A006@enron.com>",
        "date": "Fri, 19 Jan 2001 11:30:00 -0600",
        "from": "vince.kaminski@enron.com",
        "to": "kenneth.lay@enron.com",
        "cc": "jeffrey.skilling@enron.com",
        "subject": "Risk Management Report - January",
        "body": "Ken,\n\nPlease find attached the monthly risk management report.\nKey highlights:\n- VaR within acceptable limits\n- California power market positions reviewed\n- Counterparty exposure reduced by 12%\n\nVince Kaminski\nVP Risk Management",
    },
    {
        "user": "lay-k", "folder": "inbox", "id": 8,
        "msg_id": "<A007@enron.com>",
        "date": "Mon, 22 Jan 2001 08:45:00 -0600",
        "from": "legal@enron.com",
        "to": "kenneth.lay@enron.com",
        "subject": "Regulatory Filing Deadline",
        "body": "Ken,\n\nReminder: SEC 10-K filing deadline is February 15.\nLegal is coordinating with Finance to compile all required disclosures.\nWe anticipate no issues meeting the deadline.\n\nLegal Department",
    },
    {
        "user": "lay-k", "folder": "inbox", "id": 9,
        "msg_id": "<A008@enron.com>",
        "date": "Tue, 23 Jan 2001 15:00:00 -0600",
        "from": "jeffrey.skilling@enron.com",
        "to": "kenneth.lay@enron.com",
        "subject": "California Power Crisis - Update",
        "body": "Ken,\n\nThe California power situation continues to evolve.\nOur trading team has been closely monitoring market dynamics.\nI recommend we prepare a public statement addressing our role in the market.\n\nJeff",
    },
    {
        "user": "lay-k", "folder": "inbox", "id": 10,
        "msg_id": "<A009@enron.com>",
        "date": "Wed, 24 Jan 2001 10:00:00 -0600",
        "from": "analyst@enron.com",
        "to": "kenneth.lay@enron.com",
        "bcc": "cfo@enron.com",
        "subject": "Analyst Call Preparation",
        "body": "Ken,\n\nPreparation materials for the Q4 analyst call:\n- Earnings per share: $1.47 (vs $1.22 estimate)\n- Revenue: $100.8B (record)\n- EBITDA: $2.0B\n\nAntonio Moran\nInvestor Relations",
    },
    {
        "user": "lay-k", "folder": "inbox", "id": 11,
        "msg_id": "<A010@enron.com>",
        "date": "Thu, 25 Jan 2001 09:15:00 -0600",
        "from": "hr@enron.com",
        "to": "kenneth.lay@enron.com",
        "subject": "Executive Retention Program",
        "body": "Ken,\n\nFor your review: the updated executive retention package for top 50 officers.\nThe program includes:\n- Performance bonuses tied to stock price\n- Three-year vesting schedule\n- Change-of-control provisions\n\nHR Leadership",
    },
    {
        "user": "lay-k", "folder": "inbox", "id": 12,
        "msg_id": "<A011@enron.com>",
        "date": "Fri, 26 Jan 2001 16:00:00 -0600",
        "from": "trading@enron.com",
        "to": "kenneth.lay@enron.com, jeffrey.skilling@enron.com",
        "subject": "Weekly Trading Summary",
        "body": "Summary for week ending Jan 26, 2001:\n\nNatural Gas: +$45M\nElectricity: +$62M\nBroadband: -$3M\nTotal: +$104M\n\nStrong performance driven by volatility in western markets.\n\nTrading Operations",
    },

    # ── skilling-j emails ─────────────────────────────────────────────────────
    {
        "user": "skilling-j", "folder": "inbox", "id": 1,
        "msg_id": "<B001@enron.com>",
        "date": "Mon, 15 Jan 2001 11:00:00 -0600",
        "from": "jeffrey.skilling@enron.com",
        "to": "vince.kaminski@enron.com",
        "subject": "Risk Models Review",
        "body": "Vince,\n\nI need you to review our current VaR models given recent market volatility.\nPlease schedule a meeting this week.\n\nJeff",
    },
    {
        "user": "skilling-j", "folder": "inbox", "id": 2,
        "msg_id": "<B002@enron.com>",
        "date": "Mon, 15 Jan 2001 14:00:00 -0600",
        "from": "vince.kaminski@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "subject": "Re: Risk Models Review",
        "body": "Jeff,\n\nI can meet Wednesday at 2pm to review the VaR models.\nI will prepare a full stress-test analysis by then.\n\nVince",
    },
    {
        "user": "skilling-j", "folder": "inbox", "id": 3,
        "msg_id": "<B003@enron.com>",
        "date": "Tue, 16 Jan 2001 09:30:00 -0600",
        "from": "strategy@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "cc": "kenneth.lay@enron.com",
        "subject": "2001 Strategic Plan Draft",
        "body": "Jeff,\n\nAttached is the draft 2001 strategic plan for your review.\nKey initiatives:\n1. Expand broadband trading\n2. Enter water utilities market\n3. Grow international operations\n4. Improve capital efficiency\n\nStrategy Team",
    },
    {
        "user": "skilling-j", "folder": "sent", "id": 4,
        "msg_id": "<B004@enron.com>",
        "date": "Tue, 16 Jan 2001 16:00:00 -0600",
        "from": "jeffrey.skilling@enron.com",
        "to": "all-directors@enron.com",
        "subject": "Performance Review Process",
        "body": "Directors,\n\nAs we begin the year, I want to remind everyone of our rigorous performance evaluation process.\nThe bottom 15% of performers will be subject to reassignment or termination.\nThis process is what keeps Enron at the cutting edge.\n\nJeff Skilling\nPresident and COO",
    },
    {
        "user": "skilling-j", "folder": "inbox", "id": 5,
        "msg_id": "<B005@enron.com>",
        "date": "Wed, 17 Jan 2001 13:00:00 -0600",
        "from": "finance@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "subject": "SPE Structure Review",
        "body": "Jeff,\n\nThe finance team has completed its review of the special purpose entity structures.\nAll entities meet GAAP consolidation thresholds.\nThe external auditors have signed off on the approach.\n\nFinance",
    },
    {
        "user": "skilling-j", "folder": "inbox", "id": 6,
        "msg_id": "<B006@enron.com>",
        "date": "Wed, 17 Jan 2001 15:30:00 -0600",
        "from": "jeff.dasovich@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "subject": "California Legislative Update",
        "body": "Jeff,\n\nCalifornia legislators are pushing for a price cap on wholesale electricity.\nThis could significantly impact our western trading operations.\nI recommend we increase our government affairs presence in Sacramento.\n\nJeff D.",
    },
    # DUPLICATE of B006
    {
        "user": "skilling-j", "folder": "inbox", "id": 7,
        "msg_id": "<B006B@enron.com>",
        "date": "Wed, 17 Jan 2001 15:35:00 -0600",
        "from": "jeff.dasovich@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "subject": "California Legislative Update",
        "body": "Jeff,\n\nCalifornia legislators are pushing for a price cap on wholesale electricity.\nThis could significantly impact our western trading operations.\nI recommend we increase our government affairs presence in Sacramento.\n\nJeff D.",
    },
    {
        "user": "skilling-j", "folder": "inbox", "id": 8,
        "msg_id": "<B007@enron.com>",
        "date": "Thu, 18 Jan 2001 10:00:00 -0600",
        "from": "broadband@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "cc": "kenneth.lay@enron.com, vince.kaminski@enron.com",
        "subject": "Enron Broadband Q4 Update",
        "body": "Jeff,\n\nEnron Broadband Services Q4 Update:\n- Network capacity: 18,000 route miles\n- Active content deals: 23\n- Q4 revenue: $50M\n- Projection for 2001: $200M+\n\nWe are well-positioned for the broadband revolution.\n\nEBS Team",
    },
    {
        "user": "skilling-j", "folder": "inbox", "id": 9,
        "msg_id": "<B008@enron.com>",
        "date": "Fri, 19 Jan 2001 09:00:00 -0600",
        "from": "trading@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "subject": "Electricity Market Positions",
        "body": "Jeff,\n\nCurrent electricity forward positions summary:\n- Western region: long 2,400 MW\n- Texas: flat\n- Northeast: short 800 MW\n\nRecommendation: maintain current western exposure given supply constraints.\n\nTrading Desk",
    },
    {
        "user": "skilling-j", "folder": "inbox", "id": 10,
        "msg_id": "<B009@enron.com>",
        "date": "Mon, 22 Jan 2001 08:00:00 -0600",
        "from": "kenneth.lay@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "subject": "CEO Transition Planning",
        "body": "Jeff,\n\nAs we discussed, I would like to begin the formal CEO transition process.\nLet's schedule time this week to outline the transition timeline and communication strategy.\n\nKen",
    },

    # ── kaminski-v emails ─────────────────────────────────────────────────────
    {
        "user": "kaminski-v", "folder": "inbox", "id": 1,
        "msg_id": "<C001@enron.com>",
        "date": "Mon, 15 Jan 2001 08:00:00 -0600",
        "from": "vince.kaminski@enron.com",
        "to": "research@enron.com",
        "subject": "Volatility Model Update",
        "body": "Team,\n\nPlease update our electricity volatility models to incorporate the new\nCalifornia market data from Q4. The regime-switching model needs recalibration.\n\nVince",
    },
    {
        "user": "kaminski-v", "folder": "inbox", "id": 2,
        "msg_id": "<C002@enron.com>",
        "date": "Mon, 15 Jan 2001 13:00:00 -0600",
        "from": "research@enron.com",
        "to": "vince.kaminski@enron.com",
        "subject": "Re: Volatility Model Update",
        "body": "Vince,\n\nModel recalibration complete. Key findings:\n- Western electricity vol: 185% annualized\n- Gas-power correlation: 0.72\n- Jump frequency: 3.2 events per month\n\nPlease review the attached report.\n\nResearch Team",
    },
    {
        "user": "kaminski-v", "folder": "inbox", "id": 3,
        "msg_id": "<C003@enron.com>",
        "date": "Tue, 16 Jan 2001 10:00:00 -0600",
        "from": "mit.finance@mit.edu",
        "to": "vince.kaminski@enron.com",
        "subject": "Speaking Invitation - Energy Finance Symposium",
        "body": "Dear Dr. Kaminski,\n\nWe would like to invite you to speak at the MIT Energy Finance Symposium\non February 15, 2001.\n\nYour expertise in energy derivatives pricing would be invaluable to our audience\nof academics and practitioners.\n\nPlease let us know if you are available.\n\nMIT Sloan Finance Faculty",
    },
    {
        "user": "kaminski-v", "folder": "inbox", "id": 4,
        "msg_id": "<C004@enron.com>",
        "date": "Tue, 16 Jan 2001 14:30:00 -0600",
        "from": "vince.kaminski@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "cc": "kenneth.lay@enron.com",
        "subject": "Research Department 2001 Plan",
        "body": "Jeff,\n\nResearch Department priorities for 2001:\n1. Develop credit derivatives pricing framework\n2. Build weather derivatives model\n3. Improve real-time risk reporting\n4. Expand quantitative recruiting (target: 8 PhDs)\n\nVince Kaminski",
    },
    {
        "user": "kaminski-v", "folder": "inbox", "id": 5,
        "msg_id": "<C005@enron.com>",
        "date": "Wed, 17 Jan 2001 09:00:00 -0600",
        "from": "trading@enron.com",
        "to": "vince.kaminski@enron.com",
        "subject": "Exotic Options Pricing Request",
        "body": "Vince,\n\nWe need pricing on the following exotic options for a client proposal:\n- Asian calls on Henry Hub gas\n- Barrier options on western electricity\n- Weather derivatives for HDDs in Chicago\n\nCan your team turn these around by Friday?\n\nTrading Structuring",
    },
    # DUPLICATE of C005
    {
        "user": "kaminski-v", "folder": "inbox", "id": 6,
        "msg_id": "<C005B@enron.com>",
        "date": "Wed, 17 Jan 2001 09:02:00 -0600",
        "from": "trading@enron.com",
        "to": "vince.kaminski@enron.com",
        "subject": "Exotic Options Pricing Request",
        "body": "Vince,\n\nWe need pricing on the following exotic options for a client proposal:\n- Asian calls on Henry Hub gas\n- Barrier options on western electricity\n- Weather derivatives for HDDs in Chicago\n\nCan your team turn these around by Friday?\n\nTrading Structuring",
    },
    {
        "user": "kaminski-v", "folder": "inbox", "id": 7,
        "msg_id": "<C006@enron.com>",
        "date": "Wed, 17 Jan 2001 16:00:00 -0600",
        "from": "phd.recruit@enron.com",
        "to": "vince.kaminski@enron.com",
        "subject": "PhD Candidate Interview - Stochastic Calculus",
        "body": "Vince,\n\nCandidate: Dr. Elena Marchetti (Chicago, Mathematics)\nSpecialization: Stochastic PDEs and Monte Carlo methods\nInterview scheduled: January 25, 2:00 PM\n\nPlease review her thesis abstract before the interview.\n\nRecruiting Team",
    },
    {
        "user": "kaminski-v", "folder": "inbox", "id": 8,
        "msg_id": "<C007@enron.com>",
        "date": "Thu, 18 Jan 2001 11:00:00 -0600",
        "from": "vince.kaminski@enron.com",
        "to": "research@enron.com",
        "subject": "Re: Re: Volatility Model Update",
        "body": "Team,\n\nGood work on the recalibration. Please also run a backtesting analysis\ncovering January 2000 to present to validate the new parameters.\n\nVince",
    },
    {
        "user": "kaminski-v", "folder": "inbox", "id": 9,
        "msg_id": "<C008@enron.com>",
        "date": "Fri, 19 Jan 2001 14:00:00 -0600",
        "from": "legal@enron.com",
        "to": "vince.kaminski@enron.com",
        "subject": "ISDA Master Agreement Review",
        "body": "Vince,\n\nWe need your sign-off on the ISDA documentation for the new weather derivatives\nproducts before we can begin trading.\n\nPlease review Sections 14(a) and 14(b) covering calculation methodology.\n\nLegal Department",
    },
    {
        "user": "kaminski-v", "folder": "inbox", "id": 10,
        "msg_id": "<C009@enron.com>",
        "date": "Mon, 22 Jan 2001 09:30:00 -0600",
        "from": "vince.kaminski@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "subject": "California Crisis Risk Assessment",
        "body": "Jeff,\n\nBased on my team's analysis, the California power crisis poses the following risks:\n1. Regulatory backlash and potential price caps\n2. Counterparty credit exposure to California utilities\n3. Reputational risk from perceived market manipulation\n\nI recommend we immediately reduce our western power exposure.\n\nVince",
    },
    {
        "user": "kaminski-v", "folder": "inbox", "id": 11,
        "msg_id": "<C010@enron.com>",
        "date": "Tue, 23 Jan 2001 10:00:00 -0600",
        "from": "research@enron.com",
        "to": "vince.kaminski@enron.com",
        "cc": "jeffrey.skilling@enron.com",
        "subject": "Electricity Price Forecasting Model",
        "body": "Vince,\n\nNew electricity price forecasting model results:\n- 1-month forecast accuracy: 87%\n- 3-month forecast accuracy: 73%\n- Model significantly outperforms benchmark\n\nFull technical report attached.\n\nQuantitative Research",
    },
    {
        "user": "kaminski-v", "folder": "inbox", "id": 12,
        "msg_id": "<C011@enron.com>",
        "date": "Wed, 24 Jan 2001 13:00:00 -0600",
        "from": "conference@riskusa.com",
        "to": "vince.kaminski@enron.com",
        "subject": "Risk USA 2001 - Keynote Invitation",
        "body": "Dear Dr. Kaminski,\n\nWe are pleased to invite you to deliver a keynote address at Risk USA 2001\nin New York, March 5-7.\n\nYour work on energy derivatives has been highly influential.\nWe believe your perspective on managing energy market risks would be\nexcellent for our audience.\n\nBest regards,\nRisk USA Conference Committee",
    },

    # ── dasovich-j emails ─────────────────────────────────────────────────────
    {
        "user": "dasovich-j", "folder": "inbox", "id": 1,
        "msg_id": "<D001@enron.com>",
        "date": "Mon, 15 Jan 2001 07:30:00 -0800",
        "from": "jeff.dasovich@enron.com",
        "to": "gov.davis@ca.gov",
        "cc": "kenneth.lay@enron.com",
        "subject": "Meeting Request - Energy Crisis Solutions",
        "body": "Governor Davis,\n\nI am writing on behalf of Enron Corporation to request a meeting to discuss\npotential solutions to California's electricity crisis.\n\nWe believe market-based solutions, including long-term contracts, could\nprovide price stability while preserving competition.\n\nJeff Dasovich\nDirector, Government Affairs",
    },
    {
        "user": "dasovich-j", "folder": "inbox", "id": 2,
        "msg_id": "<D002@enron.com>",
        "date": "Mon, 15 Jan 2001 09:00:00 -0800",
        "from": "senator@ca.gov",
        "to": "jeff.dasovich@enron.com",
        "subject": "Senate Hearing on Energy Market Manipulation",
        "body": "Dear Mr. Dasovich,\n\nYou are hereby invited to testify before the California Senate Energy Committee\non February 1, 2001 regarding wholesale electricity market practices.\n\nPlease respond by January 25 to confirm your attendance.\n\nSenate Energy Committee",
    },
    {
        "user": "dasovich-j", "folder": "inbox", "id": 3,
        "msg_id": "<D003@enron.com>",
        "date": "Tue, 16 Jan 2001 10:30:00 -0800",
        "from": "jeff.dasovich@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "subject": "California Regulatory Risk - Urgent",
        "body": "Jeff,\n\nI have received notice that California regulators are investigating\n'possible' market manipulation by power traders.\n\nI strongly recommend:\n1. Legal review of all California trading strategies\n2. Proactive engagement with FERC\n3. Avoid any strategies that could be perceived as gaming\n\nThis is urgent. Can we talk today?\n\nJeff D.",
    },
    {
        "user": "dasovich-j", "folder": "inbox", "id": 4,
        "msg_id": "<D004@enron.com>",
        "date": "Tue, 16 Jan 2001 15:00:00 -0800",
        "from": "ferc@ferc.gov",
        "to": "jeff.dasovich@enron.com",
        "subject": "FERC Notice - Market Investigation",
        "body": "Dear Mr. Dasovich,\n\nThe Federal Energy Regulatory Commission has initiated an investigation into\nwholesale electricity market practices in the western United States.\n\nEnron is requested to preserve all relevant records and trading data\nfor the period January 2000 to present.\n\nFERC Staff",
    },
    {
        "user": "dasovich-j", "folder": "inbox", "id": 5,
        "msg_id": "<D005@enron.com>",
        "date": "Wed, 17 Jan 2001 08:00:00 -0800",
        "from": "jeff.dasovich@enron.com",
        "to": "pr@enron.com",
        "cc": "kenneth.lay@enron.com, jeffrey.skilling@enron.com",
        "subject": "Draft Press Statement - California",
        "body": "Team,\n\nDraft statement for review:\n\n'Enron is committed to fair and transparent energy markets.\nWe comply with all applicable laws and regulations.\nWe welcome any investigation that will confirm our practices are lawful.'\n\nPlease provide feedback by EOD.\n\nJeff D.",
    },
    {
        "user": "dasovich-j", "folder": "inbox", "id": 6,
        "msg_id": "<D006@enron.com>",
        "date": "Wed, 17 Jan 2001 14:00:00 -0800",
        "from": "legal@enron.com",
        "to": "jeff.dasovich@enron.com",
        "subject": "Document Hold Notice",
        "body": "Jeff,\n\nDue to the FERC investigation, we are implementing an immediate document hold.\nAll emails, trading records, and memos related to California operations\nmust be preserved.\n\nPlease inform your team immediately.\n\nLegal Department",
    },
    {
        "user": "dasovich-j", "folder": "inbox", "id": 7,
        "msg_id": "<D007@enron.com>",
        "date": "Thu, 18 Jan 2001 09:00:00 -0800",
        "from": "jeff.dasovich@enron.com",
        "to": "kenneth.lay@enron.com",
        "subject": "Governor Davis Meeting Confirmed",
        "body": "Ken,\n\nGovernor Davis has agreed to meet on January 26.\nThe agenda will focus on long-term contract solutions.\nI will bring talking points emphasizing market benefits.\n\nJeff D.",
    },
    {
        "user": "dasovich-j", "folder": "inbox", "id": 8,
        "msg_id": "<D008@enron.com>",
        "date": "Thu, 18 Jan 2001 16:00:00 -0800",
        "from": "whitehouse@eo.eop.gov",
        "to": "jeff.dasovich@enron.com",
        "subject": "National Energy Policy Development Group",
        "body": "Dear Mr. Dasovich,\n\nOn behalf of Vice President Cheney, you are invited to participate in\nthe National Energy Policy Development Group.\n\nYour expertise in energy markets would be valuable to the group's deliberations.\n\nOffice of the Vice President",
    },
    {
        "user": "dasovich-j", "folder": "inbox", "id": 9,
        "msg_id": "<D009@enron.com>",
        "date": "Fri, 19 Jan 2001 10:00:00 -0800",
        "from": "jeff.dasovich@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "cc": "kenneth.lay@enron.com",
        "subject": "Weekly Government Affairs Summary",
        "body": "Jeff,\n\nWeekly Government Affairs Update - Jan 19, 2001:\n\n1. California Senate hearing confirmed for Feb 1\n2. FERC investigation - preserving all records\n3. Governor Davis meeting set for Jan 26\n4. White House energy policy group invitation received\n5. Three new state regulatory actions filed this week\n\nJeff D.",
    },
    {
        "user": "dasovich-j", "folder": "inbox", "id": 10,
        "msg_id": "<D010@enron.com>",
        "date": "Mon, 22 Jan 2001 08:00:00 -0800",
        "from": "lobbyist@enron.com",
        "to": "jeff.dasovich@enron.com",
        "subject": "Congressional Contacts - Energy Bill Update",
        "body": "Jeff,\n\nUpdate on energy deregulation legislation:\n- HR 2024: favorable amendment passed committee\n- Senate version: still in markup\n- Key swing votes: senators from Michigan and Ohio\n\nI will continue working Senate contacts this week.\n\nGovernment Relations",
    },

    # ── allen-p emails ────────────────────────────────────────────────────────
    {
        "user": "allen-p", "folder": "inbox", "id": 1,
        "msg_id": "<E001@enron.com>",
        "date": "Mon, 15 Jan 2001 08:30:00 -0600",
        "from": "phillip.allen@enron.com",
        "to": "trading-desk@enron.com",
        "subject": "Natural Gas Trading Strategy - Q1 2001",
        "body": "Team,\n\nFor Q1 2001, we will focus on the following opportunities:\n1. Henry Hub basis trades\n2. Storage-related spreads\n3. Intraday volatility in Gulf Coast markets\n\nPosition limits remain unchanged. Please review the updated risk guidelines.\n\nPhillip Allen\nVP, Natural Gas Trading",
    },
    {
        "user": "allen-p", "folder": "inbox", "id": 2,
        "msg_id": "<E002@enron.com>",
        "date": "Mon, 15 Jan 2001 10:00:00 -0600",
        "from": "trading-desk@enron.com",
        "to": "phillip.allen@enron.com",
        "subject": "Gas Market Morning Report",
        "body": "Phillip,\n\nMorning Report - Jan 15, 2001:\n\nHenry Hub spot: $9.82/MMBtu (up $0.45)\nStorage: 2,842 Bcf (17% below 5-yr average)\nWeather: Cold front moving into Midwest this weekend\n\nRecommendation: Maintain long winter positions.\n\nTrading Desk",
    },
    {
        "user": "allen-p", "folder": "inbox", "id": 3,
        "msg_id": "<E003@enron.com>",
        "date": "Tue, 16 Jan 2001 09:00:00 -0600",
        "from": "phillip.allen@enron.com",
        "to": "counterparty-a@energy.com",
        "subject": "Gas Purchase Confirmation - Jan 2001",
        "body": "Dear Counterparty,\n\nThis confirms our agreement for the purchase of:\n- 50,000 MMBtu/day\n- Delivery: Henry Hub\n- Period: January 16-31, 2001\n- Price: $9.75/MMBtu\n\nPlease execute the ISDA confirmation by COB today.\n\nPhillip Allen\nEnron Gas Trading",
    },
    # DUPLICATE of E003
    {
        "user": "allen-p", "folder": "sent", "id": 4,
        "msg_id": "<E003B@enron.com>",
        "date": "Tue, 16 Jan 2001 09:03:00 -0600",
        "from": "phillip.allen@enron.com",
        "to": "counterparty-a@energy.com",
        "subject": "Gas Purchase Confirmation - Jan 2001",
        "body": "Dear Counterparty,\n\nThis confirms our agreement for the purchase of:\n- 50,000 MMBtu/day\n- Delivery: Henry Hub\n- Period: January 16-31, 2001\n- Price: $9.75/MMBtu\n\nPlease execute the ISDA confirmation by COB today.\n\nPhillip Allen\nEnron Gas Trading",
    },
    {
        "user": "allen-p", "folder": "inbox", "id": 5,
        "msg_id": "<E004@enron.com>",
        "date": "Tue, 16 Jan 2001 15:00:00 -0600",
        "from": "risk@enron.com",
        "to": "phillip.allen@enron.com",
        "subject": "Daily P&L Report",
        "body": "Phillip,\n\nDaily P&L - January 16, 2001:\n\nRealized: +$2.4M\nUnrealized: +$1.1M\nTotal: +$3.5M\n\nVaR: $8.2M (within $10M limit)\n\nRisk Management",
    },
    {
        "user": "allen-p", "folder": "inbox", "id": 6,
        "msg_id": "<E005@enron.com>",
        "date": "Wed, 17 Jan 2001 08:00:00 -0600",
        "from": "phillip.allen@enron.com",
        "to": "jeffrey.skilling@enron.com",
        "cc": "vince.kaminski@enron.com",
        "subject": "Storage Arbitrage Opportunity",
        "body": "Jeff,\n\nIdentified significant storage arbitrage opportunity:\n- Buy spot gas at $9.80\n- Inject into storage ($0.15 cost)\n- Sell April futures at $5.20\n\nThis is a $4.45 spread per MMBtu, historically high.\nRecommend taking maximum position within risk limits.\n\nPhillip",
    },
    {
        "user": "allen-p", "folder": "inbox", "id": 7,
        "msg_id": "<E006@enron.com>",
        "date": "Wed, 17 Jan 2001 14:00:00 -0600",
        "from": "trading-desk@enron.com",
        "to": "phillip.allen@enron.com",
        "subject": "Position Report - January 17",
        "body": "Phillip,\n\nCurrent Natural Gas Positions:\n- Spot: Long 500,000 MMBtu\n- Feb: Long 2.5M MMBtu\n- March: Long 1.8M MMBtu\n- Storage injections: 3.2M MMBtu committed\n\nTotal delta: equivalent to +8.0M MMBtu\n\nTrading Desk",
    },
    {
        "user": "allen-p", "folder": "inbox", "id": 8,
        "msg_id": "<E007@enron.com>",
        "date": "Thu, 18 Jan 2001 09:00:00 -0600",
        "from": "phillip.allen@enron.com",
        "to": "trading-desk@enron.com",
        "subject": "Re: Re: Natural Gas Trading Strategy - Q1 2001",
        "body": "Team,\n\nFollowing up on the Q1 strategy discussion. Given the current storage dynamics,\nI am increasing our long position target for February delivery by 20%.\n\nAll traders please review updated position limits sent separately.\n\nPhillip",
    },
    {
        "user": "allen-p", "folder": "inbox", "id": 9,
        "msg_id": "<E008@enron.com>",
        "date": "Fri, 19 Jan 2001 16:00:00 -0600",
        "from": "compliance@enron.com",
        "to": "phillip.allen@enron.com",
        "subject": "Position Limit Compliance Review",
        "body": "Phillip,\n\nQuarterly position limit review complete. Your desk is in full compliance.\nNo exceptions noted.\n\nNext review: April 2001.\n\nCompliance Department",
    },
    {
        "user": "allen-p", "folder": "inbox", "id": 10,
        "msg_id": "<E009@enron.com>",
        "date": "Mon, 22 Jan 2001 08:15:00 -0600",
        "from": "counterparty-b@utility.com",
        "to": "phillip.allen@enron.com",
        "bcc": "legal@enron.com",
        "subject": "Long-Term Supply Agreement Proposal",
        "body": "Dear Mr. Allen,\n\nWe are interested in a 5-year natural gas supply agreement:\n- Volume: 100,000 MMBtu/day\n- Indexing: Henry Hub + $0.05\n- Start: April 1, 2001\n\nPlease review and respond with Enron's interest.\n\nCounterparty Procurement",
    },
    {
        "user": "allen-p", "folder": "inbox", "id": 11,
        "msg_id": "<E010@enron.com>",
        "date": "Mon, 22 Jan 2001 14:00:00 -0600",
        "from": "phillip.allen@enron.com",
        "to": "trading-desk@enron.com",
        "subject": "Gas Market Morning Report",
        "body": "Team,\n\nMorning Report - Jan 22, 2001:\n\nHenry Hub spot: $10.35/MMBtu (up $0.53)\nStorage: 2,798 Bcf (19% below 5-yr average)\nCold weather extending through end of January\n\nOur long positions are performing well. Hold through Thursday.\n\nPhillip",
    },
]


def write_email(path: Path, email: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"Message-ID: {email['msg_id']}",
        f"Date: {email['date']}",
        f"From: {email['from']}",
        f"To: {email['to']}",
    ]
    if "cc" in email:
        lines.append(f"Cc: {email['cc']}")
    if "bcc" in email:
        lines.append(f"Bcc: {email['bcc']}")
    lines.append(f"Subject: {email['subject']}")
    if "x_folder" in email:
        lines.append(f"X-Folder: {email['x_folder']}")
    if "content_type" in email:
        lines.append(f"Content-Type: {email['content_type']}")
    else:
        lines.append("Content-Type: text/plain; charset=us-ascii")
    lines.append("X-Origin: Enron-Corp")
    lines.append("")
    lines.append(email["body"])

    path.write_text("\n".join(lines), encoding="utf-8")


def generate(output_dir: str) -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    user_names = {u["name"] for u in USERS}
    count = 0
    for email in EMAILS:
        assert email["user"] in user_names, f"Unknown user: {email['user']}"
        path = root / email["user"] / email["folder"] / str(email["id"])
        write_email(path, email)
        count += 1

    print(f"Generated {count} emails in {output_dir}")
    print("Users:", sorted(user_names))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic Enron test emails")
    parser.add_argument(
        "--output-dir",
        default="./data/test_maildir",
        help="Root directory for test mailboxes (default: ./data/test_maildir)",
    )
    args = parser.parse_args()
    generate(args.output_dir)
