"""
pdf_generator.py — Generate professional PDF analysis reports using reportlab.

Produces a clean engineering-style report containing:
- Analysis summary (risk score, label, confidence)
- Extracted features table
- DFM violations with severity
- Top contributing factors (SHAP-based)
- Cost impact estimation
- AI recommendations
"""

import os
import io
import tempfile
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
    PageBreak,
)
from reportlab.lib.colors import HexColor


# ---------------------------------------------------------------------------
# COLOUR PALETTE
# ---------------------------------------------------------------------------
_BRAND_PRIMARY = HexColor("#3B82F6")      # Blue-500
_BRAND_DARK    = HexColor("#1E3A5F")      # Dark navy
_HEADER_BG     = HexColor("#0F172A")      # Slate-900
_SECTION_BG    = HexColor("#F1F5F9")      # Slate-100
_ACCENT_GREEN  = HexColor("#22C55E")      # Green-500
_ACCENT_AMBER  = HexColor("#F59E0B")      # Amber-500
_ACCENT_RED    = HexColor("#EF4444")      # Red-500
_TEXT_DARK     = HexColor("#1E293B")       # Slate-800
_TEXT_MID      = HexColor("#475569")       # Slate-600
_TEXT_LIGHT    = HexColor("#94A3B8")       # Slate-400
_BORDER_COLOR  = HexColor("#CBD5E1")      # Slate-300
_TABLE_HEADER  = HexColor("#1E40AF")      # Blue-800
_TABLE_ALT_ROW = HexColor("#EFF6FF")      # Blue-50
_WHITE         = colors.white


