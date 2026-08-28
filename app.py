import os
import re
import unicodedata
from io import BytesIO
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# 基本設定
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
# CSS
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.2rem;
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
    except Exception:
        pass

    text = str(value)

    text = unicodedata.normalize(
        "NFKC",
        text
    )

    text = text.replace(
        "\u3000",
        " "
    )

    text = text.replace(
        "\xa0",
        " "
    )

    text = text.replace(
        "\r",
        " "
    )

    text = text.replace(
        "\n",
        " "
    )

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


def normalize_car_key(value):

    text = clean_text(
        value
    )

    if not text:
        return ""

    text = text.lower()

    text = text.replace(
        " ",
        ""
    )

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


def clean_series(series):

    return (
        series
        .fillna("")
        .astype(str)
        .map(clean_text)
    )


def normalize_search_series(series):

    return (
        clean_series(series)
        .str.upper()
    )


# ============================================================
# 和暦関連
# ============================================================

def japanese_year_to_ad(
    era,
    year
):

    try:
        year = int(year)
    except Exception:
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


def make_ym(
    year,
    month
):

    try:
        year = int(year)
        month = int(month)
    except Exception:
        return None

    if not 1 <= month <= 12:
        return None

    return (
        year * 100
        +
        month
    )


# ============================================================
# 年式解析
#
# 一度だけキャッシュ時に解析する
# 検索時には apply(axis=1) を使わない
# ============================================================

def parse_year_month_range(value):

    text = clean_text(
        value
    )

    if not text:
        return (
            np.nan,
            np.nan
        )

    text = unicodedata.normalize(
        "NFKC",
        text
    )

    text = (
        text
        .replace("〜", "～")
        .replace("~", "～")
        .replace("－", "～")
        .replace("―", "～")
        .replace("−", "～")
        .replace("令和", "R")
        .replace("平成", "H")
        .replace("昭和", "S")
    )

    text = re.sub(
        r"(?<=月)-(?=\d|現在)",
        "～",
        text
    )

    ym_values = []

    # --------------------------------------------------------
    # ① R4/12
    # --------------------------------------------------------

    for era, year, month in re.findall(
        r"([RHS])\s*0*(\d{1,2})\s*/\s*0*(\d{1,2})",
        text,
        flags=re.IGNORECASE
    ):

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
    # ② 22年(R4)12月
    # --------------------------------------------------------

    if not ym_values:

        for era, year, month in re.findall(
            r"\(([RHS])\s*0*(\d{1,2})\)\s*0*(\d{1,2})月",
            text,
            flags=re.IGNORECASE
        ):

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
    # ③ 2022年12月
    # --------------------------------------------------------

    if not ym_values:

        for year, month in re.findall(
            r"(19\d{2}|20\d{2})年\s*0*(\d{1,2})月",
            text
        ):

            ym = make_ym(
                year,
                month
            )

            if ym is not None:
                ym_values.append(
                    ym
                )

    # --------------------------------------------------------
    # ④ 2022/12
    # --------------------------------------------------------

    if not ym_values:

        for year, month in re.findall(
            r"(19\d{2}|20\d{2})\s*/\s*0*(\d{1,2})",
            text
        ):

            ym = make_ym(
                year,
                month
            )

            if ym is not None:
                ym_values.append(
                    ym
                )

    # --------------------------------------------------------
    # ⑤ 年だけ R4 / H28
    # --------------------------------------------------------

    if not ym_values:

        era_match = re.search(
            r"([RHS])\s*0*(\d{1,2})",
            text,
            flags=re.IGNORECASE
        )

        if era_match:

            ad_year = japanese_year_to_ad(
                era_match.group(1),
                era_match.group(2)
            )

            if ad_year is not None:

                ym_values.append(
                    make_ym(
                        ad_year,
                        1
                    )
                )

                if "現在" not in text:
                    ym_values.append(
                        make_ym(
                            ad_year,
                            12
                        )
                    )

    # --------------------------------------------------------
    # ⑥ 西暦だけ
    # --------------------------------------------------------

    if not ym_values:

        western_match = re.search(
            r"(19\d{2}|20\d{2})",
            text
        )

        if western_match:

            ad_year = int(
                western_match.group(1)
            )

            ym_values.append(
                make_ym(
                    ad_year,
                    1
                )
            )

            if "現在" not in text:
                ym_values.append(
                    make_ym(
                        ad_year,
                        12
                    )
                )

    if not ym_values:

        return (
            np.nan,
            np.nan
        )

    start_ym = ym_values[0]

    if len(
        ym_values
    ) >= 2:

        end_ym = ym_values[-1]

    elif "現在" in text:

        end_ym = 999912

    elif (
        "～" in text
        and
        text.rstrip().endswith(
            "～"
        )
    ):

        end_ym = 999912

    else:

        end_ym = start_ym

    return (
        start_ym,
        end_ym
    )


