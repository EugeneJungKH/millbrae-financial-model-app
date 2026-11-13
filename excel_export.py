"""
Excel export for the Downtown Millbrae Financial Model Dashboard.

The workbook contains a formatted financial summary with a native Excel chart,
plus a separate assumptions sheet with the selected inputs and reference maps.
"""

from io import BytesIO
from math import ceil
from pathlib import Path
import re

from PIL import Image
import xlsxwriter


SUMMARY_SHEET = "Financial Summary"
ASSUMPTIONS_SHEET = "Assumptions & Maps"
CHART_DATA_START_COLUMN = 20
DATA_DIRECTORY = Path(__file__).resolve().parent / "data"


def _prepare_map_image(image_path):
    """Resize a reference map for display in Excel while preserving its on-sheet size."""

    image_data = BytesIO()
    with Image.open(image_path) as image:
        original_width, original_height = image.size
        image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
        scale = original_width * 0.18 / image.width
        image.save(image_data, format="PNG", optimize=True)
    image_data.seek(0)
    return image_data, scale


def format_net_income(net_income):
    """Format net income the same way as the dashboard chart labels."""

    if net_income < 0:
        return f"-${abs(net_income):,.0f}"
    return f"${net_income:,.0f}"


def format_hour(hour):
    """Format an integer hour in 12-hour time."""

    return f"{hour % 12 or 12}:00 {'AM' if hour < 12 else 'PM'}"


def write_summary_table(
    workbook,
    worksheet,
    yearly_results,
    revenue_columns,
    expense_columns,
    currency_columns,
    start_row=3,
):
    """Write the financial summary table and return the first row after it."""

    revenue_header_format = workbook.add_format({
        "bold": True,
        "font_color": "#34495E",
        "bg_color": "#E8F1F7",
        "bottom": 1,
        "bottom_color": "#CAD5DF",
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })
    expense_header_format = workbook.add_format({
        "bold": True,
        "font_color": "#754B3E",
        "bg_color": "#F8EEE8",
        "bottom": 1,
        "bottom_color": "#DCCFC7",
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })
    other_header_format = workbook.add_format({
        "bold": True,
        "font_color": "#344054",
        "bg_color": "#F2F4F7",
        "bottom": 1,
        "bottom_color": "#D0D5DD",
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })
    currency_format = workbook.add_format({
        "num_format": '$#,##0.00;[Red]($#,##0.00);-',
        "bottom": 1,
        "bottom_color": "#E6EAF1",
    })
    regular_format = workbook.add_format({
        "bottom": 1,
        "bottom_color": "#E6EAF1",
    })
    total_currency_format = workbook.add_format({
        "bold": True,
        "num_format": '$#,##0.00;[Red]($#,##0.00);-',
        "top": 1,
        "top_color": "#A6B7CC",
    })
    total_number_format = workbook.add_format({
        "bold": True,
        "top": 1,
        "top_color": "#A6B7CC",
    })
    net_income_format = workbook.add_format({
        "bold": True,
        "num_format": '$#,##0.00;[Red]($#,##0.00);-',
        "top": 1,
        "top_color": "#7F9DB9",
    })

    worksheet.set_row(start_row, 32)
    for column_index, column in enumerate(yearly_results.columns):
        if column in revenue_columns or column == "Total Revenue":
            header_format = revenue_header_format
        elif column in expense_columns or column == "Total Expenses":
            header_format = expense_header_format
        else:
            header_format = other_header_format
        worksheet.write(start_row, column_index, column, header_format)

        for row_offset, value in enumerate(yearly_results[column], start=1):
            row_index = start_row + row_offset
            is_total = column in {"Total Revenue", "Total Expenses"}
            is_net_income = column == "Net Income"
            if column in currency_columns:
                cell_format = net_income_format if is_net_income else (
                    total_currency_format if is_total else currency_format
                )
                worksheet.write_number(row_index, column_index, float(value), cell_format)
            else:
                cell_format = total_number_format if is_total else regular_format
                worksheet.write_number(row_index, column_index, int(value), cell_format)

    worksheet.autofilter(
        start_row,
        0,
        start_row + len(yearly_results),
        len(yearly_results.columns) - 1,
    )
    worksheet.set_column(0, 0, 10)
    worksheet.set_column(1, len(yearly_results.columns) - 1, 21)
    return start_row + len(yearly_results) + 1


