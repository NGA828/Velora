#!/usr/bin/env python3
"""Generate the Velora Hospital Management System end-user guide PDF."""

from __future__ import annotations

import argparse
import html
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "user guide.pdf"

PRIMARY = colors.HexColor("#176B87")
PRIMARY_DARK = colors.HexColor("#0D4559")
PRIMARY_SOFT = colors.HexColor("#E5F2F5")
TEXT = colors.HexColor("#17212B")
MUTED = colors.HexColor("#5F6F7E")
BORDER = colors.HexColor("#D8E1E8")
BACKGROUND = colors.HexColor("#F5F7FA")
SUCCESS = colors.HexColor("#167A58")
SUCCESS_SOFT = colors.HexColor("#E9F6F0")
WARNING = colors.HexColor("#A76512")
WARNING_SOFT = colors.HexColor("#FFF4DE")
CRITICAL = colors.HexColor("#B93845")
CRITICAL_SOFT = colors.HexColor("#FFF0F2")
WHITE = colors.white
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT = RIGHT = 18 * mm
TOP = 21 * mm
BOTTOM = 18 * mm
CONTENT_WIDTH = PAGE_WIDTH - LEFT - RIGHT


def _register_fonts() -> tuple[str, str, str, str]:
    """Prefer DejaVu when available, otherwise use built-in PDF fonts."""
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"),
    ]
    if all(path.exists() for path in candidates):
        names = ("VeloraSans", "VeloraSans-Bold", "VeloraSans-Italic", "VeloraSans-BoldItalic")
        for name, path in zip(names, candidates):
            pdfmetrics.registerFont(TTFont(name, str(path)))
        pdfmetrics.registerFontFamily(
            "VeloraSans",
            normal=names[0],
            bold=names[1],
            italic=names[2],
            boldItalic=names[3],
        )
        return names
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique"


FONT, FONT_BOLD, FONT_ITALIC, FONT_BOLD_ITALIC = _register_fonts()


def build_styles():
    sample = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle(
            "CoverKicker",
            fontName=FONT_BOLD,
            fontSize=10,
            leading=14,
            textColor=PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=10,
            tracking=1.3,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            fontName=FONT_BOLD,
            fontSize=31,
            leading=37,
            textColor=PRIMARY_DARK,
            alignment=TA_CENTER,
            spaceAfter=15,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            fontName=FONT,
            fontSize=14,
            leading=21,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=25,
        ),
        "h1": ParagraphStyle(
            "Heading1",
            parent=sample["Heading1"],
            fontName=FONT_BOLD,
            fontSize=21,
            leading=27,
            textColor=PRIMARY_DARK,
            spaceBefore=7,
            spaceAfter=12,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=sample["Heading2"],
            fontName=FONT_BOLD,
            fontSize=14,
            leading=19,
            textColor=PRIMARY,
            spaceBefore=13,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "Heading3",
            parent=sample["Heading3"],
            fontName=FONT_BOLD,
            fontSize=11,
            leading=15,
            textColor=TEXT,
            spaceBefore=9,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=9.4,
            leading=14,
            textColor=TEXT,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=7.7,
            leading=11,
            textColor=MUTED,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=9.2,
            leading=13.5,
            textColor=TEXT,
            leftIndent=13,
            firstLineIndent=-8,
            bulletIndent=2,
            spaceAfter=3,
        ),
        "step": ParagraphStyle(
            "Step",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=9.2,
            leading=13.5,
            textColor=TEXT,
            leftIndent=21,
            firstLineIndent=-17,
            spaceAfter=4,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            fontName=FONT_BOLD,
            fontSize=7.7,
            leading=10,
            textColor=WHITE,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            fontName=FONT,
            fontSize=7.6,
            leading=10.5,
            textColor=TEXT,
        ),
        "table_cell_bold": ParagraphStyle(
            "TableCellBold",
            fontName=FONT_BOLD,
            fontSize=7.6,
            leading=10.5,
            textColor=TEXT,
        ),
        "toc_heading": ParagraphStyle(
            "TOCHeading",
            fontName=FONT_BOLD,
            fontSize=23,
            leading=28,
            textColor=PRIMARY_DARK,
            spaceAfter=15,
        ),
    }


STYLES = build_styles()


class GuideDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=LEFT,
            rightMargin=RIGHT,
            topMargin=TOP,
            bottomMargin=BOTTOM,
            title="Velora Hospital Management System User Guide",
            author="Velora Product and Engineering Team",
            subject="Role-based user guide for the Velora Hospital Management System",
            creator="Velora",
            **kwargs,
        )
        frame = Frame(LEFT, BOTTOM, CONTENT_WIDTH, PAGE_HEIGHT - TOP - BOTTOM, id="content")
        self.addPageTemplates(PageTemplate(id="guide", frames=frame, onPage=self._on_page))
        self._heading_counter = 0

    def beforeDocument(self):
        self._heading_counter = 0
        super().beforeDocument()

    def _on_page(self, canvas, doc):
        canvas.saveState()
        if doc.page == 1:
            canvas.setFillColor(BACKGROUND)
            canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
            canvas.setStrokeColor(PRIMARY_SOFT)
            canvas.setLineWidth(1)
            canvas.circle(PAGE_WIDTH - 33 * mm, PAGE_HEIGHT - 34 * mm, 30 * mm, fill=0, stroke=1)
            canvas.circle(30 * mm, 31 * mm, 23 * mm, fill=0, stroke=1)
            self._draw_logo(canvas, PAGE_WIDTH / 2, PAGE_HEIGHT - 58 * mm, 24 * mm)
        else:
            canvas.setStrokeColor(BORDER)
            canvas.setLineWidth(0.5)
            canvas.line(LEFT, PAGE_HEIGHT - 13 * mm, PAGE_WIDTH - RIGHT, PAGE_HEIGHT - 13 * mm)
            self._draw_logo(canvas, LEFT + 4 * mm, PAGE_HEIGHT - 8 * mm, 6 * mm)
            canvas.setFont(FONT_BOLD, 7.5)
            canvas.setFillColor(PRIMARY_DARK)
            canvas.drawString(LEFT + 9 * mm, PAGE_HEIGHT - 9.5 * mm, "VELORA USER GUIDE")
            canvas.setFont(FONT, 7.2)
            canvas.setFillColor(MUTED)
            canvas.drawRightString(PAGE_WIDTH - RIGHT, PAGE_HEIGHT - 9.5 * mm, "Hospital Management System")
            canvas.setStrokeColor(BORDER)
            canvas.line(LEFT, 12 * mm, PAGE_WIDTH - RIGHT, 12 * mm)
            canvas.setFont(FONT, 7.2)
            canvas.drawString(LEFT, 7.7 * mm, "Version 1.0  |  16 August 2026")
            canvas.drawRightString(PAGE_WIDTH - RIGHT, 7.7 * mm, f"Page {doc.page}")
        canvas.restoreState()

    @staticmethod
    def _draw_logo(canvas, x, y, size):
        canvas.setFillColor(PRIMARY)
        radius = size * 0.22
        canvas.roundRect(x - size / 2, y - size / 2, size, size, radius, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        thickness = size * 0.16
        arm = size * 0.56
        canvas.roundRect(x - thickness / 2, y - arm / 2, thickness, arm, thickness / 2, fill=1, stroke=0)
        canvas.roundRect(x - arm / 2, y - thickness / 2, arm, thickness, thickness / 2, fill=1, stroke=0)

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        style_name = flowable.style.name
        if style_name not in {"Heading1", "Heading2"}:
            return
        level = 0 if style_name == "Heading1" else 1
        text = flowable.getPlainText()
        self._heading_counter += 1
        key = f"heading-{self._heading_counter}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=False)
        self.notify("TOCEntry", (level, text, self.page, key))


def para(text: str, style="body"):
    return Paragraph(text, STYLES[style])


def h1(text: str):
    return Paragraph(text, STYLES["h1"])


def h2(text: str):
    return Paragraph(text, STYLES["h2"])


def h3(text: str):
    return Paragraph(text, STYLES["h3"])


def bullets(items):
    return [Paragraph(f"&bull; {item}", STYLES["bullet"]) for item in items]


def steps(items):
    return [Paragraph(f"<b>{index}.</b> {item}", STYLES["step"]) for index, item in enumerate(items, 1)]


def callout(title: str, body: str, tone="info"):
    palette = {
        "info": (PRIMARY, PRIMARY_SOFT),
        "success": (SUCCESS, SUCCESS_SOFT),
        "warning": (WARNING, WARNING_SOFT),
        "critical": (CRITICAL, CRITICAL_SOFT),
    }
    accent, fill = palette[tone]
    content = Paragraph(f"<font color='{accent.hexval()}'><b>{title}</b></font><br/>{body}", STYLES["body"])
    table = Table([["", content]], colWidths=[3 * mm, CONTENT_WIDTH - 3 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), accent),
                ("BACKGROUND", (1, 0), (1, 0), fill),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 0),
                ("TOPPADDING", (0, 0), (0, 0), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 10),
                ("RIGHTPADDING", (1, 0), (1, 0), 10),
                ("TOPPADDING", (1, 0), (1, 0), 8),
                ("BOTTOMPADDING", (1, 0), (1, 0), 8),
                ("BOX", (0, 0), (-1, -1), 0.5, accent),
            ]
        )
    )
    return KeepTogether([table, Spacer(1, 4 * mm)])


def data_table(headers, rows, widths=None):
    widths = widths or [CONTENT_WIDTH / len(headers)] * len(headers)
    data = [[Paragraph(html.escape(str(cell)), STYLES["table_header"]) for cell in headers]]
    for row in rows:
        data.append(
            [
                Paragraph(str(cell), STYLES["table_cell_bold" if col == 0 else "table_cell"])
                for col, cell in enumerate(row)
            ]
        )
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_DARK),
                ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BACKGROUND]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return [table, Spacer(1, 4 * mm)]


def section_break():
    return PageBreak()


