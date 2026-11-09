def test_statement_series_html_formats_money(annual_stockrow_income_stmt_cat):
    html = annual_stockrow_income_stmt_cat._repr_html_()
    assert "<table" in html and "$" in html


def test_period_data_html_formats_money(annual_stockrow_income_stmt_cat):
    period = next(iter(annual_stockrow_income_stmt_cat.statements.values()))
    html = period._repr_html_()
    assert "<table" in html and "$" in html