def write_chart_data(workbook, worksheet, yearly_results, revenue_columns, expense_columns):
    """Write chart data into hidden columns and return the net income labels."""

    header_format = workbook.add_format({
        "bold": True,
        "bg_color": "#17365D",
        "font_color": "#FFFFFF",
    })
    currency_format = workbook.add_format({"num_format": "$#,##0.00"})
    chart_columns = revenue_columns + expense_columns
    start_column = CHART_DATA_START_COLUMN
    label_column_index = start_column + 2 + len(chart_columns)

    headers = ["Year", "Group"] + chart_columns + ["Net Income Label Position"]
    for column_offset, header in enumerate(headers):
        worksheet.write(0, start_column + column_offset, header, header_format)

    net_income_labels = []
    row_index = 1

    for _, row in yearly_results.iterrows():
        label_group = "Revenue" if row["Total Revenue"] >= row["Total Expenses"] else "Expenses"

        for group, group_columns in (("Revenue", revenue_columns), ("Expenses", expense_columns)):
            if group == "Revenue":
                worksheet.write_number(row_index, start_column, int(row["Years"]))
            worksheet.write(row_index, start_column + 1, group)

            for column_offset, column in enumerate(chart_columns, start=start_column + 2):
                if column in group_columns:
                    worksheet.write_number(row_index, column_offset, float(row[column]), currency_format)

            if group == label_group:
                label_position = max(row["Total Revenue"], row["Total Expenses"])
                worksheet.write_number(row_index, label_column_index, float(label_position), currency_format)
                net_income_labels.append({"value": format_net_income(row["Net Income"])})
            else:
                net_income_labels.append({"delete": True})

            row_index += 1

    worksheet.set_column(
        start_column,
        label_column_index,
        None,
        None,
        {"hidden": True},
    )
    return net_income_labels, row_index - 1, label_column_index


