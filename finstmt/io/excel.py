"""Excel export for financial statements."""

from typing import TYPE_CHECKING, Dict

import pandas as pd

if TYPE_CHECKING:
    from finstmt.core.statement_series import StatementSeries


def statements_to_excel(
    statements: Dict[str, "StatementSeries"],
    filepath: str,
    separate_sheets: bool = True,
) -> None:
    """
    Save financial statements to an Excel file with statement headers.

    :param statements: Dict mapping statement names to StatementSeries objects
    :param filepath: Path where the Excel file should be saved
    :param separate_sheets: If True, creates separate sheet for each statement.
                          If False, combines all statements into one sheet
    """
    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
        workbook = writer.book
        money_fmt = workbook.add_format({
            'num_format': '$#,##0',
            'align': 'right'
        })
        header_fmt = workbook.add_format({
            'bold': True,
            'align': 'center'
        })
        title_fmt = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'left'
        })

        if separate_sheets:
            for statement_series in statements.values():
                df = statement_series.df.copy()
                df.fillna(0, inplace=True)
                df.columns = [pd.to_datetime(col).strftime("%m/%d/%Y") for col in df.columns]

                sheet_name = statement_series.statement_name
                # Write statement name first, then data starting one row down
                df.to_excel(writer, sheet_name=sheet_name, startrow=1)

                worksheet = writer.sheets[sheet_name]
                worksheet.write(0, 0, sheet_name, title_fmt)

                for idx, col in enumerate(df.columns, start=1):
                    worksheet.set_column(idx, idx, 15, money_fmt)

                worksheet.set_row(1, None, header_fmt)  # Headers now on row 1 instead of 0
                worksheet.set_column(0, 0, 30)
        else:
            all_dfs = []
            current_row = 0

            for (statement_name, statement_series) in statements.items():
                df = statement_series.df.copy()
                df.fillna(0, inplace=True)
                df.index = [f"{idx}" for idx in df.index]
                all_dfs.append((statement_name, df))

            # Create single worksheet
            worksheet = workbook.add_worksheet('Financial Statements')

            # Write each statement with its header
            for stmt_name, df in all_dfs:
                # Write statement header
                worksheet.write(current_row, 0, stmt_name, title_fmt)
                current_row += 1

                # Convert df to formatted dates
                df.columns = [pd.to_datetime(col).strftime("%m/%d/%Y") for col in df.columns]

                # Write column headers
                for idx, col in enumerate(df.columns):
                    worksheet.write(current_row, idx + 1, col, header_fmt)

                # Write index
                for idx, row in enumerate(df.index):
                    worksheet.write(current_row + 1 + idx, 0, row)

                # Write data
                for row_idx, row in enumerate(df.values):
                    for col_idx, value in enumerate(row):
                        worksheet.write(current_row + 1 + row_idx, col_idx + 1, value, money_fmt)

                current_row += len(df.index) + 2  # Move past data plus add a blank row

            # Set column widths
            worksheet.set_column(0, 0, 30)  # First column wider for labels
            worksheet.set_column(1, len(df.columns), 15)  # Data columns
