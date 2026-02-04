"""
PDF export functionality for screener and backtest results.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from slickbet.backtest import BacktestResults
from slickbet.screener import BetPrediction, ScreenerResult, to_central_time


def get_pdf_output_path(filename: str, output_path: Optional[str] = None) -> str:
    """
    Get the full path for PDF output, creating directory if needed.

    Parameters
    ----------
    filename : str
        Default filename if output_path is None
    output_path : str or None, optional
        Optional custom output path (can be file or directory)

    Returns
    -------
    str
        Full path to the PDF file
    """
    # Treat empty string as None to use default directory
    if output_path is None or output_path == "":
        # Use default directory: assets/predictions
        default_dir = Path("assets/predictions")
        default_dir.mkdir(parents=True, exist_ok=True)
        output_path = default_dir / filename
    else:
        # Custom path provided
        custom_path = Path(output_path)

        # If it's an absolute path, use it as-is
        if custom_path.is_absolute():
            output_path = custom_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
        # Check if it's an existing directory
        elif custom_path.exists() and custom_path.is_dir():
            # It's a directory, append filename
            output_path = custom_path / filename
        else:
            # It's a relative filename/path
            # Check if it has directory components (more than just a filename)
            if len(custom_path.parts) > 1:
                # It has directory components, use as-is (relative to current dir)
                output_path = custom_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                # It's just a filename - put it in default directory
                default_dir = Path("assets/predictions")
                default_dir.mkdir(parents=True, exist_ok=True)
                output_path = default_dir / custom_path.name

    # Ensure .pdf extension
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".pdf":
        output_path = output_path.with_suffix(".pdf")

    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    return str(output_path)


def export_screener_to_pdf(
    result: ScreenerResult,
    predictions: list[BetPrediction],
    output_path: Optional[str] = None,
) -> str:
    """
    Export screener results to a PDF file.

    Parameters
    ----------
    result : ScreenerResult
        The screener result
    predictions : list[BetPrediction]
        List of predictions to include
    output_path : str or None, optional
        Optional output file path. If None, generates a filename.

    Returns
    -------
    str
        Path to the generated PDF file
    """
    # Treat empty string as None to use default directory
    if output_path is None or output_path == "":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"slickbet_screener_{timestamp}.pdf"
        output_path = get_pdf_output_path(filename)
    else:
        # Custom path provided - use it directly
        output_path = get_pdf_output_path("slickbet_screener.pdf", output_path)

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=30,
        alignment=1,  # Center
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=16,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=12,
    )
    subheading_style = ParagraphStyle(
        "CustomSubheading",
        parent=styles["Heading3"],
        fontSize=14,
        textColor=colors.HexColor("#34495e"),
        spaceAfter=10,
    )

    # Title
    story.append(Paragraph("🎰 SlickBet - Betting Screener Report", title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Summary Section
    story.append(Paragraph("📊 Screening Summary", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    summary_data = [
        ["Metric", "Value"],
        ["Total Matches Scanned", str(result.total_matches_scanned)],
        ["Matches After Filtering", str(result.matches_filtered)],
        ["Actionable Predictions", str(len(result.predictions))],
        ["Home Win Predictions", str(len(result.get_home_wins()))],
        ["Away Win Predictions", str(len(result.get_away_wins()))],
        [
            "Screened At",
            to_central_time(result.timestamp).strftime("%Y-%m-%d %H:%M:%S %Z"),
        ],
    ]

    summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f8f9fa")],
                ),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))

    # Disclaimer Section
    disclaimer_style = ParagraphStyle(
        "DisclaimerStyle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#7f8c8d"),
        alignment=1,  # Center
        spaceAfter=12,
    )
    story.append(
        Paragraph(
            "<i><b>⚠️ DISCLAIMER:</b> This tool is for educational and research purposes only. "
            "We are not providing financial advice, and we are not responsible for any financial "
            "decisions made based on this information. Sports betting involves risk of financial loss. "
            "Always predict responsibly and within your means.</i>",
            disclaimer_style,
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        Paragraph(
            "<i>Powered by SlickML LLC</i>",
            ParagraphStyle(
                "PoweredByStyle",
                parent=styles["Normal"],
                fontSize=8,
                textColor=colors.HexColor("#95a5a6"),
                alignment=1,  # Center
            ),
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    # Predictions Section
    if predictions:
        for i, pred in enumerate(predictions, 1):
            # Start each recommendation on a new page
            story.append(PageBreak())

            match = pred.match
            outcome = pred.recommended_outcome

            # Determine which team to bet on
            if outcome.value == "home_win":
                bet_on = match.home_team.name
                bet_against = match.away_team.name
            else:
                bet_on = match.away_team.name
                bet_against = match.home_team.name

            # Confidence Grade
            from slickbet.screener import get_best_double_chance_prob

            best_dc_prob = get_best_double_chance_prob(pred)
            if best_dc_prob >= 0.80 and pred.probability >= 0.65:
                grade = "🔥 HIGH VALUE"
                grade_color = colors.HexColor("#27ae60")
            elif best_dc_prob >= 0.75 and pred.probability >= 0.60:
                grade = "✅ GOOD BET"
                grade_color = colors.HexColor("#2ecc71")
            elif best_dc_prob >= 0.70:
                grade = "👍 DECENT"
                grade_color = colors.HexColor("#f39c12")
            else:
                grade = "⚠️ RISKY"
                grade_color = colors.HexColor("#e74c3c")

            # Match header
            home_pos = f"({match.home_position})" if match.home_position else ""
            away_pos = f"({match.away_position})" if match.away_position else ""
            match_title = (
                f"#{i} {match.home_team.name} {home_pos} vs {match.away_team.name} {away_pos}"
            )
            story.append(Paragraph(match_title, subheading_style))
            story.append(
                Paragraph(
                    f"<b>{match.competition}</b> ({match.country}) • {to_central_time(match.kickoff_time).strftime('%Y-%m-%d %H:%M %Z')}",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"<b>Grade:</b> <font color='{grade_color.hexval()}'>{grade}</font>",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 0.1 * inch))

            # Double Chance Recommendation
            if pred.double_chance:
                dc = pred.double_chance
                best_type, best_prob = dc.best_double_chance

                if "1X" in best_type:
                    bet_desc = f"{match.home_team.name} wins OR Draw"
                    short_bet = "1X"
                elif "X2" in best_type:
                    bet_desc = f"{match.away_team.name} wins OR Draw"
                    short_bet = "X2"
                else:
                    bet_desc = "Either team wins (no draw)"
                    short_bet = "12"

                story.append(Paragraph(f"<b>⭐ Recommended Bet: {short_bet}</b>", styles["Normal"]))
                story.append(Paragraph(f"   {bet_desc}", styles["Normal"]))
                story.append(Paragraph(f"   Probability: <b>{best_prob:.1%}</b>", styles["Normal"]))
                story.append(Spacer(1, 0.05 * inch))

            # Win Bet
            story.append(Paragraph(f"<b>💰 Win Bet:</b> {bet_on.upper()} TO WIN", styles["Normal"]))
            story.append(
                Paragraph(f"   Probability: <b>{pred.probability:.1%}</b>", styles["Normal"])
            )
            story.append(Spacer(1, 0.1 * inch))

            # Analysis Breakdown
            analysis_data = [
                ["Factor", "Score"],
                ["Form Score", f"{pred.form_score:+.2f}"],
                ["Position Score", f"{pred.position_score:+.2f}"],
                ["Home Advantage", f"{pred.home_advantage_score:+.2f}"],
                ["H2H Score", f"{pred.h2h_score:+.2f}"],
            ]

            if pred.odds_score != 0:
                analysis_data.append(["Odds Score", f"{pred.odds_score:+.2f}"])
            if pred.goal_score != 0:
                analysis_data.append(["Goals (Attack/Defense)", f"{pred.goal_score:+.2f}"])
            if pred.venue_form_score != 0:
                analysis_data.append(["Venue Form", f"{pred.venue_form_score:+.2f}"])
            if pred.defense_score != 0:
                analysis_data.append(["Defense (Clean Sheets)", f"{pred.defense_score:+.2f}"])
            if pred.momentum_score != 0:
                analysis_data.append(["Momentum", f"{pred.momentum_score:+.2f}"])

            analysis_table = Table(analysis_data, colWidths=[2.5 * inch, 1.5 * inch])
            analysis_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
                    ]
                )
            )
            story.append(analysis_table)

            # Key Insights
            key_reasons = [r for r in pred.reasoning if not r.startswith("🎲")][:5]
            if key_reasons:
                story.append(Spacer(1, 0.1 * inch))
                story.append(Paragraph("<b>📝 Key Insights:</b>", styles["Normal"]))
                for reason in key_reasons:
                    # Remove emojis for cleaner PDF
                    clean_reason = (
                        reason.replace("🔥", "")
                        .replace("✅", "")
                        .replace("👍", "")
                        .replace("⚠️", "")
                        .strip()
                    )
                    story.append(Paragraph(f"   • {clean_reason}", styles["Normal"]))

            # Disclaimer at the bottom of each recommendation
            story.append(Spacer(1, 0.2 * inch))
            story.append(
                Paragraph(
                    "<i>Past performance does not guarantee future results. Always 'predict' responsibly.</i>",
                    ParagraphStyle(
                        "DisclaimerStyle",
                        parent=styles["Normal"],
                        fontSize=8,
                        textColor=colors.HexColor("#7f8c8d"),
                        alignment=1,  # Center alignment
                    ),
                )
            )

            # Each recommendation ends here, next one will start on new page
            # (PageBreak is added at the start of each loop iteration)

    # Footer note (simplified since we have a prominent disclaimer after summary)
    story.append(Spacer(1, 0.2 * inch))

    # Build PDF
    doc.build(story)
    return output_path


def export_backtest_to_pdf(
    results: BacktestResults,
    output_path: Optional[str] = None,
) -> str:
    """
    Export backtest results to a PDF file.

    Parameters
    ----------
    results : BacktestResult
        The backtest results
    output_path : str or None, optional
        Optional output file path. If None, generates a filename.

    Returns
    -------
    str
        Path to the generated PDF file
    """
    # Treat empty string as None to use default directory
    if output_path is None or output_path == "":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"slickbet_backtest_{timestamp}.pdf"
        output_path = get_pdf_output_path(filename)
    else:
        # Custom path provided - use it directly
        output_path = get_pdf_output_path("slickbet_backtest.pdf", output_path)

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=30,
        alignment=1,  # Center
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=16,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=12,
    )

    # Title
    story.append(Paragraph("📊 SlickBet - Backtest Report", title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Competition and Period
    story.append(Paragraph("Test Details", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    details_data = [
        ["Competition", results.competition],
        [
            "Period",
            f"{results.from_date.strftime('%Y-%m-%d') if results.from_date else 'N/A'} to "
            f"{results.to_date.strftime('%Y-%m-%d') if results.to_date else 'N/A'}",
        ],
    ]

    details_table = Table(details_data, colWidths=[2 * inch, 3 * inch])
    details_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
            ]
        )
    )
    story.append(details_table)
    story.append(Spacer(1, 0.3 * inch))

    # Overall Performance
    story.append(Paragraph("📈 Overall Performance", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    total = results.total_predictions
    draws_pct = (results.draws_encountered / total * 100) if total > 0 else 0

    performance_data = [
        ["Metric", "Value"],
        ["Total Predictions", str(total)],
        ["Correct Predictions", str(results.correct_predictions)],
        ["Overall Accuracy", f"{results.accuracy:.1%}"],
        ["Draws Encountered", f"{results.draws_encountered} ({draws_pct:.1f}%)"],
        ["Accuracy (excl. draws)", f"{results.accuracy_excluding_draws:.1%}"],
    ]

    performance_table = Table(performance_data, colWidths=[3 * inch, 2 * inch])
    performance_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f8f9fa")],
                ),
            ]
        )
    )
    story.append(performance_table)
    story.append(Spacer(1, 0.3 * inch))

    # Home vs Away
    story.append(Paragraph("🏠 Home vs ✈️ Away Predictions", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    home_pct = (len(results.home_predictions) / total * 100) if total > 0 else 0
    away_pct = (len(results.away_predictions) / total * 100) if total > 0 else 0

    home_away_data = [
        ["Type", "Count", "Percentage", "Accuracy"],
        [
            "Home Win",
            str(len(results.home_predictions)),
            f"{home_pct:.1f}%",
            f"{results.home_accuracy:.1%}",
        ],
        [
            "Away Win",
            str(len(results.away_predictions)),
            f"{away_pct:.1f}%",
            f"{results.away_accuracy:.1%}",
        ],
    ]

    home_away_table = Table(home_away_data, colWidths=[1.5 * inch, 1 * inch, 1 * inch, 1.5 * inch])
    home_away_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
            ]
        )
    )
    story.append(home_away_table)
    story.append(Spacer(1, 0.3 * inch))

    # Double Chance Analysis
    story.append(Paragraph("🎲 Double Chance Analysis (Safer Bets)", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    dc_data = [
        ["Bet Type", "Accuracy"],
        ["1X (Home or Draw)", f"{results.home_or_draw_accuracy:.1%}"],
        ["X2 (Away or Draw)", f"{results.away_or_draw_accuracy:.1%}"],
        ["Best Recommended DC", f"{results.best_double_chance_accuracy:.1%}"],
    ]

    dc_table = Table(dc_data, colWidths=[3 * inch, 2 * inch])
    dc_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#27ae60")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
            ]
        )
    )
    story.append(dc_table)
    story.append(Spacer(1, 0.3 * inch))

    # Confidence Analysis
    story.append(Paragraph("🎯 Confidence & Probability Analysis", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    confidence_data = [
        ["Category", "Count", "Accuracy", "Accuracy (excl. draws)"],
        [
            "High Confidence (>30%)",
            str(len(results.high_confidence_results)),
            f"{results.high_confidence_accuracy:.1%}",
            f"{results.high_confidence_accuracy_excl_draws:.1%}",
        ],
        [
            "High Probability (>60%)",
            str(len(results.high_probability_results)),
            f"{results.high_probability_accuracy:.1%}",
            f"{results.high_probability_accuracy_excl_draws:.1%}",
        ],
        [
            "Low Draw Risk (<30%)",
            str(len(results.low_draw_risk_results)),
            f"{results.low_draw_risk_accuracy:.1%}",
            "N/A",
        ],
    ]

    confidence_table = Table(
        confidence_data, colWidths=[2 * inch, 1 * inch, 1.2 * inch, 1.8 * inch]
    )
    confidence_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#9b59b6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
            ]
        )
    )
    story.append(confidence_table)

    # Footer note
    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            "<i>⚠️ Disclaimer: This tool is for educational and entertainment purposes only. "
            "Past performance does not guarantee future results. Always 'predict' responsibly.</i>",
            styles["Normal"],
        )
    )

    # Build PDF
    doc.build(story)
    return output_path


def export_backtest_all_to_pdf(
    league_summaries: list[dict],
    all_results: list,
    league_type: str,
    weeks: int,
    output_path: Optional[str] = None,
) -> str:
    """
    Export aggregated backtest results (from backtest-all) to a PDF file.

    Parameters
    ----------
    league_summaries : list[dict]
        List of league summary dictionaries
    all_results : list
        List of all prediction results
    league_type : str
        Type of leagues tested (e.g., "major European", "Persian Gulf")
    weeks : int
        Number of weeks tested
    output_path : str or None, optional
        Optional output file path. If None, generates a filename.

    Returns
    -------
    str
        Path to the generated PDF file
    """
    # Treat empty string as None to use default directory
    if output_path is None or output_path == "":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"slickbet_backtest_all_{timestamp}.pdf"
        output_path = get_pdf_output_path(filename)
    else:
        # Custom path provided - use it directly
        output_path = get_pdf_output_path("slickbet_backtest_all.pdf", output_path)

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=30,
        alignment=1,  # Center
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=16,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=12,
    )

    # Title
    story.append(Paragraph("📊 SlickBet - All Leagues Backtest Report", title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Test Details
    story.append(Paragraph("Test Details", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    details_data = [
        ["Leagues Tested", league_type],
        ["Number of Leagues", str(len(league_summaries))],
        ["Period", f"{weeks} weeks"],
    ]

    details_table = Table(details_data, colWidths=[2 * inch, 3 * inch])
    details_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
            ]
        )
    )
    story.append(details_table)
    story.append(Spacer(1, 0.3 * inch))

    # Aggregated Results
    story.append(Paragraph("📊 Aggregated Results (All Leagues)", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    total_matches = len(all_results)
    correct = sum(1 for r in all_results if r.is_correct)
    draws = sum(1 for r in all_results if r.actual_outcome == "D")
    non_draws = [r for r in all_results if r.actual_outcome != "D"]
    home_or_draw_correct = sum(1 for r in all_results if r.home_or_draw_correct)
    away_or_draw_correct = sum(1 for r in all_results if r.away_or_draw_correct)
    best_dc_correct = sum(1 for r in all_results if r.best_double_chance_correct)

    aggregated_data = [
        ["Metric", "Value"],
        ["Total Matches", str(total_matches)],
        ["Correct Predictions", str(correct)],
        ["Overall Accuracy", f"{correct / total_matches:.1%}"],
        ["Draws Encountered", f"{draws} ({draws / total_matches * 100:.1f}%)"],
        [
            "Accuracy (excl. draws)",
            f"{sum(1 for r in non_draws if r.is_correct) / max(len(non_draws), 1):.1%}",
        ],
    ]

    aggregated_table = Table(aggregated_data, colWidths=[3 * inch, 2 * inch])
    aggregated_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f8f9fa")],
                ),
            ]
        )
    )
    story.append(aggregated_table)
    story.append(Spacer(1, 0.3 * inch))

    # Double Chance
    story.append(Paragraph("🎲 Double Chance (Aggregated)", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    dc_data = [
        ["Bet Type", "Accuracy"],
        ["1X (Home or Draw)", f"{home_or_draw_correct / total_matches:.1%}"],
        ["X2 (Away or Draw)", f"{away_or_draw_correct / total_matches:.1%}"],
        ["Best Recommended DC", f"{best_dc_correct / total_matches:.1%}"],
    ]

    dc_table = Table(dc_data, colWidths=[3 * inch, 2 * inch])
    dc_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#27ae60")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
            ]
        )
    )
    story.append(dc_table)
    story.append(Spacer(1, 0.3 * inch))

    # League Comparison
    story.append(Paragraph("📈 League Comparison", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    # Sort by accuracy excluding draws
    sorted_leagues = sorted(league_summaries, key=lambda x: x["accuracy_excl_draws"], reverse=True)

    league_data = [
        ["League", "Matches", "Accuracy", "Excl. Draws", "Best DC"],
    ]

    for league in sorted_leagues:
        league_data.append(
            [
                league["name"],
                str(league["total"]),
                f"{league['accuracy']:.1%}",
                f"{league['accuracy_excl_draws']:.1%}",
                f"{league['best_dc']:.1%}",
            ]
        )

    league_table = Table(
        league_data,
        colWidths=[2.5 * inch, 0.8 * inch, 0.8 * inch, 1 * inch, 0.9 * inch],
    )
    league_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f8f9fa")],
                ),
            ]
        )
    )
    story.append(league_table)

    # Footer note
    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            "<i>⚠️ Disclaimer: This tool is for educational and entertainment purposes only. "
            "Past performance does not guarantee future results. Always predict responsibly.</i>",
            styles["Normal"],
        )
    )

    # Build PDF
    doc.build(story)
    return output_path
