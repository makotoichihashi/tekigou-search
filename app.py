import os
import re
import unicodedata
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st


# ============================================================
# 基本設定
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "master_database.xlsx"
)

CAR_MASTER_PATH = os.path.join(
    BASE_DIR,
    "car_name_master_final.xlsx"
)

PAGE_SIZE = 50


st.set_page_config(
    page_title="車種別 適合情報検索",
    page_icon="🚗",
    layout="wide"
)


# ============================================================
# 表示調整
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    .stButton > button,
    .stDownloadButton > button {
        min-height: 44px;
        font-weight: 600;
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        min-height: 44px;
    }

    @media (max-width: 768px) {

        .block-container {
            padding-top: 0.7rem;
            padding-left: 0.7rem;
            padding-right: 0.7rem;
        }

        h1 {
            font-size: 1.65rem !important;
        }

        h2 {
            font-size: 1.30rem !important;
        }

        h3 {
            font-size: 1.12rem !important;
        }

        .stButton > button,
        .stDownloadButton > button {
            min-height: 48px;
            width: 100%;
        }
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 文字整理
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except:
        pass

    text = str(value)

    text = unicodedata.normalize(
        "NFKC",
        text
    )

    text = text.replace("\u3000", " ")
    text = text.replace("\xa0", " ")
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def normalize_search(value):

    return clean_text(
        value
    ).upper()


# ============================================================
# 車種比較用
# ============================================================

def normalize_car_key(value):

    text = clean_text(
        value
    )

    if not text:
        return ""

    text = text.lower()

    text = text.replace(" ", "")
    text = text.replace("　", "")

    text = (
        text
        .replace("‐", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("：", ":")
        .replace("／", "/")
    )

    return text


# ============================================================
# 和暦 → 西暦
# ============================================================

def japanese_year_to_ad(
    era,
    year
):

    try:
        year = int(year)
    except:
        return None

    era = clean_text(
        era
    ).upper()

    if era == "R":
        return 2018 + year

    if era == "H":
        return 1988 + year

    if era == "S":
        return 1925 + year

    return None


# ============================================================
# 西暦 → 和暦
# ============================================================

def get_japanese_era_label(year):

    year = int(year)

    if year >= 2019:
        return f"R{year - 2018}"

    if year >= 1989:
        return f"H{year - 1988}"

    if year >= 1926:
        return f"S{year - 1925}"

    return ""


def year_display_label(year):

    era = get_japanese_era_label(
        year
    )

    if era:
        return f"{year}年（{era}）"

    return f"{year}年"


# ============================================================
# 年月数値化
#
# 2022/12 → 202212
# ============================================================

def make_ym(
    year,
    month
):

    try:
        year = int(year)
        month = int(month)
    except:
        return None

    if not 1 <= month <= 12:
        return None

    return year * 100 + month


# ============================================================
# 年式文字列正規化
# ============================================================

def normalize_year_text(value):

    text = clean_text(
        value
    )

    if not text:
        return ""

    text = text.replace("〜", "～")
    text = text.replace("~", "～")
    text = text.replace("－", "～")
    text = text.replace("―", "～")
    text = text.replace("−", "～")

    text = text.replace("令和", "R")
    text = text.replace("平成", "H")
    text = text.replace("昭和", "S")

    return text.strip()


# ============================================================
# 年式原文 → 開始年月・終了年月
#
# 対応例
#
# H28/8～R4/11
# R4/12～現在
# 22年(R4)12月-現在
# 15年(H27)2月-19年(R1)6月
# H22/11～H27/7 S-HYBRIDを含む
# ============================================================

def parse_year_month_range(value):

    text = normalize_year_text(
        value
    )

    if not text:
        return None, None


    # --------------------------------------------------------
    # 区切り記号を統一
    # --------------------------------------------------------

    text = text.replace("-", "～")


    ym_values = []


    # --------------------------------------------------------
    # R4/12
    # H28/8
    # --------------------------------------------------------

    era_slash_matches = re.findall(
        r"([RHS])\s*0*(\d{1,2})\s*/\s*0*(\d{1,2})",
        text,
        flags=re.IGNORECASE
    )


    for era, year, month in era_slash_matches:

        ad_year = japanese_year_to_ad(
            era,
            year
        )

        if ad_year is None:
            continue

        ym = make_ym(
            ad_year,
            month
        )

        if ym is not None:
            ym_values.append(
                ym
            )


    # --------------------------------------------------------
    # 22年(R4)12月
    # 15年(H27)2月
    # --------------------------------------------------------

    if not ym_values:

        era_parenthesis_matches = re.findall(
            r"\(([RHS])\s*0*(\d{1,2})\)\s*0*(\d{1,2})月",
            text,
            flags=re.IGNORECASE
        )


        for era, year, month in era_parenthesis_matches:

            ad_year = japanese_year_to_ad(
                era,
                year
            )

            if ad_year is None:
                continue

            ym = make_ym(
                ad_year,
                month
            )

            if ym is not None:
                ym_values.append(
                    ym
                )


    # --------------------------------------------------------
    # 2022年12月 のような西暦表記
    # --------------------------------------------------------

    if not ym_values:

        western_matches = re.findall(
            r"(19\d{2}|20\d{2})年\s*0*(\d{1,2})月",
            text
        )


        for year, month in western_matches:

            ym = make_ym(
                year,
                month
            )

            if ym is not None:
                ym_values.append(
                    ym
                )


    # --------------------------------------------------------
    # 年月が取れない場合
    # --------------------------------------------------------

    if not ym_values:
        return None, None


    start_ym = ym_values[0]


    if len(ym_values) >= 2:

        end_ym = ym_values[-1]


    elif "現在" in text:

        end_ym = 999912


    elif (
        "～" in text
        and
        text.rstrip().endswith("～")
    ):

        end_ym = 999912


    else:

        end_ym = start_ym


    return (
        start_ym,
        end_ym
    )


# ============================================================
# 年月検索
# ============================================================

def filter_by_year_month(
    target_df,
    selected_year,
    selected_month=None
):

    if selected_year is None:
        return target_df


    if selected_month is not None:

        search_start = make_ym(
            selected_year,
            selected_month
        )

        search_end = search_start


    else:

        search_start = make_ym(
            selected_year,
            1
        )

        search_end = make_ym(
            selected_year,
            12
        )


    def check_row(row):

        year_text = clean_text(
            row.get(
                "年式原文",
                ""
            )
        )


        if not year_text:

            year_text = clean_text(
                row.get(
                    "年式",
                    ""
                )
            )


        start_ym, end_ym = (
            parse_year_month_range(
                year_text
            )
        )


        if (
            start_ym is None
            or
            end_ym is None
        ):
            return False


        return not (
            end_ym < search_start
            or
            start_ym > search_end
        )


    mask = target_df.apply(
        check_row,
        axis=1
    )


    return target_df[
        mask
    ]


# ============================================================
# Excel読込
# ============================================================

@st.cache_data
def load_main_database(
    path,
    file_mtime
):

    try:

        df = pd.read_excel(
            path,
            sheet_name="master"
        )

    except:

        df = pd.read_excel(
            path
        )

    return df.fillna("")


@st.cache_data
def load_car_master(
    path,
    file_mtime
):

    df = pd.read_excel(
        path,
        sheet_name="車種名統合"
    )

    return df.fillna("")


# ============================================================
# ファイル確認
# ============================================================

if not os.path.exists(
    DB_PATH
):

    st.error(
        "master_database.xlsx が見つかりません。"
    )

    st.stop()


if not os.path.exists(
    CAR_MASTER_PATH
):

    st.error(
        "car_name_master_final.xlsx が見つかりません。"
    )

    st.stop()


# ============================================================
# DB読込
# ============================================================

df = load_main_database(
    DB_PATH,
    os.path.getmtime(
        DB_PATH
    )
)


car_master_df = load_car_master(
    CAR_MASTER_PATH,
    os.path.getmtime(
        CAR_MASTER_PATH
    )
)


# ============================================================
# 車種統合辞書
# ============================================================

CAR_NAME_LOOKUP = {}


for _, row in car_master_df.iterrows():

    enabled = clean_text(
        row.get(
            "有効",
            "YES"
        )
    ).upper()


    if enabled not in [
        "",
        "YES",
        "Y",
        "TRUE",
        "1"
    ]:
        continue


    maker = clean_text(
        row.get(
            "メーカー",
            ""
        )
    )

    original_name = clean_text(
        row.get(
            "元車種名",
            ""
        )
    )

    merged_name = clean_text(
        row.get(
            "統合車種名",
            ""
        )
    )


    if (
        not maker
        or
        not original_name
        or
        not merged_name
    ):
        continue


    CAR_NAME_LOOKUP[
        (
            normalize_search(
                maker
            ),
            normalize_car_key(
                original_name
            )
        )
    ] = merged_name


# ============================================================
# 統合車種名
# ============================================================

def get_merged_car_name(
    maker,
    car_name
):

    maker = clean_text(
        maker
    )

    car_name = clean_text(
        car_name
    )


    if not car_name:
        return ""


    key = (
        normalize_search(
            maker
        ),
        normalize_car_key(
            car_name
        )
    )


    return CAR_NAME_LOOKUP.get(
        key,
        car_name
    )


# ============================================================
# 部分一致
# ============================================================

def contains_value(
    series,
    keyword
):

    keyword = normalize_search(
        keyword
    )


    if not keyword:

        return pd.Series(
            True,
            index=series.index
        )


    normalized = (
        series
        .fillna("")
        .astype(str)
        .map(
            normalize_search
        )
    )


    return normalized.str.contains(
        re.escape(
            keyword
        ),
        na=False
    )


# ============================================================
# Pioneer最終判定
# ============================================================

def get_final_fitment(row):

    maker = clean_text(
        row.get(
            "商品メーカー",
            ""
        )
    )

    raw_fitment = clean_text(
        row.get(
            "適合状態",
            ""
        )
    )

    data_type = clean_text(
        row.get(
            "データ種別",
            ""
        )
    )


    if maker == "Pioneer":

        data_type_lower = (
            data_type.lower()
        )


        if data_type_lower in [
            "gtable",
            "select"
        ]:

            if raw_fitment in [
                "適合",
                "不適合",
                "要確認"
            ]:
                return raw_fitment

            return "要確認"


        if data_type.upper() == "PDF":
            return "要確認"


        if data_type_lower == "business補完":
            return "要確認"


        return "要確認"


    if raw_fitment:
        return raw_fitment


    return "要確認"


# ============================================================
# セッション
# ============================================================

if "searched" not in st.session_state:
    st.session_state.searched = False

if "page" not in st.session_state:
    st.session_state.page = 1


# ============================================================
# リセット
# ============================================================

def reset_conditions():

    keys = [
        "vehicle_maker",
        "car_name",
        "year_select",
        "month_select",
        "model_keyword",
        "product_maker",
        "category",
        "product_code",
        "product_name",
        "current_only",
        "fit_only",
        "page",
        "searched",
    ]


    for key in keys:

        if key in st.session_state:
            del st.session_state[
                key
            ]


    st.session_state.searched = False
    st.session_state.page = 1


# ============================================================
# ヘッダー
# ============================================================

st.title(
    "🚗 車種別 適合情報検索"
)


st.caption(
    f"登録データ：{len(df):,}件"
    f" ｜ 車種統合ルール：{len(CAR_NAME_LOOKUP):,}件"
)


st.write(
    "車両を選択したあと、商品条件を指定して検索してください。"
)


# ============================================================
# ① 車両選択
# ============================================================

st.subheader(
    "① 車両を選択"
)


row_vehicle_1, row_vehicle_2 = st.columns(
    2
)


# ============================================================
# メーカー
# ============================================================

makers = sorted(
    [
        clean_text(x)
        for x in
        df[
            "メーカー"
        ].unique()
        if clean_text(x)
    ]
)


with row_vehicle_1:

    selected_maker = st.selectbox(
        "車両メーカー",
        [
            "指定なし"
        ]
        +
        makers,
        key="vehicle_maker"
    )


# ============================================================
# メーカー絞込
# ============================================================

car_source_df = df.copy()


if selected_maker != "指定なし":

    car_source_df = car_source_df[
        car_source_df[
            "メーカー"
        ].map(
            clean_text
        )
        ==
        selected_maker
    ]


# ============================================================
# 統合車種一覧
# ============================================================

merged_car_names = []


for _, row in (
    car_source_df[
        [
            "メーカー",
            "車種"
        ]
    ]
    .drop_duplicates()
    .iterrows()
):

    merged_name = get_merged_car_name(
        row[
            "メーカー"
        ],
        row[
            "車種"
        ]
    )


    if merged_name:

        merged_car_names.append(
            merged_name
        )


cars = sorted(
    list(
        dict.fromkeys(
            merged_car_names
        )
    )
)


with row_vehicle_2:

    selected_car = st.selectbox(
        "車種",
        [
            "指定なし"
        ]
        +
        cars,
        key="car_name"
    )


# ============================================================
# 年月選択
# ============================================================

st.write(
    "#### 年式"
)


year_col, month_col = st.columns(
    2
)


# ============================================================
# 現在年
# ============================================================

current_year = datetime.now().year


year_options = [
    "指定なし"
]


year_lookup = {}


for year in range(
    current_year,
    1979,
    -1
):

    label = year_display_label(
        year
    )

    year_options.append(
        label
    )

    year_lookup[
        label
    ] = year


with year_col:

    selected_year_label = st.selectbox(
        "年",
        year_options,
        key="year_select"
    )


with month_col:

    selected_month_label = st.selectbox(
        "月",
        [
            "指定なし",
            "1月",
            "2月",
            "3月",
            "4月",
            "5月",
            "6月",
            "7月",
            "8月",
            "9月",
            "10月",
            "11月",
            "12月",
        ],
        key="month_select"
    )


selected_year = (
    year_lookup.get(
        selected_year_label
    )
)


selected_month = None


if selected_month_label != "指定なし":

    selected_month = int(
        selected_month_label.replace(
            "月",
            ""
        )
    )


# ============================================================
# ② 商品条件
# ============================================================

st.subheader(
    "② 商品条件"
)


product_row1_col1, product_row1_col2, product_row1_col3 = (
    st.columns(
        3
    )
)


with product_row1_col1:

    model_keyword = st.text_input(
        "型式",
        placeholder="例：ZN8 / TRH200V",
        key="model_keyword"
    )


product_makers = sorted(
    [
        clean_text(x)
        for x in
        df[
            "商品メーカー"
        ].unique()
        if clean_text(x)
    ]
)


with product_row1_col2:

    selected_product_maker = st.selectbox(
        "商品メーカー",
        [
            "指定なし"
        ]
        +
        product_makers,
        key="product_maker"
    )


# ============================================================
# カテゴリ候補
# ============================================================

category_source_df = df.copy()


if selected_product_maker != "指定なし":

    category_source_df = category_source_df[
        category_source_df[
            "商品メーカー"
        ].map(
            clean_text
        )
        ==
        selected_product_maker
    ]


categories = sorted(
    [
        clean_text(x)
        for x in
        category_source_df[
            "カテゴリ"
        ].unique()
        if clean_text(x)
    ]
)


with product_row1_col3:

    selected_category = st.selectbox(
        "カテゴリ",
        [
            "指定なし"
        ]
        +
        categories,
        key="category"
    )


product_row2_col1, product_row2_col2 = (
    st.columns(
        2
    )
)


with product_row2_col1:

    product_code = st.text_input(
        "商品型番",
        placeholder="例：AVIC-RW822-D",
        key="product_code"
    )


with product_row2_col2:

    product_name = st.text_input(
        "商品名",
        placeholder="商品名の一部でも検索できます",
        key="product_name"
    )


# ============================================================
# 絞り込み
# ============================================================

st.write(
    "#### 絞り込み"
)


filter_col1, filter_col2 = st.columns(
    2
)


with filter_col1:

    current_only = st.checkbox(
        "現行商品のみ表示",
        value=False,
        key="current_only"
    )


with filter_col2:

    fit_only = st.checkbox(
        "適合商品のみ表示",
        value=False,
        key="fit_only"
    )


# ============================================================
# 検索
# ============================================================

if st.button(
    "🔍 検索する",
    type="primary",
    width="stretch"
):

    st.session_state.searched = True

    st.session_state.page = 1


if not st.session_state.searched:

    st.info(
        "条件を指定して「検索する」を押してください。"
    )

    st.stop()


# ============================================================
# 検索処理
# ============================================================

search_df = df.copy()


# ------------------------------------------------------------
# メーカー
# ------------------------------------------------------------

if selected_maker != "指定なし":

    search_df = search_df[
        search_df[
            "メーカー"
        ].map(
            clean_text
        )
        ==
        selected_maker
    ]


# ------------------------------------------------------------
# 統合車種
# ------------------------------------------------------------

if selected_car != "指定なし":

    car_mask = search_df.apply(
        lambda row:
        get_merged_car_name(
            row.get(
                "メーカー",
                ""
            ),
            row.get(
                "車種",
                ""
            )
        )
        ==
        selected_car,
        axis=1
    )


    search_df = search_df[
        car_mask
    ]


# ------------------------------------------------------------
# 年月
# ------------------------------------------------------------

if selected_year is not None:

    search_df = filter_by_year_month(
        search_df,
        selected_year,
        selected_month
    )


# ------------------------------------------------------------
# 型式
# ------------------------------------------------------------

if model_keyword:

    model_mask = pd.Series(
        False,
        index=search_df.index
    )


    if "実型式" in search_df.columns:

        model_mask = (
            model_mask
            |
            contains_value(
                search_df[
                    "実型式"
                ],
                model_keyword
            )
        )


    if "型式" in search_df.columns:

        model_mask = (
            model_mask
            |
            contains_value(
                search_df[
                    "型式"
                ],
                model_keyword
            )
        )


    search_df = search_df[
        model_mask
    ]


# ------------------------------------------------------------
# 商品メーカー
# ------------------------------------------------------------

if selected_product_maker != "指定なし":

    search_df = search_df[
        search_df[
            "商品メーカー"
        ].map(
            clean_text
        )
        ==
        selected_product_maker
    ]


# ------------------------------------------------------------
# カテゴリ
# ------------------------------------------------------------

if selected_category != "指定なし":

    search_df = search_df[
        search_df[
            "カテゴリ"
        ].map(
            clean_text
        )
        ==
        selected_category
    ]


# ------------------------------------------------------------
# 商品型番
# ------------------------------------------------------------

if product_code:

    search_df = search_df[
        contains_value(
            search_df[
                "商品型番"
            ],
            product_code
        )
    ]


# ------------------------------------------------------------
# 商品名
# ------------------------------------------------------------

if product_name:

    search_df = search_df[
        contains_value(
            search_df[
                "商品名"
            ],
            product_name
        )
    ]


# ------------------------------------------------------------
# 現行
# ------------------------------------------------------------

if current_only:

    if "生産状態" in search_df.columns:

        search_df = search_df[
            search_df[
                "生産状態"
            ].map(
                clean_text
            )
            ==
            "現行"
        ]


# ------------------------------------------------------------
# 適合のみ
# ------------------------------------------------------------

if fit_only:

    fit_mask = search_df.apply(
        lambda row:
        get_final_fitment(
            row
        )
        ==
        "適合",
        axis=1
    )


    search_df = search_df[
        fit_mask
    ]


search_df = search_df.reset_index(
    drop=True
)


# ============================================================
# 再検索
# ============================================================

st.divider()


retry_col1, retry_col2 = st.columns(
    2
)


with retry_col1:

    if st.button(
        "✏️ 条件を修正して再検索",
        width="stretch"
    ):

        st.session_state.searched = False
        st.rerun()


with retry_col2:

    if st.button(
        "🔄 検索条件をすべてリセット",
        width="stretch"
    ):

        reset_conditions()
        st.rerun()


# ============================================================
# 結果
# ============================================================

st.subheader(
    "③ 検索結果"
)


summary_df = search_df.copy()


if not summary_df.empty:

    summary_df[
        "最終適合状態"
    ] = summary_df.apply(
        get_final_fitment,
        axis=1
    )


    fit_count = int(
        (
            summary_df[
                "最終適合状態"
            ]
            ==
            "適合"
        ).sum()
    )


    check_count = int(
        (
            summary_df[
                "最終適合状態"
            ]
            ==
            "要確認"
        ).sum()
    )


    ng_count = int(
        (
            summary_df[
                "最終適合状態"
            ]
            ==
            "不適合"
        ).sum()
    )


else:

    fit_count = 0
    check_count = 0
    ng_count = 0


metric1, metric2, metric3, metric4 = st.columns(
    4
)


with metric1:

    st.metric(
        "該当件数",
        len(
            search_df
        )
    )


with metric2:

    st.metric(
        "✅ 適合",
        fit_count
    )


with metric3:

    st.metric(
        "⚠️ 要確認",
        check_count
    )


with metric4:

    st.metric(
        "❌ 不適合",
        ng_count
    )


if search_df.empty:

    st.warning(
        "該当する適合情報はありません。"
    )

    st.stop()


# ============================================================
# 検索条件
# ============================================================

with st.expander(
    "今回の検索条件"
):

    st.write(
        "**車両メーカー：**",
        selected_maker
    )

    st.write(
        "**車種：**",
        selected_car
    )


    if selected_year is not None:

        st.write(
            "**年：**",
            year_display_label(
                selected_year
            )
        )


    if selected_month is not None:

        st.write(
            "**月：**",
            f"{selected_month}月"
        )


# ============================================================
# Excelダウンロード
# ============================================================

download_df = search_df.copy()


download_df[
    "最終適合状態"
] = download_df.apply(
    get_final_fitment,
    axis=1
)


download_df[
    "統合車種名"
] = download_df.apply(
    lambda row:
    get_merged_car_name(
        row.get(
            "メーカー",
            ""
        ),
        row.get(
            "車種",
            ""
        )
    ),
    axis=1
)


buffer = BytesIO()


with pd.ExcelWriter(
    buffer,
    engine="openpyxl"
) as writer:

    download_df.to_excel(
        writer,
        sheet_name="検索結果",
        index=False
    )


st.download_button(
    "📥 検索結果をExcelでダウンロード",
    data=buffer.getvalue(),
    file_name="search_result.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
    width="stretch"
)


# ============================================================
# ページング
# ============================================================

total_pages = max(
    1,
    (
        len(search_df)
        +
        PAGE_SIZE
        -
        1
    )
    //
    PAGE_SIZE
)


if total_pages > 1:

    page = st.number_input(
        "ページ",
        min_value=1,
        max_value=total_pages,
        value=min(
            st.session_state.page,
            total_pages
        ),
        step=1
    )

else:

    page = 1


st.session_state.page = int(
    page
)


start_index = (
    int(page) - 1
) * PAGE_SIZE


end_index = (
    start_index
    +
    PAGE_SIZE
)


page_df = search_df.iloc[
    start_index:end_index
]


st.write(
    f"### 適合情報 "
    f"{start_index + 1}～"
    f"{min(end_index, len(search_df))}件目"
)


# ============================================================
# 詳細
# ============================================================

for _, row in page_df.iterrows():

    code = clean_text(
        row.get(
            "商品型番",
            ""
        )
    )

    name = clean_text(
        row.get(
            "商品名",
            ""
        )
    )

    maker = clean_text(
        row.get(
            "商品メーカー",
            ""
        )
    )

    category = clean_text(
        row.get(
            "カテゴリ",
            ""
        )
    )

    fitment = get_final_fitment(
        row
    )


    title = (
        f"{maker} | "
        f"{category} | "
        f"{code or name} | "
        f"{fitment}"
    )


    with st.expander(
        title
    ):

        left, right = st.columns(
            2
        )


        with left:

            vehicle_maker = clean_text(
                row.get(
                    "メーカー",
                    ""
                )
            )

            original_car_name = clean_text(
                row.get(
                    "車種",
                    ""
                )
            )

            merged_car_name = get_merged_car_name(
                vehicle_maker,
                original_car_name
            )


            st.write(
                "**車両メーカー：**",
                vehicle_maker
            )


            st.write(
                "**車種：**",
                original_car_name
            )


            if merged_car_name != original_car_name:

                st.caption(
                    f"統合検索車種：{merged_car_name}"
                )


            year_text = clean_text(
                row.get(
                    "年式原文",
                    ""
                )
            )


            if not year_text:

                year_text = clean_text(
                    row.get(
                        "年式",
                        ""
                    )
                )


            if year_text:

                st.write(
                    "**年式：**",
                    year_text
                )


            model = clean_text(
                row.get(
                    "実型式",
                    ""
                )
            )


            if not model:

                model = clean_text(
                    row.get(
                        "型式",
                        ""
                    )
                )


            if model:

                st.write(
                    "**型式：**",
                    model
                )


        with right:

            st.write(
                "**商品メーカー：**",
                maker
            )


            st.write(
                "**カテゴリ：**",
                category
            )


            if name:

                st.write(
                    "**商品名：**",
                    name
                )


            if code:

                st.write(
                    "**商品型番：**",
                    code
                )


            production = clean_text(
                row.get(
                    "生産状態",
                    ""
                )
            )


            if production:

                st.write(
                    "**生産状態：**",
                    production
                )


        # ----------------------------------------------------
        # 適合
        # ----------------------------------------------------

        if fitment == "適合":

            st.success(
                "✅ 適合"
            )

        elif fitment == "不適合":

            st.error(
                "❌ 不適合"
            )

        else:

            st.warning(
                "⚠️ 要確認"
            )


        # ----------------------------------------------------
        # Pioneer根拠
        # ----------------------------------------------------

        data_type = clean_text(
            row.get(
                "データ種別",
                ""
            )
        )


        if maker == "Pioneer":

            if data_type.lower() == "select":

                st.info(
                    "Pioneer公式「車種別カーナビセレクト」に基づく判定です。"
                )


            elif data_type.lower() == "gtable":

                st.info(
                    "Pioneer公式の商品別適合情報（gtable）に基づく判定です。"
                )


            elif data_type.upper() == "PDF":

                st.warning(
                    "Pioneer公式取付資料への掲載情報です。"
                    "商品型番単位の直接適合が確認できないため"
                    "「要確認」としています。"
                )


            elif data_type.lower() == "business補完":

                source_model = clean_text(
                    row.get(
                        "補完元商品型番",
                        ""
                    )
                )


                if source_model:

                    st.info(
                        f"{source_model} のPioneer公式適合情報を"
                        "参照した業務用モデル候補です。"
                    )


        # ----------------------------------------------------
        # 取付キット
        # ----------------------------------------------------

        kit = clean_text(
            row.get(
                "取付キット",
                ""
            )
        )


        if kit:

            st.write(
                "**取付キット：**",
                kit
            )


        related = clean_text(
            row.get(
                "関連品番",
                ""
            )
        )


        if related:

            st.write(
                "**関連品番：**",
                related
            )


        # ----------------------------------------------------
        # 注意事項
        # ----------------------------------------------------

        reason = clean_text(
            row.get(
                "適合条件・理由",
                ""
            )
        )

        notes = clean_text(
            row.get(
                "注意事項",
                ""
            )
        )


        if reason or notes:

            st.write(
                "#### ⚠️ 適合条件・注意事項"
            )


            if reason:

                st.warning(
                    reason
                )


            if (
                notes
                and
                notes != reason
            ):

                st.error(
                    notes
                )


        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------

        product_url = clean_text(
            row.get(
                "商品URL",
                ""
            )
        )


        source_url = clean_text(
            row.get(
                "商品適合URL",
                ""
            )
        )


        if not source_url:

            source_url = clean_text(
                row.get(
                    "適合概要URL",
                    ""
                )
            )


        if not source_url:

            source_url = clean_text(
                row.get(
                    "元URL",
                    ""
                )
            )


        pdf_url = clean_text(
            row.get(
                "PDF・資料URL",
                ""
            )
        )


        links = st.columns(
            3
        )


        if product_url:

            with links[0]:

                st.link_button(
                    "商品ページ",
                    product_url,
                    width="stretch"
                )


        if source_url:

            with links[1]:

                st.link_button(
                    "適合情報ページ",
                    source_url,
                    width="stretch"
                )


        if pdf_url:

            with links[2]:

                st.link_button(
                    "PDF・資料",
                    pdf_url,
                    width="stretch"
                )