def _write_assumptions_sheet(
    workbook,
    worksheet,
    parking_operator,
    rpp_mode,
    meter_type,
    weekday_start_hour,
    weekday_end_hour,
    onstreet_hourly_rate,
    offstreet_hourly_rate,
    permit_rate,
    rpp_rate,
    attrition_rate,
    inhouse_scaling_factor,
    analysis_period,
    sunday_parking_enabled,
    credit_card_processing_fee_enabled,
    credit_card_percentage,
):
    """Write the selected inputs, model assumptions, and parking maps."""

    title_format = workbook.add_format({
        "bold": True,
        "font_size": 20,
        "font_color": "#17365D",
        "valign": "vcenter",
    })
    section_format = workbook.add_format({
        "bold": True,
        "font_size": 12,
        "font_color": "#17365D",
        "bottom": 1,
        "bottom_color": "#D0D5DD",
        "valign": "vcenter",
    })
    label_format = workbook.add_format({
        "bold": True,
        "bottom": 1,
        "bottom_color": "#E6EAF1",
        "valign": "top",
    })
    value_format = workbook.add_format({
        "bottom": 1,
        "bottom_color": "#E6EAF1",
        "valign": "top",
    })
    currency_format = workbook.add_format({
        "bottom": 1,
        "bottom_color": "#E6EAF1",
        "num_format": '$#,##0.00;[Red]($#,##0.00);-',
    })
    assumption_text_format = workbook.add_format({
        "text_wrap": True,
        "valign": "top",
        "font_color": "#344054",
    })
    assumption_bullet_format = workbook.add_format({
        "text_wrap": True,
        "valign": "top",
        "font_color": "#344054",
        "indent": 1,
    })
    percentage_format = workbook.add_format({
        "bottom": 1,
        "bottom_color": "#E6EAF1",
        "num_format": "0.0%",
    })

    worksheet.merge_range(0, 0, 0, 2, "Assumptions & Reference Maps", title_format)
    worksheet.set_row(0, 34)

    worksheet.merge_range(2, 0, 2, 1, "Selected Scenario Inputs", section_format)
    daily_rate = offstreet_hourly_rate * 4
    inputs = [
        ("Parking Operator", parking_operator, None),
        ("RPP Mode", rpp_mode, None),
        ("Paystation Type", meter_type, None),
        ("Weekday Hours of Operation", f"{format_hour(weekday_start_hour)} - {format_hour(weekday_end_hour)}", None),
        ("On-Street Hourly Rate", onstreet_hourly_rate, "currency"),
        ("Off-Street Hourly Rate", offstreet_hourly_rate, "currency"),
        ("Off-Street Daily Maximum (4x hourly rate)", daily_rate, "currency"),
        ("Monthly Permit Rate", permit_rate, "currency"),
        ("Annual RPP Rate", rpp_rate, "currency"),
        ("Attrition Rate per $1 Rate Increase", attrition_rate, "percentage"),
        ("In-House Scaling Increase", inhouse_scaling_factor - 1, "percentage"),
        ("Analysis Period", f"{analysis_period} years", None),
        ("Sunday Parking", "Included" if sunday_parking_enabled else "Not included", None),
        ("Credit Card Processing Fee", "Included" if credit_card_processing_fee_enabled else "Not included", None),
        ("Credit Card Transaction Share", credit_card_percentage, "percentage"),
    ]

    for row_index, (label, value, value_type) in enumerate(inputs, start=3):
        worksheet.write(row_index, 0, label, label_format)
        if value_type == "currency":
            worksheet.write_number(row_index, 1, float(value), currency_format)
        elif value_type == "percentage":
            worksheet.write_number(row_index, 1, float(value), percentage_format)
        else:
            worksheet.write(row_index, 1, value, value_format)

    model_assumptions_header_row = len(inputs) + 4
    worksheet.merge_range(
        model_assumptions_header_row,
        0,
        model_assumptions_header_row,
        2,
        "Model Assumptions",
        section_format,
    )

    assumptions_path = Path(__file__).resolve().parent / "assumptions.md"
    assumption_row = model_assumptions_header_row + 1
    for line in assumptions_path.read_text(encoding="utf-8").splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue
        if stripped_line.startswith("#"):
            text = stripped_line.lstrip("#").strip()
            worksheet.merge_range(assumption_row, 0, assumption_row, 2, text, section_format)
            worksheet.set_row(assumption_row, 22)
        else:
            indentation = len(line) - len(line.lstrip())
            is_sub_bullet = indentation > 0 and stripped_line.startswith("- ")
            text = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped_line)
            if is_sub_bullet:
                text = f"- {text[2:]}"
                cell_format = assumption_bullet_format
            else:
                cell_format = assumption_text_format
            worksheet.merge_range(assumption_row, 0, assumption_row, 2, text, cell_format)
            worksheet.set_row(assumption_row, max(30, min(90, 15 * ceil(len(text) / 95))))
        assumption_row += 1

    worksheet.merge_range(0, 3, 0, 11, "Parking Space Allocation Map", section_format)
    worksheet.merge_range(35, 3, 35, 11, "Residential Parking Permit Map", section_format)
    allocation_map, allocation_map_scale = _prepare_map_image(
        DATA_DIRECTORY / "11x17 RFP 061026_Page_1.png"
    )
    permit_map, permit_map_scale = _prepare_map_image(
        DATA_DIRECTORY / "11x17 RFP 061026_Page_3.png"
    )
    worksheet.insert_image(
        1,
        3,
        str(DATA_DIRECTORY / "11x17 RFP 061026_Page_1.png"),
        {
            "image_data": allocation_map,
            "x_scale": allocation_map_scale,
            "y_scale": allocation_map_scale,
            "object_position": 1,
        },
    )
    worksheet.insert_image(
        36,
        3,
        str(DATA_DIRECTORY / "11x17 RFP 061026_Page_3.png"),
        {
            "image_data": permit_map,
            "x_scale": permit_map_scale,
            "y_scale": permit_map_scale,
            "object_position": 1,
        },
    )

    worksheet.set_column(0, 0, 43)
    worksheet.set_column(1, 1, 24)
    worksheet.set_column(2, 2, 4)
    worksheet.set_column(3, 11, 12)
    worksheet.hide_gridlines(2)
    worksheet.set_zoom(75)
    worksheet.set_landscape()
    worksheet.fit_to_pages(1, 0)
    worksheet.set_tab_color("#70AD47")


