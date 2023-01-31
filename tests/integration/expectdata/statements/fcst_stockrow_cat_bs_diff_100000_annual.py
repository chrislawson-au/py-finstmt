import pandas as pd

FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX_str = [
    "2019-12-31 00:00:00",
    "2020-12-31 00:00:00",
]
FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX = [
    pd.to_datetime(val) for val in FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX_str
]
FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX_DATA_DICT = dict(
    revenue=pd.Series(
        [57667220437.771454, 60770957074.275894],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Revenue",
    ),
    cogs=pd.Series(
        [40454639058.16816, 42291653260.50249],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Cost of Goods Sold",
    ),
    gross_profit=pd.Series(
        [17212581379.603294, 18479303813.773407],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Gross Profit",
    ),
    rd_exp=pd.Series(
        [2130504180.795485, 1973832561.7877598],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="R&D Expense",
    ),
    sga=pd.Series(
        [5705772840.60267, 5943016376.151709],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="SG&A Expense",
    ),
    dep_exp=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Depreciation & Amortization Expense",
    ),
    other_op_exp=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Other Operating Expenses",
    ),
    op_exp=pd.Series(
        [7836277021.398155, 7916848937.939468],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Operating Expense",
    ),
    ebit=pd.Series(
        [9376304358.20514, 10562454875.833939],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Earnings Before Interest and Taxes",
    ),
    int_exp=pd.Series(
        [531281196.22238696, 555071035.0977135],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Interest Expense",
    ),
    gain_on_sale_invest=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Gain on Sale of Investments",
    ),
    gain_on_sale_asset=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Gain on Sale of Assets",
    ),
    impairment=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Impairment Expense",
    ),
    ebt=pd.Series(
        [8845023161.982752, 10007383840.736225],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Earnings Before Tax",
    ),
    tax_exp=pd.Series(
        [3283577897.2585177, 3715086301.872095],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Income Tax Expense",
    ),
    net_income=pd.Series(
        [5561445264.724234, 6292297538.86413],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Net Income",
    ),
    cash=pd.Series(
        [9368129050.394783, 10012396894.55082],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Cash and Cash Equivalents",
    ),
    st_invest=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Short-Term Investments",
    ),
    cash_and_st_invest=pd.Series(
        [9368129050.394783, 10012396894.55082],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Cash and Short-Term Investments",
    ),
    receivables=pd.Series(
        [36913288131.6947, 38900016881.20703],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Receivables",
    ),
    inventory=pd.Series(
        [12560519689.098722, 13203297991.089027],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Inventory",
    ),
    def_tax_st=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Deferred Tax Assets, Current",
    ),
    other_current_assets=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Other Current Assets",
    ),
    total_current_assets=pd.Series(
        [58841936871.18821, 62115711766.84688],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Total Current Assets",
    ),
    gross_ppe=pd.Series(
        [13698894523.433386, 0.0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Gross Property, Plant & Equipment",
    ),
    dep=pd.Series(
        [0.0, 13824938202.751822],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Accumulated Depreciation",
    ),
    net_ppe=pd.Series(
        [13698894523.433386, 13824938202.751822],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Net Property, Plant & Equipment",
    ),
    goodwill=pd.Series(
        [8311100000.0, 8311100000.0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Goodwill and Intangible Assets",
    ),
    lt_invest=pd.Series(
        [0.0, 0.0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Long-Term Investments",
    ),
    def_tax_lt=pd.Series(
        [1301450391.2211661, 1177048728.846231],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Deferred Tax Assets, Long-Term",
    ),
    other_lt_assets=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Other Long-Term Assets",
    ),
    total_non_current_assets=pd.Series(
        [23311444914.654552, 23313086931.598053],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Total Non-Current Assets",
    ),
    total_assets=pd.Series(
        [82153381785.84277, 85428798698.44493],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Total Assets",
    ),
    payables=pd.Series(
        [7504926219.835061, 8018535007.403371],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Payables",
    ),
    st_debt=pd.Series(
        [13416180694.846247, 14047202455.660326],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Short-Term Debt",
    ),
    current_lt_debt=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Current Portion of Long-Term Debt",
    ),
    tax_liab_st=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Tax Liabilities, Short-Term",
    ),
    other_current_liab=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Other Current Liabilities",
    ),
    total_current_liab=pd.Series(
        [20921106914.68131, 22065737463.063698],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Total Current Liabilities",
    ),
    lt_debt=pd.Series(
        [28940344972.139137, 30205974039.73957],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Long-Term Debt",
    ),
    total_debt=pd.Series(
        [42356525666.98538, 44253176495.399895],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Total Debt",
    ),
    deferred_rev=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Deferred Revenue",
    ),
    tax_liab_lt=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Tax Liabilities, Long-Term",
    ),
    deposit_liab=pd.Series(
        [1721200000.0, 1721200000.0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Deposit Liabilities",
    ),
    other_lt_liab=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Other Long-Term Liabilities",
    ),
    total_non_current_liab=pd.Series(
        [30661544972.139137, 31927174039.73957],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Total Non-Current Liabilities",
    ),
    total_liab=pd.Series(
        [51582651886.82044, 53992911502.80327],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Total Liabilities",
    ),
    common_stock=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Common Stock",
    ),
    other_income=pd.Series(
        [-1684000000.0, -1684000000.0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Other Comprehensive Income",
    ),
    retained_earnings=pd.Series(
        [32254733333.333344, 33119884848.484863],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Retained Earnings",
    ),
    minority_interest=pd.Series(
        [0, 0],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Minority Interest",
    ),
    total_equity=pd.Series(
        [30570733333.333344, 31435884848.484863],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Total Stockholder's Equity",
    ),
    total_liab_and_equity=pd.Series(
        [82153385220.15378, 85428796351.28813],
        index=FCST_STOCKROW_CAT_BS_DIFF_100000_A_INDEX,
        name="Total Liabilities and Equity",
    ),
)