def build_story():
    s = []

    # Cover
    s += [Spacer(1, 58 * mm)]
    s.append(para("SINGLE-HOSPITAL CLINICAL OPERATIONS", "cover_kicker"))
    s.append(para("Velora Hospital<br/>Management System", "cover_title"))
    s.append(para("Complete Role-Based User Guide", "cover_subtitle"))
    s.append(Spacer(1, 13 * mm))
    cover_info = Table(
        [
            [para("Document", "small"), para("User Guide", "small")],
            [para("Version", "small"), para("1.0", "small")],
            [para("Release date", "small"), para("16 August 2026", "small")],
            [para("Audience", "small"), para("Hospital staff and authorized Patient Guards", "small")],
        ],
        colWidths=[35 * mm, 92 * mm],
        hAlign="CENTER",
    )
    cover_info.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    s.append(cover_info)
    s.append(Spacer(1, 20 * mm))
    s.append(para("Modern. Secure. Connected care.", "cover_kicker"))
    s.append(PageBreak())

    # TOC
    s.append(Paragraph("Contents", STYLES["toc_heading"]))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOCLevel1",
            fontName=FONT_BOLD,
            fontSize=9.5,
            leading=15,
            leftIndent=0,
            firstLineIndent=0,
            textColor=PRIMARY_DARK,
            spaceBefore=4,
        ),
        ParagraphStyle(
            "TOCLevel2",
            fontName=FONT,
            fontSize=8.5,
            leading=13,
            leftIndent=12,
            firstLineIndent=0,
            textColor=MUTED,
        ),
    ]
    s.append(toc)
    s.append(PageBreak())

    # 1 Overview
    s.append(h1("1. About This Guide"))
    s.append(
        para(
            "This guide explains how to use Velora as a connected hospital workflow. It is organized first around common tasks, then around the six application roles: Head of Service, Doctor, Nurse, Patient Guard, Accounting, and Admin."
        )
    )
    s.append(
        callout(
            "Clinical safety",
            "Velora stores and applies hospital-configured rules. It does not replace clinical judgment, create diagnoses, or invent medical thresholds. If approved rule coverage is incomplete, vital signs are marked <b>Unassessed</b> rather than assumed Stable.",
            "warning",
        )
    )
    s.append(h2("1.1 Who should use this guide"))
    s += bullets(
        [
            "Hospital leadership configuring staff, services, resources, and referral hospitals.",
            "Doctors registering patients and managing medical decisions.",
            "Nurses monitoring assigned patients, Patient Guards, vital signs, and medication administration.",
            "Patient Guards using only information and decisions explicitly linked to their patient relationship.",
            "Accounting personnel managing invoices, payments, receipts, and financial reports.",
            "System administrators managing identity, technical health, and redacted audit information.",
        ]
    )
    s.append(h2("1.2 Core workflow"))
    s += steps(
        [
            "Head of Service prepares hospital reference data and staff accounts.",
            "Doctor registers the patient and assigns a Nurse.",
            "Nurse invites the authorized Patient Guard.",
            "Nurse records vital signs; configured rules produce Stable, Critical, or Unassessed.",
            "Doctor reviews the file and uses prescriptions, monitoring, transfer, or certificate workflows as needed.",
            "Patient Guard responds to questions and transfer decisions within explicit permissions.",
            "Accounting handles financial records without receiving clinical-record access.",
            "Messages, notifications, audit history, and optional Twilio calls connect the workflow.",
        ]
    )
    s.append(h2("1.3 Important terms"))
    s += data_table(
        ["Term", "Meaning"],
        [
            ("MRN", "Medical Record Number generated by Velora when a patient is registered."),
            ("Care episode", "The active inpatient, outpatient, or emergency period for a patient."),
            ("Care assignment", "The active Doctor or Nurse relationship that authorizes patient access."),
            ("Patient Guard", "An authorized family member or representative linked to one or more patients."),
            ("Released record", "Clinical information explicitly marked visible to an authorized Patient Guard."),
            ("Rule set", "A versioned group of hospital-approved vital-sign evaluation rules."),
            ("External hospital", "A possible transfer destination configured by the Head of Service."),
        ],
        [34 * mm, CONTENT_WIDTH - 34 * mm],
    )

    # 2 Quick start
    s.append(section_break())
    s.append(h1("2. Getting Started"))
    s.append(h2("2.1 Demo sign-in accounts"))
    s.append(
        callout(
            "Local demonstration only",
            "The accounts below use the requested shared demo password <b>password123</b>. They are generated only by the DEBUG-only demo seed command. Never use this password for production accounts.",
            "critical",
        )
    )
    s += data_table(
        ["Role", "Email", "Demo password"],
        [
            ("Admin", "admin@velora.com", "password123"),
            ("Head of Service", "head@velora.com", "password123"),
            ("Doctor", "doctor@velora.com", "password123"),
            ("Nurse", "nurse@velora.com", "password123"),
            ("Patient Guard", "guard@velora.com", "password123"),
            ("Accounting", "accounts@velora.com", "password123"),
        ],
        [42 * mm, 82 * mm, CONTENT_WIDTH - 124 * mm],
    )
    s.append(h2("2.2 Sign in"))
    s += steps(
        [
            "Open the Velora web address supplied by the hospital.",
            "Enter your hospital email address and password.",
            "Select <b>Sign in securely</b>.",
            "If a password change is required, enter the temporary/current password and choose a private replacement.",
            "Velora opens the dashboard for your assigned role.",
        ]
    )
    s.append(h2("2.3 Navigation"))
    s += bullets(
        [
            "The left sidebar shows modules available to your role only.",
            "On tablets and phones, use the menu button in the top bar to open or close navigation.",
            "The role label above navigation confirms the workspace you are using.",
            "Your name and email appear at the bottom of the sidebar with the sign-out control.",
            "Use the visible Back link on detail pages instead of the browser back button when possible.",
        ]
    )
    s.append(h2("2.4 Notifications"))
    s += steps(
        [
            "Open <b>Notifications</b> from the sidebar.",
            "Unread notifications are visually emphasized and contain an Open action when a destination is available.",
            "Select <b>Mark read</b> on one item or <b>Mark all read</b>.",
            "Reading an alert does not resolve the underlying clinical or financial condition.",
        ]
    )
    s.append(h2("2.5 Profile, password, and sign out"))
    s += bullets(
        [
            "Open <b>Profile & security</b> to confirm your name, email, telephone, and role.",
            "Select <b>Change password</b> whenever a password may have been exposed or reused.",
            "Use the sign-out icon next to your email. Closing the browser alone is not the recommended sign-out method.",
        ]
    )

    # 3 Shared communication
    s.append(section_break())
    s.append(h1("3. Communication"))
    s.append(h2("3.1 Start a conversation"))
    s += steps(
        [
            "Open <b>Messages</b> and select <b>New conversation</b>.",
            "Choose a contact. Only users allowed by current staff and patient relationships are listed.",
            "Optionally select a patient context. Both participants must have current access to that patient.",
            "Select <b>Start conversation</b>.",
        ]
    )
    s.append(h2("3.2 Send messages and attachments"))
    s += steps(
        [
            "Select a conversation from the left panel.",
            "Enter a message in the composer.",
            "To attach a file, select the paperclip and choose PDF, JPEG, PNG, or UTF-8 text up to 10 MB.",
            "Select <b>Send</b>. The message is written to the database before the interface confirms it.",
        ]
    )
    s += data_table(
        ["Receipt", "Meaning"],
        [
            ("Sent", "The message is stored by Velora and recipient receipt rows exist."),
            ("Delivered", "The recipient application acknowledged delivery."),
            ("Seen", "The recipient opened the conversation and acknowledged the message."),
        ],
        [30 * mm, CONTENT_WIDTH - 30 * mm],
    )
    s.append(
        callout(
            "Attachment safety",
            "Velora verifies extension, MIME type, size, and basic file signature. Downloads require active conversation membership. This is not a substitute for the hospital's production malware scanning and quarantine policy.",
            "info",
        )
    )
    s.append(h2("3.3 Voice calls"))
    s += steps(
        [
            "Open <b>Calls</b>.",
            "If Twilio is not configured, Velora clearly displays that calling is unavailable and does not simulate a call.",
            "When configured, select an authorized contact and choose <b>Start call</b>.",
            "Accept or decline incoming calls from the call panel.",
            "Use <b>End call</b> when finished. Velora stores call participants, provider state, and timing, but not audio.",
        ]
    )

    # 4 HOS
    s.append(section_break())
    s.append(h1("4. Head of Service Guide"))
    s.append(para("The Head of Service prepares the operational and clinical reference data on which every later workflow depends."))
    s.append(h2("4.1 Dashboard"))
    s += bullets(
        [
            "Review active clinical staff, departments, available beds, and external hospitals.",
            "Use the attention list for incomplete hospital profile, pending invitations, unavailable resources, or incomplete transfer destinations.",
            "Follow setup shortcuts instead of attempting to configure everything from the dashboard.",
        ]
    )
    s.append(h2("4.2 Invite and manage personnel"))
    s += steps(
        [
            "Open <b>Medical personnel</b> and select <b>Invite staff</b>.",
            "Enter the work email, Doctor or Nurse role, unique employee number, department, job title, license number, and hire date.",
            "Send the secure invitation. The recipient sets their own password.",
            "Track Pending, Accepted, Revoked, or Expired invitation state.",
            "Use Manage to update department, title, license, employment status, or sign-in access without deleting history.",
        ]
    )
    s.append(h2("4.3 Hospital profile and departments"))
    s += steps(
        [
            "Open <b>Hospital information</b>.",
            "Enter display/legal name, registration number, timezone, three-letter ISO billing currency, location, email, telephone, and website.",
            "Save the profile. New invoices preserve the configured currency as a historical snapshot.",
            "Add departments with code, name, location, telephone, description, active state, and optional parent department.",
        ]
    )
    s.append(h2("4.4 Specialties, conditions, and matching rules"))
    s += steps(
        [
            "Open <b>Specialties</b> and define active specialist capabilities.",
            "Add hospital-approved clinical condition labels and code systems.",
            "Open Matching rules and map each condition to an appropriate specialty with a visible relative weight.",
            "Keep mappings explainable; they are used by transfer recommendations and are not diagnoses.",
        ]
    )
    s.append(h2("4.5 Resources, rooms, beds, and services"))
    s += bullets(
        [
            "Resources: asset code, equipment/supply category, department, total/available quantity, status, and notes.",
            "Rooms: room code, department, floor, room type, and operational status.",
            "Beds: bed code, room, current status, and notes.",
            "Services: catalogue code/name/category and departmental Available, Limited, or Unavailable coverage.",
        ]
    )
    s.append(h2("4.6 Medication catalogue"))
    s += steps(
        [
            "Open <b>Medications</b> and select Add medication.",
            "Enter generic name, optional brand, strength, form, description, and active state.",
            "Do not place patient dosage or schedule in the catalogue; those belong to each Doctor prescription.",
            "Deactivate obsolete items instead of deleting historical references.",
        ]
    )
    s.append(h2("4.7 External hospitals"))
    s += steps(
        [
            "Open <b>External hospitals</b> and add verified location, telephone, general email, and medical transfer email.",
            "Select the hospital and add specialty/service capabilities and named specialists.",
            "Set capability availability accurately.",
            "A destination is Transfer ready only when a transfer email and at least one capability are stored.",
        ]
    )
    s.append(h2("4.8 Vital analysis rules"))
    s += steps(
        [
            "Open <b>Clinical rules</b> and add metric definitions with code, name, unit, and precision. Metric definitions contain no thresholds.",
            "Create a versioned draft rule set.",
            "Add each hospital-approved critical rule: metric, operator, values, priority, and clinician-facing explanation.",
            "Review and activate the draft. Activating a new set retires the prior active set.",
            "Do not enter values without clinical governance approval.",
        ]
    )
    s.append(h2("4.9 Operational reports"))
    s += bullets(
        [
            "Review aggregate staff, patient, bed, resource, and external-hospital statistics.",
            "The operational report does not open patient diagnoses or clinical notes.",
        ]
    )

    # 5 Doctor
    s.append(section_break())
    s.append(h1("5. Doctor Guide"))
    s.append(h2("5.1 Register a patient"))
    s += steps(
        [
            "Open <b>Patients</b> and select <b>Register patient</b>.",
            "Enter identity, date of birth, sex at birth, optional blood type, contact details, address, and emergency contact.",
            "Select department, episode type, admission reason, and an active primary Nurse.",
            "Submit once. Velora creates the patient, MRN, medical file, active care episode, Doctor assignment, Nurse assignment, audit event, and Nurse notification atomically.",
            "If a duplicate current identity is detected, review the existing record rather than creating another patient.",
        ]
    )
    s.append(h2("5.2 Patient overview and Nurse reassignment"))
    s += bullets(
        [
            "The overview shows patient identity, current care state, latest vital result, episode, care team, contact information, and Guard count.",
            "Use Reassign Nurse only when responsibility changes. The previous Nurse loses patient access immediately while assignment history remains.",
        ]
    )
    s.append(h2("5.3 Medical file"))
    s += data_table(
        ["Section", "Doctor action"],
        [
            ("Allergies", "Record substance, reaction, severity, status, and Guard visibility."),
            ("History", "Add categorized medical, surgical, family, social, or other history."),
            ("Diagnoses", "Select a configured condition, status, description, and release visibility."),
            ("Treatment plans", "Record title, objectives, instructions, dates, status, and release visibility."),
            ("Clinical notes", "Create progress/consultation/discharge/other notes, then sign when final."),
        ],
        [35 * mm, CONTENT_WIDTH - 35 * mm],
    )
    s.append(
        callout(
            "Signed notes",
            "A signed note cannot be silently edited. Create an amendment when correction is required. Patient Guards see only released signed notes and other released records.",
            "warning",
        )
    )
    s.append(h2("5.4 Review vital signs"))
    s += bullets(
        [
            "Open Vital history from the patient record.",
            "Review actual measurements, units, Nurse, observation time, status, and rule-set version.",
            "For Critical observations, read each matched rule explanation before taking action.",
            "Unassessed means approved rule coverage was missing or incomplete; it does not mean Stable.",
        ]
    )
    s.append(h2("5.5 Prescriptions"))
    s += steps(
        [
            "Open Prescriptions and select New prescription.",
            "Select an assigned patient and treatment dates.",
            "Add one or more medication items with amount, unit, route, frequency text, duration, instructions, scheduled times, and optional weekdays.",
            "Save the complete draft, review it, then select Activate schedule.",
            "Activation creates concrete medication doses and makes the prescription visible to the Patient Guard and Nurse.",
            "Review administered, missed, and refused counts. Resolve pending doses before completing the prescription.",
            "Cancellation requires a reason and cancels unresolved doses without deleting past administration.",
        ]
    )
    s.append(h2("5.6 Monitoring questions"))
    s += steps(
        [
            "Open <b>Patient monitoring</b> and create a thread for an assigned patient and authorized Patient Guard.",
            "Add Yes/No, text, number, or single-choice questions and optional due time.",
            "Review the current answer and any preserved correction history.",
            "Close the thread when monitoring is complete.",
        ]
    )
    s.append(h2("5.7 Transfer requests"))
    s += steps(
        [
            "Create a transfer request with patient, decision Guard, urgency, reason, clinical summary, and weighted requirements.",
            "Generate recommendations. Review eligibility, score, matched requirements, missing requirements, and explanation.",
            "Submit an eligible current recommendation to the Patient Guard.",
            "After approval, select Send medical package. Velora creates an allowlisted package, checksum, transmission record, and SMTP message.",
            "A failed provider delivery remains Failed; do not manually label it sent.",
        ]
    )
    s.append(h2("5.8 Death certificates"))
    s += steps(
        [
            "Open Death certificates and create a draft only when clinically and legally appropriate.",
            "Enter date/time, place, primary cause, contributing causes, manner, and notes according to hospital policy.",
            "Review before Issue. Issuing marks the patient Deceased and notifies authorized Patient Guards.",
            "Void only with a documented reason; never rewrite an issued certificate.",
        ]
    )

    # 6 Nurse
    s.append(section_break())
    s.append(h1("6. Nurse Guide"))
    s.append(h2("6.1 Dashboard and assigned patients"))
    s += bullets(
        [
            "The dashboard prioritizes assigned patients, medication due, Critical latest vitals, and missing Patient Guard access.",
            "My Patients contains only current Nurse assignments.",
            "Opening an unassigned patient identifier returns no protected record.",
        ]
    )
    s.append(h2("6.2 Invite a Patient Guard"))
    s += steps(
        [
            "Open an assigned patient and select Invite Patient Guard.",
            "Enter the Guard email and relationship.",
            "Choose explicit permissions for released medical file, monitoring, transfers, and optional billing.",
            "Send the invitation. The Guard chooses a password and receives access only to this patient.",
            "Revoke access when authorization ends. The account and history are preserved.",
        ]
    )
    s.append(h2("6.3 Record vital signs"))
    s += steps(
        [
            "Open Vital signs, choose the assigned patient, and select Record vitals.",
            "Confirm observation time and enter only measurements actually taken, using the displayed units.",
            "Add an optional Nurse note and select Save and analyze.",
            "Review Stable, Critical, or Unassessed and the explanation. A Critical result notifies the assigned Doctor.",
            "Never interpret Unassessed as a normal clinical result.",
        ]
    )
    s.append(h2("6.4 Nursing clinical documentation"))
    s += bullets(
        [
            "Review care-relevant medical file information for assigned patients.",
            "Record allergies/history where authorized and create Nursing notes only.",
            "Sign a Nursing note when final; signed notes are immutable.",
            "Nurses cannot create diagnoses, Doctor treatment plans, transfers, prescriptions, or death certificates.",
        ]
    )
    s.append(h2("6.5 Medication administration"))
    s += steps(
        [
            "Open Medication. The Due queue shows pending doses within the next 24 hours and marks overdue items.",
            "Verify patient, medication, amount, unit, route, instructions, and scheduled time.",
            "Select Administer, Refused, or Mark missed.",
            "Enter mandatory notes for Missed or Refused and optional administration notes.",
            "Confirm once. Velora records actual action time, Nurse, status, notes, and an append-only event.",
            "A second outcome for the same resolved dose is rejected.",
        ]
    )

    # 7 Guard
    s.append(section_break())
    s.append(h1("7. Patient Guard Guide"))
    s.append(
        callout(
            "Your access boundary",
            "Being a Patient Guard does not provide access to every patient. Each patient must have an active Guard relationship, and individual permissions may restrict medical file, monitoring, transfer, or billing features.",
            "info",
        )
    )
    s.append(h2("7.1 Patient information and medical file"))
    s += bullets(
        [
            "The dashboard and Patient information list only linked patients.",
            "Medical files show released allergies, history, diagnoses, treatment plans, and signed notes only.",
            "Internal notes and unreleased records remain hidden.",
            "Patient information and certificates are read-only for Patient Guards.",
        ]
    )
    s.append(h2("7.2 Prescriptions"))
    s += bullets(
        [
            "Prescriptions become visible only after the Doctor activates them.",
            "Review medication, dose, route, frequency, dates, times, instructions, Doctor, and administration summary.",
            "Do not alter the prescription or confirm medication administration; contact the care team through Messages if clarification is needed.",
        ]
    )
    s.append(h2("7.3 Answer monitoring questions"))
    s += steps(
        [
            "Open Monitoring and locate a question marked Response requested.",
            "Select Answer question and provide the required Yes/No, text, number, or choice response.",
            "Submit. The Doctor receives a notification.",
            "Use Correct response if needed. Velora keeps the previous response in history.",
        ]
    )
    s.append(h2("7.4 Decide a transfer"))
    s += steps(
        [
            "Open Transfer requests and review patient, Doctor, urgency, proposed hospital, reason, clinical summary, and required capabilities.",
            "Select Approve transfer or Reject.",
            "A rejection requires a reason. Submit the decision once.",
            "The Doctor receives the decision. Medical package sending remains impossible without approval.",
        ]
    )
    s.append(h2("7.5 Death certificate"))
    s += steps(
        [
            "Open Death certificate. Only issued certificates are listed.",
            "Review patient, certificate number, dates, place, causes, and issuing Doctor.",
            "Select Print certificate. Velora logs print access and opens the print layout.",
            "Patient Guards cannot create, edit, issue, or void a certificate.",
        ]
    )
    s.append(h2("7.6 Billing"))
    s += bullets(
        [
            "Billing appears only when the patient relationship grants billing permission.",
            "Review invoice number, charge lines, ISO currency, amount paid, outstanding amount, and status.",
            "Billing is read-only. Contact Accounting for payment and correction workflows.",
        ]
    )

    # 8 Accounting
    s.append(section_break())
    s.append(h1("8. Accounting Guide"))
    s.append(h2("8.1 Financial privacy"))
    s.append(
        para(
            "Accounting patient lookup provides MRN, name, date of birth, and care status for financial identification. It does not provide diagnoses, vital signs, prescriptions, monitoring responses, or transfer clinical summaries."
        )
    )
    s.append(h2("8.2 Charge catalogue"))
    s += steps(
        [
            "Open Billing, choose Charge catalogue, and select New charge item.",
            "Enter code, name, category, default unit price, description, and active state.",
            "Use Room for room charges, or Service, Medication, Procedure, or Other as applicable.",
            "Deactivate items that should not be used on future invoices.",
        ]
    )
    s.append(h2("8.3 Create and issue an invoice"))
    s += steps(
        [
            "Select New invoice and choose the patient from billing-only lookup.",
            "Add one or more charges with catalogue item or manual description, quantity, unit price, and service date.",
            "Review subtotal, total, paid, and outstanding values.",
            "Select Issue invoice, set the due date/time, and confirm.",
            "The invoice preserves the hospital ISO currency configured at creation time.",
        ]
    )
    s.append(h2("8.4 Payments and reversals"))
    s += steps(
        [
            "Open Payments and select Record payment.",
            "Choose an outstanding invoice. The form displays its remaining balance.",
            "Enter amount, method, and provider/reference value; post the payment.",
            "Velora prevents nonpositive and overpayment amounts and updates invoice status.",
            "For an error, use Reverse and enter a reason. Never delete or overwrite the original receipt.",
        ]
    )
    s.append(h2("8.5 Reports"))
    s += bullets(
        [
            "Review billed, collected, outstanding, invoice-status, and payment-method aggregates.",
            "Select Export CSV for reconciliation. Currency is included.",
            "Financial reports contain no clinical record content.",
        ]
    )

    # 9 Admin
    s.append(section_break())
    s.append(h1("9. Admin Guide"))
    s.append(h2("9.1 System dashboard"))
    s += bullets(
        [
            "Database: confirms SQLite connectivity.",
            "Medication worker: Online when its heartbeat is recent; Stale when action is required.",
            "Integrations: shows SMTP and Twilio configuration presence, not credentials.",
            "Failures: shows transfer email and Twilio webhook processing failures.",
            "Security: shows failed logins and audit event volume.",
        ]
    )
    s.append(h2("9.2 Manage system users"))
    s += steps(
        [
            "Open Users and locate the account.",
            "Select Manage.",
            "Turn Account is active off to suspend sign-in without deleting historical records.",
            "Enable Require password change when credentials may be compromised or temporary.",
            "Save access. Velora prevents an Admin from deactivating their own current account.",
        ]
    )
    s.append(h2("9.3 Redacted audit log"))
    s += bullets(
        [
            "Filter by action to review actor, object type, object identifier, time, IP, and request ID.",
            "Clinical record bodies and before/after snapshots are deliberately excluded from the Admin API.",
            "Use request IDs when correlating application logs during incident review.",
            "Admin does not gain patient-record access from audit permissions.",
        ]
    )

    # 10 Status reference
    s.append(section_break())
    s.append(h1("10. Status Reference"))
    s.append(h2("10.1 Patient and vital status"))
    s += data_table(
        ["Status", "Meaning / next action"],
        [
            ("Registered", "Patient identity exists; review the active episode and assignments."),
            ("Admitted", "Patient has active inpatient/emergency care."),
            ("Discharged", "Episode ended; follow hospital discharge policy."),
            ("Transferred", "Patient transfer was completed."),
            ("Deceased", "Doctor issued the death certificate workflow."),
            ("Stable", "No configured critical rule matched all assessed submitted metrics."),
            ("Critical", "At least one active configured critical rule matched; Doctor review required."),
            ("Unassessed", "No complete approved rule coverage; never interpret as Stable."),
        ],
        [31 * mm, CONTENT_WIDTH - 31 * mm],
    )
    s.append(h2("10.2 Prescription and medication status"))
    s += data_table(
        ["Status", "Meaning"],
        [
            ("Draft prescription", "Doctor can review before any doses are generated or shown to Guard."),
            ("Active prescription", "Schedule generated; Nurse/Guard workflows are available."),
            ("Completed prescription", "All pending doses resolved and Doctor completed the order."),
            ("Cancelled prescription", "Future pending doses cancelled with reason; history preserved."),
            ("Pending dose", "Scheduled outcome not yet recorded."),
            ("Administered", "Nurse confirmed administration and actual action time."),
            ("Missed", "Nurse documented missed dose with notes; Doctor notified."),
            ("Refused", "Patient refused and Nurse documented reason; Doctor notified."),
        ],
        [37 * mm, CONTENT_WIDTH - 37 * mm],
    )
    s.append(h2("10.3 Transfer, invoice, message, and call status"))
    s += data_table(
        ["Area", "Status", "Meaning"],
        [
            ("Transfer", "Recommended", "Deterministic options generated from current directory data."),
            ("Transfer", "Pending Guard", "Selected destination awaits the designated Guard decision."),
            ("Transfer", "Approved/Rejected", "Guard decision stored; approval enables package sending."),
            ("Transfer", "File sent", "SMTP delivery succeeded and checksum/audit were recorded."),
            ("Invoice", "Draft/Issued", "Editable before issue; payable after issue."),
            ("Invoice", "Partially paid/Paid", "Some or all issued balance was collected."),
            ("Payment", "Posted/Reversed", "Active receipt or explicit correction with reason."),
            ("Message", "Sent/Delivered/Seen", "Stored, recipient acknowledged, recipient opened."),
            ("Call", "Queued/Ringing/In progress", "Current provider call progression."),
            ("Call", "Completed/Declined/No answer/Failed", "Persisted terminal provider outcome."),
        ],
        [25 * mm, 35 * mm, CONTENT_WIDTH - 60 * mm],
    )

    # 11 Errors
    s.append(section_break())
    s.append(h1("11. Errors and Troubleshooting"))
    s += data_table(
        ["What you see", "What it means", "What to do"],
        [
            ("Authentication required", "No valid session.", "Return to Sign in; do not repeatedly submit the same action."),
            ("Permission denied", "Your role cannot perform the operation.", "Use the correct role/workflow; contact the hospital owner if assignment is wrong."),
            ("Not found", "Record does not exist or is outside your authorized scope.", "Confirm patient/care assignment; do not try random identifiers."),
            ("Validation error", "A required value or workflow rule is invalid.", "Read field errors, correct input, and submit once."),
            ("Conflict/already resolved", "Another valid action already changed the record.", "Refresh and review current state before deciding."),
            ("Network unavailable", "Browser cannot reach Velora.", "Preserve entered information, check connection, and retry only after service returns."),
            ("Integration unavailable", "SMTP or Twilio is not configured/healthy.", "Use hospital escalation; never simulate or manually mark provider success."),
            ("Unassessed vitals", "Approved rule coverage was incomplete.", "Use clinical judgment and request governance configuration; do not assume Stable."),
        ],
        [33 * mm, 50 * mm, CONTENT_WIDTH - 83 * mm],
    )
    s.append(h2("11.1 Safe retry rules"))
    s += bullets(
        [
            "Refresh before retrying a status-changing action after timeout.",
            "Messages use client identifiers to prevent duplicate sends, but users should still avoid rapid repeated clicks.",
            "Medication outcomes, transfer decisions, certificate issue, and payment posting must be verified before retry.",
            "Failed SMTP transmission keeps a Failed record and can be retried after configuration is corrected.",
        ]
    )

    # 12 privacy
    s.append(section_break())
    s.append(h1("12. Privacy and Security Responsibilities"))
    s += bullets(
        [
            "Use only your own named account. Do not share credentials or sessions.",
            "Verify the patient identity strip before entering clinical or financial data.",
            "Use only the minimum patient information needed in messages and attachments.",
            "Mark Guard visibility deliberately; Internal and Guard-released information have different audiences.",
            "Sign out when leaving a shared workstation and follow hospital screen-lock policy.",
            "Report suspected unauthorized access immediately; do not delete evidence.",
            "Do not store SMTP, Twilio, backup, or database credentials in chat messages or uploaded documents.",
            "Do not download protected attachments to unmanaged devices.",
        ]
    )
    s.append(h2("12.1 Audit behavior"))
    s.append(
        para(
            "Velora records security and workflow events including identity changes, patient registration, clinical mutations, medical file access, attachment downloads, vital analysis, prescription transitions, medication outcomes, transfer transmission, certificate view/print, payments, and Admin actions. Audit history is not a substitute for hospital policy review, but it supports accountability and investigation."
        )
    )

    # 13 FAQ
    s.append(section_break())
    s.append(h1("13. Frequently Asked Questions"))
    faq = [
        ("Why can I not see a patient?", "Your active care or Patient Guard relationship may not exist, may have ended, or may lack the feature permission."),
        ("Why is a vital result Unassessed?", "No active approved rule set fully covered every submitted metric. This is intentional safety behavior."),
        ("Why can the Guard not see my note?", "The note may be Internal, still Draft, or Guard medical-file permission may be off."),
        ("Why is a medication not in the Nurse queue?", "The prescription may still be Draft, the dose may be beyond the 24-hour queue, or the patient may be assigned to another Nurse."),
        ("Why can I not send the transfer package?", "The latest eligible recommendation must be selected and the designated Guard must approve first."),
        ("Why is calling disabled?", "All Twilio credentials, TwiML application, and signed public webhook URL must be configured."),
        ("Can Admin read patient records?", "No. Admin manages identity, health, and redacted audit metadata without default clinical access."),
        ("Can a payment or signed note be deleted?", "No. Corrections use reversal, void, cancellation, supersession, or amendment workflows."),
        ("What currency is used?", "Head of Service configures a three-letter ISO 4217 code. Each invoice stores its own currency snapshot."),
    ]
    for question, answer in faq:
        s.append(h3(question))
        s.append(para(answer))

    # 14 support
    s.append(section_break())
    s.append(h1("14. Support and Escalation"))
    s.append(h2("14.1 Include this information"))
    s += bullets(
        [
            "Your role and hospital email (never your password).",
            "Approximate time and hospital timezone.",
            "Page/module and action attempted.",
            "Patient MRN only when hospital policy permits the support channel.",
            "Visible error message and request reference ID.",
            "Whether the action may already have succeeded.",
        ]
    )
    s.append(h2("14.2 Escalation categories"))
    s += data_table(
        ["Issue", "Escalate to"],
        [
            ("Clinical rule or medication policy", "Clinical governance / Head of Service"),
            ("Incorrect patient assignment or Guard authorization", "Head of Service and responsible clinician"),
            ("Invoice/payment correction", "Accounting supervisor"),
            ("Login, system health, audit, backup", "System administrator / operations"),
            ("SMTP transfer failure", "Operations plus responsible Doctor"),
            ("Twilio calling failure", "Operations / communications provider owner"),
            ("Suspected privacy incident", "Hospital security and legal incident process immediately"),
        ],
        [58 * mm, CONTENT_WIDTH - 58 * mm],
    )
    s.append(
        callout(
            "Final reminder",
            "Velora is a connected workflow system. Complete actions through the correct role and status transitions; never work around permissions, provider failures, or clinical governance controls.",
            "success",
        )
    )

    return s


def generate(output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    document = GuideDocTemplate(str(output))
    document.multiBuild(build_story())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    generate(args.output.resolve())
    print(f"Generated {args.output.resolve()}")


if __name__ == "__main__":
    main()