def build_excel_file(
    yearly_results,
    revenue_columns,
    expense_columns,
    currency_columns,
    column_colors,
    parking_operator,
    rpp_mode,
    meter_type,
    weekday_start_hour,
    weekday_end_hour,
    onstreet_hourly_rate,
    offstreet_hourly_rate,
    permit_rate,
    rpp_rate,
    attrition_rate,
    inhouse_scaling_factor,
    analysis_period,
    sunday_parking_enabled,
    credit_card_processing_fee_enabled,
    credit_card_percentage,
):
    """Return a formatted Excel workbook containing the summary and assumptions."""

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    summary_sheet = workbook.add_worksheet(SUMMARY_SHEET)
    assumptions_sheet = workbook.add_worksheet(ASSUMPTIONS_SHEET)

    title_format = workbook.add_format({
        "bold": True,
        "font_size": 20,
        "font_color": "#17365D",
        "valign": "vcenter",
    })
    subtitle_format = workbook.add_format({
        "font_size": 10,
        "font_color": "#5B6573",
        "italic": True,
    })
    section_format = workbook.add_format({
        "bold": True,
        "font_size": 13,
        "font_color": "#17365D",
    })

    last_summary_column = len(yearly_results.columns) - 1
    summary_sheet.merge_range(0, 0, 0, last_summary_column, "Downtown Millbrae Financial Model", title_format)
    summary_sheet.set_row(0, 36)
    summary_sheet.merge_range(
        1,
        0,
        1,
        last_summary_column,
        f"{rpp_mode} RPP | {parking_operator} | {meter_type} | {analysis_period}-year analysis",
        subtitle_format,
    )
    summary_sheet.write(2, 0, "Annual Financial Summary", section_format)

    table_end_row = write_summary_table(
        workbook,
        summary_sheet,
        yearly_results,
        revenue_columns,
        expense_columns,
        currency_columns,
        start_row=3,
    )

    net_income_labels, last_chart_row, label_column_index = write_chart_data(
        workbook,
        summary_sheet,
        yearly_results,
        revenue_columns,
        expense_columns,
    )

    chart_start_column = CHART_DATA_START_COLUMN
    chart_columns = revenue_columns + expense_columns
    categories = [
        SUMMARY_SHEET,
        1,
        chart_start_column,
        last_chart_row,
        chart_start_column + 1,
    ]

    chart = workbook.add_chart({"type": "column", "subtype": "stacked"})
    for column_index, column in enumerate(chart_columns, start=chart_start_column + 2):
        chart.add_series({
            "name": [SUMMARY_SHEET, 0, column_index],
            "categories": categories,
            "values": [SUMMARY_SHEET, 1, column_index, last_chart_row, column_index],
            "fill": {"color": column_colors[column]},
            "gap": 40,
        })

    net_income_line = workbook.add_chart({"type": "line"})
    net_income_line.add_series({
        "name": "Net Income",
        "categories": categories,
        "values": [SUMMARY_SHEET, 1, label_column_index, last_chart_row, label_column_index],
        "line": {"none": True},
        "marker": {"type": "none"},
        "data_labels": {
            "value": True,
            "position": "above",
            "custom": net_income_labels,
            "font": {"size": 10, "color": "#344054"},
        },
    })
    chart.combine(net_income_line)
    chart.show_hidden_data()
    chart.set_title({"none": True})
    chart.set_x_axis({"name": "Year", "name_font": {"bold": False}})
    chart.set_y_axis({
        "name": "Amount ($)",
        "name_font": {"bold": False},
        "num_format": '0.0,,"M"',
        "major_gridlines": {"visible": True, "line": {"color": "#E6EAF1"}},
        "line": {"none": True},
    })
    chart.set_legend({"position": "right", "delete_series": [len(chart_columns)]})
    chart.set_chartarea({"border": {"none": True}})
    chart.set_plotarea({"border": {"none": True}})
    chart.set_size({"width": 900, "height": 450})

    chart_title_row = table_end_row + 1
    summary_sheet.write(chart_title_row, 0, "Annual Revenue and Expenses", section_format)
    summary_sheet.insert_chart(chart_title_row + 1, 0, chart)
    summary_sheet.set_column(0, 0, 14)
    summary_sheet.set_column(1, last_summary_column, 18)
    summary_sheet.hide_gridlines(2)
    summary_sheet.set_zoom(85)
    summary_sheet.set_landscape()
    summary_sheet.fit_to_pages(1, 0)
    summary_sheet.set_tab_color("#17365D")

    _write_assumptions_sheet(
        workbook,
        assumptions_sheet,
        parking_operator,
        rpp_mode,
        meter_type,
        weekday_start_hour,
        weekday_end_hour,
        onstreet_hourly_rate,
        offstreet_hourly_rate,
        permit_rate,
        rpp_rate,
        attrition_rate,
        inhouse_scaling_factor,
        analysis_period,
        sunday_parking_enabled,
        credit_card_processing_fee_enabled,
        credit_card_percentage,
    )

    workbook.close()
    return output.getvalue()