# ---------------------------------------------------------------------------
# CUSTOM STYLES
# ---------------------------------------------------------------------------
def _build_styles():
    """Create a custom style set for the report."""
    base = getSampleStyleSheet()

    styles = {}

    styles["Title"] = ParagraphStyle(
        "ReportTitle",
        parent=base["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        textColor=_BRAND_DARK,
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )

    styles["Subtitle"] = ParagraphStyle(
        "ReportSubtitle",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=_TEXT_MID,
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
    )

    styles["SectionHeading"] = ParagraphStyle(
        "SectionHeading",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=18,
        textColor=_BRAND_PRIMARY,
        spaceBefore=8 * mm,
        spaceAfter=4 * mm,
        borderPadding=(0, 0, 2, 0),
    )

    styles["Body"] = ParagraphStyle(
        "BodyText",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=_TEXT_DARK,
        alignment=TA_JUSTIFY,
        spaceAfter=3 * mm,
    )

    styles["Bullet"] = ParagraphStyle(
        "BulletItem",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=_TEXT_DARK,
        leftIndent=12,
        spaceAfter=2 * mm,
        bulletFontName="Helvetica",
        bulletFontSize=9,
        bulletIndent=0,
    )

    styles["SmallGrey"] = ParagraphStyle(
        "SmallGrey",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=_TEXT_LIGHT,
        alignment=TA_CENTER,
    )

    styles["MetricLabel"] = ParagraphStyle(
        "MetricLabel",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=_TEXT_MID,
    )

    styles["MetricValue"] = ParagraphStyle(
        "MetricValue",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=_TEXT_DARK,
    )

    return styles


# ---------------------------------------------------------------------------
# SEVERITY COLOUR HELPER
# ---------------------------------------------------------------------------
def _severity_color(severity_type: str) -> HexColor:
    """Return a colour for a violation severity type."""
    mapping = {
        "CRITICAL": _ACCENT_RED,
        "WARNING": _ACCENT_AMBER,
        "INFO": _BRAND_PRIMARY,
    }
    return mapping.get(severity_type, _TEXT_MID)


def _risk_color(label: str) -> HexColor:
    """Return a colour matching the risk label."""
    mapping = {
        "LOW": _ACCENT_GREEN,
        "MEDIUM": _ACCENT_AMBER,
        "HIGH": _ACCENT_RED,
    }
    return mapping.get(label, _TEXT_MID)


# ---------------------------------------------------------------------------
# FEATURE LABEL MAPPING
# ---------------------------------------------------------------------------
_FEATURE_LABELS = {
    "wall_thickness": ("Wall Thickness", "mm"),
    "draft_angle": ("Draft Angle", "°"),
    "corner_radius": ("Corner Radius", "mm"),
    "aspect_ratio": ("Aspect Ratio", ""),
    "wall_uniformity": ("Wall Uniformity", ""),
    "undercut_present": ("Undercut", ""),
}


# ---------------------------------------------------------------------------
# PAGE TEMPLATE CALLBACKS
# ---------------------------------------------------------------------------
def _header_footer(canvas, doc):
    """Draw a sleek header bar and footer on every page."""
    width, height = A4

    # --- Header stripe ---
    canvas.saveState()
    canvas.setFillColor(_HEADER_BG)
    canvas.rect(0, height - 18 * mm, width, 18 * mm, fill=True, stroke=False)

    # Brand accent line
    canvas.setFillColor(_BRAND_PRIMARY)
    canvas.rect(0, height - 18.8 * mm, width, 0.8 * mm, fill=True, stroke=False)

    # Header text
    canvas.setFillColor(_WHITE)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(15 * mm, height - 12 * mm, "Varroc DesignCopilot AI")

    canvas.setFillColor(HexColor("#94A3B8"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 15 * mm, height - 12 * mm, "Analysis Report")

    # --- Footer ---
    canvas.setFillColor(_BORDER_COLOR)
    canvas.rect(15 * mm, 12 * mm, width - 30 * mm, 0.3 * mm, fill=True, stroke=False)

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_TEXT_LIGHT)
    canvas.drawString(15 * mm, 8 * mm, f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}")
    canvas.drawRightString(width - 15 * mm, 8 * mm, f"Page {doc.page}")

    canvas.restoreState()


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------
def generate_analysis_pdf(analysis_data: dict) -> str:
    """
    Generate a professional PDF report from analysis data.

    Args:
        analysis_data: Dictionary with keys like risk_score, risk_label,
                       features, violations, shap_values, recommendations,
                       top_issues, confidence, cost_impact, processing_time, etc.

    Returns:
        Absolute path to the generated temporary PDF file.
    """
    # Create a temp file that persists until explicitly deleted
    tmp = tempfile.NamedTemporaryFile(
        suffix=".pdf",
        prefix="cadguard_report_",
        delete=False,
        dir=tempfile.gettempdir(),
    )
    tmp_path = tmp.name
    tmp.close()

    doc = SimpleDocTemplate(
        tmp_path,
        pagesize=A4,
        topMargin=25 * mm,
        bottomMargin=20 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )

    styles = _build_styles()
    elements = []

    # ---------------------------------------------------------------
    # TITLE BLOCK
    # ---------------------------------------------------------------
    elements.append(Spacer(1, 6 * mm))
    elements.append(
        Paragraph("Varroc DesignCopilot AI", styles["Title"])
    )
    elements.append(
        Paragraph("DFM Analysis Report", styles["Subtitle"])
    )

    # File info line
    file_name = analysis_data.get("file_name", "Unknown")
    material = analysis_data.get("material", "N/A")
    created_at = analysis_data.get("created_at", "")
    date_str = ""
    if created_at:
        try:
            dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            date_str = dt.strftime("%B %d, %Y %H:%M")
        except Exception:
            date_str = str(created_at)
    else:
        date_str = datetime.now().strftime("%B %d, %Y %H:%M")

    elements.append(
        Paragraph(
            f'<b>File:</b> {file_name} &nbsp;&nbsp;|&nbsp;&nbsp; '
            f'<b>Material:</b> {material} &nbsp;&nbsp;|&nbsp;&nbsp; '
            f'<b>Date:</b> {date_str}',
            styles["Body"],
        )
    )
    elements.append(
        HRFlowable(
            width="100%", thickness=0.5, color=_BORDER_COLOR,
            spaceBefore=3 * mm, spaceAfter=2 * mm,
        )
    )

    # ---------------------------------------------------------------
    # SECTION 1: SUMMARY
    # ---------------------------------------------------------------
    elements.append(Paragraph("1. Analysis Summary", styles["SectionHeading"]))

    risk_score = analysis_data.get("risk_score", 0)
    risk_label = analysis_data.get("risk_label", "N/A")
    confidence = analysis_data.get("confidence")
    processing_time = analysis_data.get("processing_time")

    # Build a metrics table
    risk_color = _risk_color(risk_label)
    metric_data = [
        [
            Paragraph('<font size="9" color="#475569">Risk Score</font>', styles["Body"]),
            Paragraph('<font size="9" color="#475569">Risk Level</font>', styles["Body"]),
            Paragraph('<font size="9" color="#475569">Confidence</font>', styles["Body"]),
            Paragraph('<font size="9" color="#475569">Processing Time</font>', styles["Body"]),
        ],
        [
            Paragraph(
                f'<font size="18"><b>{risk_score:.0f}</b></font>'
                f'<font size="10" color="#94A3B8"> / 100</font>',
                styles["Body"],
            ),
            Paragraph(
                f'<font size="14" color="{risk_color.hexval()}"><b>{risk_label}</b></font>',
                styles["Body"],
            ),
            Paragraph(
                f'<font size="14"><b>{confidence:.0%}</b></font>'
                if confidence is not None
                else '<font size="12" color="#94A3B8">N/A</font>',
                styles["Body"],
            ),
            Paragraph(
                f'<font size="14"><b>{processing_time:.2f}s</b></font>'
                if processing_time is not None
                else '<font size="12" color="#94A3B8">N/A</font>',
                styles["Body"],
            ),
        ],
    ]

    metrics_table = Table(
        metric_data,
        colWidths=[doc.width / 4] * 4,
        hAlign="LEFT",
    )
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _SECTION_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, _BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, _BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 3 * mm))

    # ---------------------------------------------------------------
    # SECTION 2: EXTRACTED FEATURES
    # ---------------------------------------------------------------
    elements.append(Paragraph("2. Extracted Features", styles["SectionHeading"]))

    features = analysis_data.get("features", {})
    feature_rows = [
        [
            Paragraph('<b>Feature</b>', styles["Body"]),
            Paragraph('<b>Value</b>', styles["Body"]),
        ]
    ]

    for key, (label, unit) in _FEATURE_LABELS.items():
        val = features.get(key)
        if val is None:
            display = "N/A"
        elif key == "undercut_present":
            display = "Yes" if val == 1 else "No"
        else:
            try:
                if unit:
                    display = f"{float(val):.2f} {unit}"
                else:
                    display = f"{float(val):.2f}"
            except (ValueError, TypeError):
                display = str(val)

        feature_rows.append([
            Paragraph(label, styles["Body"]),
            Paragraph(f"<b>{display}</b>", styles["Body"]),
        ])

    feature_table = Table(
        feature_rows,
        colWidths=[doc.width * 0.5, doc.width * 0.5],
        hAlign="LEFT",
    )
    feature_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), _TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
        # Alternating data rows
        *[
            ("BACKGROUND", (0, i), (-1, i), _TABLE_ALT_ROW)
            for i in range(2, len(feature_rows), 2)
        ],
        ("BOX", (0, 0), (-1, -1), 0.5, _BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, _BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(feature_table)
    elements.append(Spacer(1, 3 * mm))

    # ---------------------------------------------------------------
    # SECTION 3: DFM VIOLATIONS
    # ---------------------------------------------------------------
    elements.append(Paragraph("3. DFM Violations", styles["SectionHeading"]))

    violations = analysis_data.get("violations", [])
    if not violations:
        elements.append(
            Paragraph(
                '<font color="#22C55E">&#10003;</font> '
                "No major violations detected. The design meets all DFM thresholds.",
                styles["Body"],
            )
        )
    else:
        elements.append(
            Paragraph(
                f"<b>{len(violations)}</b> violation(s) detected:",
                styles["Body"],
            )
        )
        elements.append(Spacer(1, 2 * mm))

        for idx, v in enumerate(violations, 1):
            v_type = v.get("type", "INFO")
            v_color = _severity_color(v_type)
            severity = v.get("severity", 0)

            violation_block = []

            # Title line with severity badge
            violation_block.append(
                Paragraph(
                    f'<font color="{v_color.hexval()}"><b>[{v_type}]</b></font> '
                    f'<b>{v.get("message", "Unnamed violation")}</b> '
                    f'<font size="8" color="#94A3B8">(Severity: {severity})</font>',
                    styles["Body"],
                )
            )

            # Detail
            detail = v.get("detail", "")
            if detail:
                violation_block.append(
                    Paragraph(
                        f'<font color="#475569">{detail}</font>',
                        styles["Bullet"],
                    )
                )

            # Suggestion
            suggestion = v.get("suggestion", "")
            if suggestion:
                violation_block.append(
                    Paragraph(
                        f'<font color="#1E40AF"><b>Fix:</b></font> {suggestion}',
                        styles["Bullet"],
                    )
                )

            violation_block.append(Spacer(1, 2 * mm))
            elements.append(KeepTogether(violation_block))

    # ---------------------------------------------------------------
    # SECTION 4: TOP CONTRIBUTING FACTORS
    # ---------------------------------------------------------------
    elements.append(Paragraph("4. Top Contributing Factors", styles["SectionHeading"]))

    top_issues = analysis_data.get("top_issues", [])

    # Also try deriving from SHAP values if top_issues is empty
    if not top_issues:
        shap_data = analysis_data.get("shap_values", {})
        shap_vals = shap_data.get("shap_values", {}) if isinstance(shap_data, dict) else {}
        if shap_vals:
            sorted_shap = sorted(
                shap_vals.items(), key=lambda x: abs(x[1]), reverse=True
            )[:3]
            total_abs = sum(abs(v) for _, v in sorted_shap) or 1
            top_issues = [
                {
                    "feature": _FEATURE_LABELS.get(name, (name, ""))[0],
                    "impact_pct": round(abs(val) / total_abs * 100, 1),
                }
                for name, val in sorted_shap
            ]

    if not top_issues:
        elements.append(
            Paragraph(
                "Contributing factor analysis is not available for this report.",
                styles["Body"],
            )
        )
    else:
        factor_rows = [
            [
                Paragraph('<b>Rank</b>', styles["Body"]),
                Paragraph('<b>Factor</b>', styles["Body"]),
                Paragraph('<b>Contribution</b>', styles["Body"]),
            ]
        ]
        for idx, issue in enumerate(top_issues[:5], 1):
            feature_name = issue.get("feature", issue.get("name", "Unknown"))
            # Prettify feature name
            feature_label = _FEATURE_LABELS.get(feature_name, (feature_name, ""))[0] \
                if feature_name in _FEATURE_LABELS else feature_name

            pct = issue.get(
                "impact_pct",
                issue.get("contribution_pct", issue.get("percentage", 0)),
            )

            # Create a simple bar representation
            bar_width = int(pct / 5)  # Scale to ~20 chars max
            bar = "█" * bar_width

            factor_rows.append([
                Paragraph(f"<b>#{idx}</b>", styles["Body"]),
                Paragraph(feature_label, styles["Body"]),
                Paragraph(
                    f'<font color="{_BRAND_PRIMARY.hexval()}">{bar}</font> '
                    f'<b>{pct:.0f}%</b>',
                    styles["Body"],
                ),
            ])

        factor_table = Table(
            factor_rows,
            colWidths=[doc.width * 0.12, doc.width * 0.44, doc.width * 0.44],
            hAlign="LEFT",
        )
        factor_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _TABLE_HEADER),
            ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
            *[
                ("BACKGROUND", (0, i), (-1, i), _TABLE_ALT_ROW)
                for i in range(2, len(factor_rows), 2)
            ],
            ("BOX", (0, 0), (-1, -1), 0.5, _BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, _BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(factor_table)

    elements.append(Spacer(1, 3 * mm))

    # ---------------------------------------------------------------
    # SECTION 5: COST IMPACT
    # ---------------------------------------------------------------
    elements.append(Paragraph("5. Cost Impact", styles["SectionHeading"]))

    estimated_cost = analysis_data.get("estimated_cost_impact")
    cost_breakdown = analysis_data.get("cost_breakdown")

    if estimated_cost is None and isinstance(analysis_data.get("cost_impact"), dict):
        legacy = analysis_data.get("cost_impact", {})
        estimated_cost = legacy.get("estimated_cost", 0)
        cost_breakdown = legacy.get("breakdown", [])

    try:
        estimated_cost = max(0, int(float(estimated_cost or 0)))
    except (TypeError, ValueError):
        estimated_cost = 0

    if not isinstance(cost_breakdown, list) or not cost_breakdown:
        cost_breakdown = ["Minimal additional tooling cost"]

    elements.append(
        Paragraph(
            f'<b>Estimated Manufacturing Cost:</b> '
            f'<font size="14" color="{_BRAND_PRIMARY.hexval()}"><b>₹{estimated_cost:,.0f}</b></font>',
            styles["Body"],
        )
    )

    for reason in cost_breakdown:
        elements.append(Paragraph(f"• {reason}", styles["Bullet"]))

    elements.append(Spacer(1, 3 * mm))

    # ---------------------------------------------------------------
    # SECTION 6: AI RECOMMENDATIONS
    # ---------------------------------------------------------------
    elements.append(Paragraph("6. AI Recommendations", styles["SectionHeading"]))

    recommendations = analysis_data.get("recommendations", {})
    summary_text = ""
    rec_list = []

    if isinstance(recommendations, dict):
        summary_text = recommendations.get("summary", "")
        rec_list = recommendations.get("recommendations", [])
    elif isinstance(recommendations, list):
        rec_list = recommendations
    elif isinstance(recommendations, str):
        summary_text = recommendations

    if summary_text:
        elements.append(
            Paragraph(
                f'<i><font color="#475569">{summary_text}</font></i>',
                styles["Body"],
            )
        )
        elements.append(Spacer(1, 2 * mm))

    if rec_list:
        for idx, rec in enumerate(rec_list, 1):
            rec_text = str(rec).strip()
            # Strip markdown bold markers for PDF
            rec_text = rec_text.replace("**", "")
            elements.append(
                Paragraph(
                    f'<b>{idx}.</b> {rec_text}',
                    styles["Bullet"],
                )
            )
    else:
        elements.append(
            Paragraph(
                "No specific recommendations available at this time.",
                styles["Body"],
            )
        )

    # ---------------------------------------------------------------
    # FOOTER / DISCLAIMER
    # ---------------------------------------------------------------
    elements.append(Spacer(1, 10 * mm))
    elements.append(
        HRFlowable(
            width="100%", thickness=0.3, color=_BORDER_COLOR,
            spaceBefore=2 * mm, spaceAfter=4 * mm,
        )
    )
    elements.append(
        Paragraph(
            "This report was auto-generated by Varroc DesignCopilot AI. "
            "The analysis is based on machine learning predictions and rule-based "
            "DFM checks. Results should be validated by a qualified manufacturing engineer "
            "before making production decisions.",
            styles["SmallGrey"],
        )
    )

    analysis_id = analysis_data.get("id", "N/A")
    elements.append(
        Paragraph(
            f"Analysis ID: {analysis_id}",
            styles["SmallGrey"],
        )
    )

    # ---------------------------------------------------------------
    # BUILD
    # ---------------------------------------------------------------
    doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)

    return tmp_path