# ============================================================
# 車種マスター読込
# ============================================================

@st.cache_data(
    show_spinner="車種統合マスターを読み込んでいます..."
)
def load_car_master(
    path,
    file_mtime
):

    try:

        df = pd.read_excel(
            path,
            sheet_name="車種名統合"
        )

    except Exception:

        df = pd.read_excel(
            path
        )

    return df.fillna("")


# ============================================================
# 車種統合辞書作成
# ============================================================

def build_car_lookup(
    car_master_df
):

    lookup = {}

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

        key = (
            normalize_search(
                maker
            )
            +
            "||"
            +
            normalize_car_key(
                original_name
            )
        )

        lookup[
            key
        ] = merged_name

    return lookup


# ============================================================
# DB読込＋高速検索用列の事前生成
# ============================================================

@st.cache_data(
    show_spinner="適合データベースを準備しています..."
)
def load_and_prepare_database(
    db_path,
    db_mtime,
    car_master_path,
    car_master_mtime
):

    # --------------------------------------------------------
    # DB
    # --------------------------------------------------------

    try:

        df = pd.read_excel(
            db_path,
            sheet_name="master"
        )

    except Exception:

        df = pd.read_excel(
            db_path
        )

    df = df.fillna("")

    # --------------------------------------------------------
    # 車種マスター
    # --------------------------------------------------------

    car_master_df = load_car_master(
        car_master_path,
        car_master_mtime
    )

    lookup = build_car_lookup(
        car_master_df
    )

    # --------------------------------------------------------
    # 必要列の不足を空列で補う
    # --------------------------------------------------------

    optional_columns = [
        "年式原文",
        "年式",
        "開始年",
        "終了年",
        "実型式",
        "型式",
        "適合状態",
        "データ種別",
        "生産状態",
        "取付キット",
        "関連品番",
        "適合条件・理由",
        "注意事項",
        "商品URL",
        "商品適合URL",
        "適合概要URL",
        "元URL",
        "PDF・資料URL",
        "補完元商品型番",
    ]

    for col in optional_columns:

        if col not in df.columns:
            df[col] = ""

    # --------------------------------------------------------
    # 正規化列
    # --------------------------------------------------------

    df["_メーカー"] = clean_series(
        df["メーカー"]
    )

    df["_商品メーカー"] = clean_series(
        df["商品メーカー"]
    )

    df["_カテゴリ"] = clean_series(
        df["カテゴリ"]
    )

    df["_商品型番検索"] = normalize_search_series(
        df["商品型番"]
    )

    df["_商品名検索"] = normalize_search_series(
        df["商品名"]
    )

    df["_実型式検索"] = normalize_search_series(
        df["実型式"]
    )

    df["_型式検索"] = normalize_search_series(
        df["型式"]
    )

    df["_生産状態"] = clean_series(
        df["生産状態"]
    )

    df["_適合状態"] = clean_series(
        df["適合状態"]
    )

    df["_データ種別"] = (
        clean_series(
            df["データ種別"]
        )
        .str.lower()
    )

    # --------------------------------------------------------
    # 統合車種名
    # --------------------------------------------------------

    maker_key = normalize_search_series(
        df["メーカー"]
    )

    car_key = (
        clean_series(
            df["車種"]
        )
        .map(
            normalize_car_key
        )
    )

    composite_key = (
        maker_key
        +
        "||"
        +
        car_key
    )

    mapped = composite_key.map(
        lookup
    )

    original_car = clean_series(
        df["車種"]
    )

    df["_統合車種名"] = (
        mapped
        .fillna(
            original_car
        )
    )

    # --------------------------------------------------------
    # Pioneerを含む最終適合状態
    #
    # gtable/select/rear_monitor:
    #   元の適合状態を尊重
    #
    # PDF:
    #   要確認
    #
    # business補完:
    #   要確認
    # --------------------------------------------------------

    raw_fitment = df[
        "_適合状態"
    ]

    final_fitment = raw_fitment.where(
        raw_fitment.isin(
            [
                "適合",
                "不適合",
                "要確認"
            ]
        ),
        "要確認"
    )

    pioneer_mask = (
        df[
            "_商品メーカー"
        ]
        ==
        "Pioneer"
    )

    trusted_pioneer_mask = (
        pioneer_mask
        &
        df[
            "_データ種別"
        ].isin(
            [
                "gtable",
                "select",
                "rear_monitor",
            ]
        )
    )

    pioneer_force_check_mask = (
        pioneer_mask
        &
        ~trusted_pioneer_mask
    )

    final_fitment.loc[
        pioneer_force_check_mask
    ] = "要確認"

    df[
        "_最終適合状態"
    ] = final_fitment

    # --------------------------------------------------------
    # 年式原文
    # --------------------------------------------------------

    year_source = clean_series(
        df["年式原文"]
    )

    empty_year_mask = (
        year_source
        ==
        ""
    )

    year_source.loc[
        empty_year_mask
    ] = clean_series(
        df.loc[
            empty_year_mask,
            "年式"
        ]
    )

    df[
        "_年式検索元"
    ] = year_source

    # --------------------------------------------------------
    # 年式を一度だけ解析
    # --------------------------------------------------------

    parsed = year_source.map(
        parse_year_month_range
    )

    df[
        "_開始年月"
    ] = parsed.map(
        lambda x: x[0]
    )

    df[
        "_終了年月"
    ] = parsed.map(
        lambda x: x[1]
    )

    # --------------------------------------------------------
    # 開始年・終了年列から補完
    # --------------------------------------------------------

    start_year_num = pd.to_numeric(
        df["開始年"],
        errors="coerce"
    )

    end_year_num = pd.to_numeric(
        df["終了年"],
        errors="coerce"
    )

    missing_start = df[
        "_開始年月"
    ].isna()

    valid_start_year = (
        start_year_num
        .between(
            1900,
            2200
        )
    )

    start_fill_mask = (
        missing_start
        &
        valid_start_year
    )

    df.loc[
        start_fill_mask,
        "_開始年月"
    ] = (
        start_year_num.loc[
            start_fill_mask
        ]
        *
        100
        +
        1
    )

    missing_end = df[
        "_終了年月"
    ].isna()

    valid_end_year = (
        end_year_num
        .between(
            1900,
            2200
        )
    )

    end_fill_mask = (
        missing_end
        &
        valid_end_year
    )

    df.loc[
        end_fill_mask,
        "_終了年月"
    ] = (
        end_year_num.loc[
            end_fill_mask
        ]
        *
        100
        +
        12
    )

    # 開始年だけある場合は現在までとして扱う
    current_fill_mask = (
        df[
            "_開始年月"
        ].notna()
        &
        df[
            "_終了年月"
        ].isna()
    )

    df.loc[
        current_fill_mask,
        "_終了年月"
    ] = 999912

    return (
        df,
        car_master_df,
        lookup
    )


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

