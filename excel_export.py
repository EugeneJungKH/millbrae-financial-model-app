"""
Excel export for the Downtown Millbrae Financial Model Dashboard.

Builds a workbook containing the financial summary table and a native Excel
version of the Annual Revenue and Expenses chart.

Excel has no side-by-side stacked column chart, so each year gets one row for
revenue and one row for expenses on the Chart Data sheet.
"""

# import packages
from io import BytesIO
import xlsxwriter

SUMMARY_SHEET = "Financial Summary"
CHART_DATA_SHEET = "Chart Data"


def format_net_income(net_income):
    """Format net income the same way as the dashboard chart labels."""

    if net_income < 0:
        return f"-${abs(net_income):,.0f}"
    return f"${net_income:,.0f}"


def write_summary_table(workbook, worksheet, yearly_results, currency_columns):
    """Write the financial summary table and return the number of rows used."""

    header_format = workbook.add_format({"bold": True, "bottom": 1, "align": "center", "text_wrap": True})
    currency_format = workbook.add_format({"num_format": "$#,##0.00"})

    for column_index, column in enumerate(yearly_results.columns):
        worksheet.write(0, column_index, column, header_format)

        for row_index, value in enumerate(yearly_results[column], start=1):
            if column in currency_columns:
                worksheet.write_number(row_index, column_index, float(value), currency_format)
            else:
                worksheet.write_number(row_index, column_index, int(value))

    worksheet.set_column(0, 0, 8)
    worksheet.set_column(1, len(yearly_results.columns) - 1, 15)
    worksheet.freeze_panes(1, 1)

    return len(yearly_results) + 1


def write_chart_data(workbook, worksheet, yearly_results, revenue_columns, expense_columns):
    """Write the rows behind the chart and return the net income data labels."""

    header_format = workbook.add_format({"bold": True, "bottom": 1})
    currency_format = workbook.add_format({"num_format": "$#,##0.00"})
    chart_columns = revenue_columns + expense_columns
    label_column_index = 2 + len(chart_columns)

    headers = ["Year", "Group"] + chart_columns + ["Net Income Label Position"]
    for column_index, header in enumerate(headers):
        worksheet.write(0, column_index, header, header_format)

    net_income_labels = []
    row_index = 1

    for _, row in yearly_results.iterrows():
        # Net income sits above the taller of the two bars.
        label_group = "Revenue" if row["Total Revenue"] >= row["Total Expenses"] else "Expenses"

        for group, group_columns in (("Revenue", revenue_columns), ("Expenses", expense_columns)):
            # Excel groups the axis labels when the year only appears on its first row.
            if group == "Revenue":
                worksheet.write_number(row_index, 0, int(row["Years"]))
            worksheet.write(row_index, 1, group)

            for column_index, column in enumerate(chart_columns, start=2):
                if column in group_columns:
                    worksheet.write_number(row_index, column_index, float(row[column]), currency_format)

            if group == label_group:
                label_position = max(row["Total Revenue"], row["Total Expenses"])
                worksheet.write_number(row_index, label_column_index, float(label_position), currency_format)
                net_income_labels.append({"value": format_net_income(row["Net Income"])})
            else:
                net_income_labels.append({"delete": True})

            row_index += 1

    worksheet.set_column(0, 1, 10)
    worksheet.set_column(2, label_column_index, 15)

    return net_income_labels


def build_excel_file(yearly_results, revenue_columns, expense_columns, currency_columns, column_colors):
    """Return an Excel workbook of the summary table and chart as bytes."""

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    summary_sheet = workbook.add_worksheet(SUMMARY_SHEET)
    chart_data_sheet = workbook.add_worksheet(CHART_DATA_SHEET)

    table_rows = write_summary_table(workbook, summary_sheet, yearly_results, currency_columns)
    net_income_labels = write_chart_data(workbook, chart_data_sheet, yearly_results, revenue_columns, expense_columns)

    chart_columns = revenue_columns + expense_columns
    last_row = len(yearly_results) * 2
    label_column_index = 2 + len(chart_columns)
    categories = [CHART_DATA_SHEET, 1, 0, last_row, 1]

    # Add stacked revenue and expense components.
    chart = workbook.add_chart({"type": "column", "subtype": "stacked"})
    for column_index, column in enumerate(chart_columns, start=2):
        chart.add_series({
            "name": [CHART_DATA_SHEET, 0, column_index],
            "categories": categories,
            "values": [CHART_DATA_SHEET, 1, column_index, last_row, column_index],
            "fill": {"color": column_colors[column]},
            "gap": 40,
        })

    # Add net income above each year's bars using an invisible line.
    net_income_line = workbook.add_chart({"type": "line"})
    net_income_line.add_series({
        "name": "Net Income",
        "categories": categories,
        "values": [CHART_DATA_SHEET, 1, label_column_index, last_row, label_column_index],
        "line": {"none": True},
        "marker": {"type": "none"},
        "data_labels": {"value": True, "position": "above", "custom": net_income_labels, "font": {"size": 12}},
    })
    chart.combine(net_income_line)

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
    chart.set_size({"width": 900, "height": 450})

    chart_title_row = table_rows + 1
    summary_sheet.write(chart_title_row, 0, "Annual Revenue and Expenses", workbook.add_format({"bold": True, "font_size": 14}))
    summary_sheet.insert_chart(chart_title_row + 1, 0, chart)

    workbook.close()

    return output.getvalue()