df, car_master_df, CAR_NAME_LOOKUP = (
    load_and_prepare_database(
        DB_PATH,
        os.path.getmtime(
            DB_PATH
        ),
        CAR_MASTER_PATH,
        os.path.getmtime(
            CAR_MASTER_PATH
        )
    )
)


# ============================================================
# 必須列チェック
# ============================================================

required_columns = [
    "メーカー",
    "車種",
    "商品メーカー",
    "カテゴリ",
    "商品型番",
    "商品名",
]


missing_columns = [
    col
    for col in required_columns
    if col not in df.columns
]


if missing_columns:

    st.error(
        "master_database.xlsx に必要な列がありません："
        +
        " / ".join(
            missing_columns
        )
    )

    st.stop()


# ============================================================
# セッション初期化
# ============================================================

if "searched" not in st.session_state:
    st.session_state.searched = False

if "page" not in st.session_state:
    st.session_state.page = 1

if "excel_ready" not in st.session_state:
    st.session_state.excel_ready = False


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
        "excel_ready",
    ]

    for key in keys:

        if key in st.session_state:

            del st.session_state[
                key
            ]

    st.session_state.searched = False
    st.session_state.page = 1
    st.session_state.excel_ready = False


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
# 車両メーカー
# ============================================================

makers = sorted(
    [
        x
        for x in df[
            "_メーカー"
        ].unique()
        if x
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
# 車種候補
#
# 全件iterrows()をしない
# ============================================================

if selected_maker == "指定なし":

    car_mask_for_select = pd.Series(
        True,
        index=df.index
    )

else:

    car_mask_for_select = (
        df[
            "_メーカー"
        ]
        ==
        selected_maker
    )


cars = sorted(
    [
        x
        for x in df.loc[
            car_mask_for_select,
            "_統合車種名"
        ].drop_duplicates().tolist()
        if x
    ]
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
# 年式
# ============================================================

st.write(
    "#### 年式"
)


year_col, month_col = st.columns(
    2
)


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


selected_year = year_lookup.get(
    selected_year_label
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


product_row1_col1, product_row1_col2, product_row1_col3 = st.columns(
    3
)


# ============================================================
# 型式
# ============================================================

with product_row1_col1:

    model_keyword = st.text_input(
        "型式",
        placeholder="例：ZN8 / TRH200V",
        key="model_keyword"
    )


# ============================================================
# 商品メーカー
# ============================================================

product_makers = sorted(
    [
        x
        for x in df[
            "_商品メーカー"
        ].unique()
        if x
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
# 商品メーカー → カテゴリ連動
# ============================================================

if selected_product_maker == "指定なし":

    category_mask = pd.Series(
        True,
        index=df.index
    )

else:

    category_mask = (
        df[
            "_商品メーカー"
        ]
        ==
        selected_product_maker
    )


categories = sorted(
    [
        x
        for x in df.loc[
            category_mask,
            "_カテゴリ"
        ].drop_duplicates().tolist()
        if x
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


# ============================================================
# 商品型番・商品名
# ============================================================

product_row2_col1, product_row2_col2 = st.columns(
    2
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
# 検索ボタン
# ============================================================

if st.button(
    "🔍 検索する",
    type="primary",
    width="stretch"
):

    st.session_state.searched = True
    st.session_state.page = 1
    st.session_state.excel_ready = False


if not st.session_state.searched:

    st.info(
        "条件を指定して「検索する」を押してください。"
    )

    st.stop()


# ============================================================
# 高速検索処理
#
# 原則としてBoolean Maskのみ
# ============================================================

mask = pd.Series(
    True,
    index=df.index
)


# ============================================================
# 車両メーカー
# ============================================================

if selected_maker != "指定なし":

    mask &= (
        df[
            "_メーカー"
        ]
        ==
        selected_maker
    )


# ============================================================
# 統合車種
# ============================================================

if selected_car != "指定なし":

    mask &= (
        df[
            "_統合車種名"
        ]
        ==
        selected_car
    )


# ============================================================
# 年月
# ============================================================

if selected_year is not None:

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

    known_year_mask = (
        df[
            "_開始年月"
        ].notna()
        &
        df[
            "_終了年月"
        ].notna()
    )

    year_match_mask = (
        known_year_mask
        &
        ~(
            (
                df[
                    "_終了年月"
                ]
                <
                search_start
            )
            |
            (
                df[
                    "_開始年月"
                ]
                >
                search_end
            )
        )
    )

    # 年式解析不能のPioneerを、年式だけを理由に落とさない
    pioneer_unknown_year_mask = (
        (
            df[
                "_商品メーカー"
            ]
            ==
            "Pioneer"
        )
        &
        ~known_year_mask
    )

    mask &= (
        year_match_mask
        |
        pioneer_unknown_year_mask
    )


# ============================================================
# 車両型式
# ============================================================

if model_keyword:

    keyword = normalize_search(
        model_keyword
    )

    model_mask = (
        df[
            "_実型式検索"
        ].str.contains(
            re.escape(
                keyword
            ),
            na=False
        )
        |
        df[
            "_型式検索"
        ].str.contains(
            re.escape(
                keyword
            ),
            na=False
        )
    )

    mask &= model_mask


# ============================================================
# 商品メーカー
# ============================================================

if selected_product_maker != "指定なし":

    mask &= (
        df[
            "_商品メーカー"
        ]
        ==
        selected_product_maker
    )


# ============================================================
# カテゴリ
# ============================================================

if selected_category != "指定なし":

    mask &= (
        df[
            "_カテゴリ"
        ]
        ==
        selected_category
    )


# ============================================================
# 商品型番
# ============================================================

if product_code:

    keyword = normalize_search(
        product_code
    )

    mask &= (
        df[
            "_商品型番検索"
        ].str.contains(
            re.escape(
                keyword
            ),
            na=False
        )
    )


# ============================================================
# 商品名
# ============================================================

if product_name:

    keyword = normalize_search(
        product_name
    )

    mask &= (
        df[
            "_商品名検索"
        ].str.contains(
            re.escape(
                keyword
            ),
            na=False
        )
    )


# ============================================================
# 現行商品のみ
# ============================================================

if current_only:

    mask &= (
        df[
            "_生産状態"
        ]
        ==
        "現行"
    )


# ============================================================
# 適合商品のみ
# ============================================================

if fit_only:

    mask &= (
        df[
            "_最終適合状態"
        ]
        ==
        "適合"
    )


search_df = df.loc[
    mask
].copy()


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
        st.session_state.excel_ready = False

        st.rerun()


with retry_col2:

    if st.button(
        "🔄 検索条件をすべてリセット",
        width="stretch"
    ):

        reset_conditions()

        st.rerun()


# ============================================================
# 検索結果
# ============================================================

st.subheader(
    "③ 検索結果"
)


fit_count = int(
    (
        search_df[
            "_最終適合状態"
        ]
        ==
        "適合"
    ).sum()
)


check_count = int(
    (
        search_df[
            "_最終適合状態"
        ]
        ==
        "要確認"
    ).sum()
)


ng_count = int(
    (
        search_df[
            "_最終適合状態"
        ]
        ==
        "不適合"
    ).sum()
)


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
# 検索条件確認
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

    if model_keyword:

        st.write(
            "**型式：**",
            model_keyword
        )

    if selected_product_maker != "指定なし":

        st.write(
            "**商品メーカー：**",
            selected_product_maker
        )

    if selected_category != "指定なし":

        st.write(
            "**カテゴリ：**",
            selected_category
        )

    if product_code:

        st.write(
            "**商品型番：**",
            product_code
        )

    if product_name:

        st.write(
            "**商品名：**",
            product_name
        )


# ============================================================
# Excel出力
#
# 画面表示時には作らない
# ============================================================

st.write(
    "#### 検索結果のExcel出力"
)


if st.button(
    "Excelファイルを作成",
    width="stretch"
):

    st.session_state.excel_ready = True


if st.session_state.excel_ready:

    with st.spinner(
        "Excelファイルを作成しています..."
    ):

        helper_columns = [
            col
            for col in search_df.columns
            if col.startswith(
                "_"
            )
        ]

        download_df = search_df.drop(
            columns=helper_columns,
            errors="ignore"
        ).copy()

        download_df[
            "最終適合状態"
        ] = search_df[
            "_最終適合状態"
        ].values

        download_df[
            "統合車種名"
        ] = search_df[
            "_統合車種名"
        ].values

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
        len(
            search_df
        )
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
    int(
        page
    )
    -
    1
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
# 詳細表示
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

    fitment = clean_text(
        row.get(
            "_最終適合状態",
            "要確認"
        )
    )

    title_product = (
        code
        or
        name
        or
        "商品情報"
    )

    title = (
        f"{maker} | "
        f"{category} | "
        f"{title_product} | "
        f"{fitment}"
    )

    with st.expander(
        title
    ):

        left, right = st.columns(
            2
        )

        # ====================================================
        # 車両情報
        # ====================================================

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

            merged_car_name = clean_text(
                row.get(
                    "_統合車種名",
                    original_car_name
                )
            )

            st.write(
                "**車両メーカー：**",
                vehicle_maker
            )

            st.write(
                "**車種：**",
                original_car_name
            )

            if (
                merged_car_name
                and
                merged_car_name
                !=
                original_car_name
            ):

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

        # ====================================================
        # 商品情報
        # ====================================================

        with right:

            st.write(
                "**商品メーカー：**",
                maker
            )

            st.write(
                "**カテゴリ：**",
                category
            )

            suspicious_name = False

            if name:

                suspicious_words = [
                    "必要です",
                    "必要となります",
                    "使用できません",
                    "取付できません",
                    "装着できません",
                    "別売",
                    "注意",
                    "接続には",
                    "取付には",
                ]

                suspicious_name = any(
                    word in name
                    for word in suspicious_words
                )

            if (
                name
                and
                not suspicious_name
            ):

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

        # ====================================================
        # 適合状態
        # ====================================================

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

        # ====================================================
        # Pioneer判定根拠
        # ====================================================

        data_type = clean_text(
            row.get(
                "データ種別",
                ""
            )
        )

        data_type_lower = data_type.lower()

        if maker == "Pioneer":

            if data_type_lower == "select":

                st.info(
                    "Pioneer公式「車種別カーナビセレクト」"
                    "に基づく判定です。"
                )

            elif data_type_lower == "gtable":

                st.info(
                    "Pioneer公式の商品別適合情報"
                    "（gtable）に基づく判定です。"
                )

            elif data_type_lower == "rear_monitor":

                st.info(
                    "Pioneer公式「フリップダウンモニター適合情報」"
                    "に基づく判定です。"
                )

            elif data_type.upper() == "PDF":

                st.warning(
                    "Pioneer公式取付資料への掲載情報です。"
                    "商品型番単位の直接適合が確認できないため"
                    "「要確認」としています。"
                )

            elif data_type_lower == "business補完":

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

                else:

                    st.info(
                        "Pioneerの既存公式適合情報を参照した"
                        "業務用モデル候補です。"
                    )

        # ====================================================
        # 取付キット
        # ====================================================

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

        # ====================================================
        # 注意事項
        # ====================================================

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

        moved_name_note = ""

        if suspicious_name:

            moved_name_note = name

        if (
            reason
            or
            notes
            or
            moved_name_note
        ):

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

                st.warning(
                    notes
                )

            if (
                moved_name_note
                and
                moved_name_note != notes
                and
                moved_name_note != reason
            ):

                st.warning(
                    moved_name_note
                )

        # ====================================================
        # URL
        # ====================================================

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

        link_col1, link_col2, link_col3 = st.columns(
            3
        )

        if product_url:

            with link_col1:

                st.link_button(
                    "商品ページ",
                    product_url,
                    width="stretch"
                )

        if source_url:

            with link_col2:

                st.link_button(
                    "適合情報ページ",
                    source_url,
                    width="stretch"
                )

        if pdf_url:

            with link_col3:

                st.link_button(
                    "PDF・資料",
                    pdf_url,
                    width="stretch"
                )
