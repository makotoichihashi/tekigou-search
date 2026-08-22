import os
import re
import unicodedata
from io import BytesIO

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
# スマホ・タブレット対応
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
            font-size: 1rem;
            width: 100%;
        }
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 共通文字処理
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
# 車種名比較用正規化
# ============================================================

def normalize_car_key(value):

    text = clean_text(
        value
    )

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFKC",
        text
    )

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
# 年式正規化
#
# H03/05 → H3/5
# R08/02 → R8/2
# ============================================================

def normalize_year_text(value):

    text = clean_text(
        value
    )

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFKC",
        text
    )

    text = text.replace("〜", "～")
    text = text.replace("~", "～")
    text = text.replace("－", "～")
    text = text.replace("―", "～")
    text = text.replace("−", "～")

    text = text.replace("令和", "R")
    text = text.replace("平成", "H")
    text = text.replace("昭和", "S")


    def era_replace(match):

        era = match.group(1).upper()

        try:
            year = int(
                match.group(2)
            )
        except:
            return match.group(0)

        return f"{era}{year}"


    text = re.sub(
        r"([RHS])0*(\d{1,2})",
        era_replace,
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"/0+(\d+)",
        r"/\1",
        text
    )

    text = re.sub(
        r"(?<!\d)0+(\d+)年",
        r"\1年",
        text
    )

    text = re.sub(
        r"(?<!\d)0+(\d+)月",
        r"\1月",
        text
    )

    return text.strip()


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
# 手入力年式
# ============================================================

def convert_year_input(value):

    text = clean_text(
        value
    ).upper()

    text = text.replace("令和", "R")
    text = text.replace("平成", "H")
    text = text.replace("昭和", "S")
    text = text.replace("年", "")

    if not text:
        return None

    if re.fullmatch(
        r"\d{4}",
        text
    ):
        return int(text)

    match = re.fullmatch(
        r"R\s*0*(\d+)",
        text
    )

    if match:
        return 2018 + int(
            match.group(1)
        )

    match = re.fullmatch(
        r"H\s*0*(\d+)",
        text
    )

    if match:
        return 1988 + int(
            match.group(1)
        )

    match = re.fullmatch(
        r"S\s*0*(\d+)",
        text
    )

    if match:
        return 1925 + int(
            match.group(1)
        )

    return None


# ============================================================
# 年式範囲解析
# ============================================================

def parse_year_range_from_text(value):

    text = normalize_year_text(
        value
    )

    if not text:
        return None, None

    era_matches = re.findall(
        r"([RHS])\s*(\d{1,2})(?:\s*/\s*\d{1,2})?",
        text,
        flags=re.IGNORECASE
    )

    years = []

    for era, year in era_matches:

        ad_year = japanese_year_to_ad(
            era,
            year
        )

        if ad_year is not None:
            years.append(
                ad_year
            )

    if years:

        start_year = years[0]

        if len(years) >= 2:
            end_year = years[-1]

        elif (
            "～" in text
            and
            text.rstrip().endswith("～")
        ):
            end_year = 9999

        else:
            end_year = start_year

        return (
            start_year,
            end_year
        )


    western_years = re.findall(
        r"(?<!\d)(19\d{2}|20\d{2})(?!\d)",
        text
    )

    if western_years:

        years = [
            int(x)
            for x in western_years
        ]

        start_year = years[0]

        if len(years) >= 2:
            end_year = years[-1]

        elif (
            "～" in text
            and
            text.rstrip().endswith("～")
        ):
            end_year = 9999

        else:
            end_year = start_year

        return (
            start_year,
            end_year
        )

    return None, None


# ============================================================
# Excel読込
#
# mtimeを引数にすることで
# Excel差し替え時にキャッシュを更新
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

    st.write(
        "GitHubで app.py と同じ場所に "
        "car_name_master_final.xlsx をアップロードしてください。"
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
# 車種統合マスター辞書作成
#
# キー：
# メーカー + 元車種名
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


    lookup_key = (
        normalize_search(
            maker
        ),
        normalize_car_key(
            original_name
        )
    )


    CAR_NAME_LOOKUP[
        lookup_key
    ] = merged_name


# ============================================================
# 車種名統合
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

    if key in CAR_NAME_LOOKUP:
        return CAR_NAME_LOOKUP[
            key
        ]

    # マスターに存在しない車種は元名称
    return car_name


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
# 年式検索
# ============================================================

def filter_by_year(
    target_df,
    target_year
):

    if target_year is None:
        return target_df


    def check_row(row):

        start_year = clean_text(
            row.get(
                "開始年",
                ""
            )
        )

        end_year = clean_text(
            row.get(
                "終了年",
                ""
            )
        )


        try:
            start_year = (
                int(float(start_year))
                if start_year
                else None
            )
        except:
            start_year = None


        try:
            end_year = (
                int(float(end_year))
                if end_year
                else None
            )
        except:
            end_year = None


        if (
            start_year is not None
            and
            end_year is not None
            and
            1900 <= start_year <= 2200
            and
            1900 <= end_year <= 2200
        ):
            return (
                start_year
                <= target_year
                <= end_year
            )


        if (
            start_year is not None
            and
            end_year is None
            and
            1900 <= start_year <= 2200
        ):
            return (
                target_year
                >= start_year
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


        start, end = (
            parse_year_range_from_text(
                year_text
            )
        )


        if (
            start is not None
            and
            end is not None
        ):
            return (
                start
                <= target_year
                <= end
            )

        return False


    mask = target_df.apply(
        check_row,
        axis=1
    )

    return target_df[
        mask
    ]


# ============================================================
# Pioneer 最終適合判定
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


        # JUST FIT商品別
        if data_type_lower == "gtable":

            if raw_fitment in [
                "適合",
                "不適合",
                "要確認"
            ]:
                return raw_fitment

            return "要確認"


        # 車種別カーナビセレクト
        if data_type_lower == "select":

            if raw_fitment in [
                "適合",
                "不適合",
                "要確認"
            ]:
                return raw_fitment

            return "要確認"


        # PDF掲載は断定しない
        if data_type.upper() == "PDF":
            return "要確認"


        # 業務用補完
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
        "year_input",
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
    f"登録データ：{len(df):,}件　"
    f"｜ 車種統合ルール：{len(CAR_NAME_LOOKUP):,}件"
)

st.write(
    "車両を選択したあと、商品条件を指定して検索してください。"
)


# ============================================================
# ① 車両
# ============================================================

st.subheader(
    "① 車両を選択"
)


vehicle_col1, vehicle_col2, vehicle_col3 = (
    st.columns(
        3
    )
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


with vehicle_col1:

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
# 車種候補
#
# ここでExcel統合マスターを適用
# ============================================================

merged_car_names = []


for _, row in car_source_df[
    [
        "メーカー",
        "車種"
    ]
].drop_duplicates().iterrows():

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


with vehicle_col2:

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
# 選択車種に属する元データ抽出
# ============================================================

year_source_df = car_source_df.copy()


if selected_car != "指定なし":

    car_mask = year_source_df.apply(
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

    year_source_df = year_source_df[
        car_mask
    ]


# ============================================================
# 年式候補
# ============================================================

year_candidates = []


if "年式原文" in year_source_df.columns:

    year_candidates.extend(
        [
            normalize_year_text(x)
            for x in
            year_source_df[
                "年式原文"
            ].unique()
            if normalize_year_text(x)
        ]
    )


if "年式" in year_source_df.columns:

    year_candidates.extend(
        [
            normalize_year_text(x)
            for x in
            year_source_df[
                "年式"
            ].unique()
            if normalize_year_text(x)
        ]
    )


year_candidates = sorted(
    list(
        dict.fromkeys(
            year_candidates
        )
    )
)


with vehicle_col3:

    selected_year_text = st.selectbox(
        "年式",
        [
            "指定なし"
        ]
        +
        year_candidates,
        key="year_select"
    )


# ============================================================
# ② 商品条件
# ============================================================

st.subheader(
    "② 商品条件"
)


row1_col1, row1_col2, row1_col3 = (
    st.columns(
        3
    )
)


with row1_col1:

    year_input = st.text_input(
        "年式を直接入力",
        placeholder="例：2026 / R8 / H30",
        key="year_input"
    )


with row1_col2:

    model_keyword = st.text_input(
        "型式",
        placeholder="例：ZN8 / TRH200V",
        key="model_keyword"
    )


with row1_col3:

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
# 商品メーカー → カテゴリ
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


row2_col1, row2_col2, row2_col3 = (
    st.columns(
        3
    )
)


with row2_col1:

    selected_category = st.selectbox(
        "カテゴリ",
        [
            "指定なし"
        ]
        +
        categories,
        key="category"
    )


with row2_col2:

    product_code = st.text_input(
        "商品型番",
        placeholder="例：AVIC-RW822-D",
        key="product_code"
    )


with row2_col3:

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


if not st.session_state.searched:

    st.info(
        "条件を指定して「検索する」を押してください。"
    )

    st.stop()


# ============================================================
# 検索処理
# ============================================================

search_df = df.copy()


# メーカー
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


# 車種統合マスター
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


# 年式選択
if selected_year_text != "指定なし":

    selected_normalized_year = (
        normalize_year_text(
            selected_year_text
        )
    )

    year_mask = pd.Series(
        False,
        index=search_df.index
    )


    if "年式原文" in search_df.columns:

        year_mask = (
            year_mask
            |
            search_df[
                "年式原文"
            ].map(
                normalize_year_text
            ).eq(
                selected_normalized_year
            )
        )


    if "年式" in search_df.columns:

        year_mask = (
            year_mask
            |
            search_df[
                "年式"
            ].map(
                normalize_year_text
            ).eq(
                selected_normalized_year
            )
        )


    search_df = search_df[
        year_mask
    ]


# 年式直接入力
if year_input:

    target_year = convert_year_input(
        year_input
    )

    if target_year is None:

        st.warning(
            "入力された年式を判定できません。"
        )

    else:

        search_df = filter_by_year(
            search_df,
            target_year
        )


# 型式
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


# 商品メーカー
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


# カテゴリ
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


# 型番
if product_code:

    search_df = search_df[
        contains_value(
            search_df[
                "商品型番"
            ],
            product_code
        )
    ]


# 商品名
if product_name:

    search_df = search_df[
        contains_value(
            search_df[
                "商品名"
            ],
            product_name
        )
    ]


# 現行商品のみ
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


# 適合のみ
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
# ③ 結果
# ============================================================

st.subheader(
    "③ 検索結果"
)


# ============================================================
# 適合状態集計
# ============================================================

result_summary = search_df.copy()


if not result_summary.empty:

    result_summary[
        "最終適合状態"
    ] = result_summary.apply(
        get_final_fitment,
        axis=1
    )


    fit_count = int(
        (
            result_summary[
                "最終適合状態"
            ]
            ==
            "適合"
        ).sum()
    )


    check_count = int(
        (
            result_summary[
                "最終適合状態"
            ]
            ==
            "要確認"
        ).sum()
    )


    ng_count = int(
        (
            result_summary[
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
        f"{len(search_df):,}"
    )


with metric2:

    st.metric(
        "✅ 適合",
        f"{fit_count:,}"
    )


with metric3:

    st.metric(
        "⚠️ 要確認",
        f"{check_count:,}"
    )


with metric4:

    st.metric(
        "❌ 不適合",
        f"{ng_count:,}"
    )


if search_df.empty:

    st.warning(
        "該当する適合情報はありません。"
    )

    st.stop()


# ============================================================
# 検索条件表示
# ============================================================

with st.expander(
    "今回の検索条件"
):

    st.write(
        "**車両メーカー：**",
        selected_maker
    )

    st.write(
        "**統合車種名：**",
        selected_car
    )

    st.write(
        "**年式：**",
        selected_year_text
    )

    st.write(
        "**商品メーカー：**",
        selected_product_maker
    )

    st.write(
        "**カテゴリ：**",
        selected_category
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


        # ----------------------------------------------------
        # 車両
        # ----------------------------------------------------

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


            # 元データと統合名が違う時だけ表示
            if (
                merged_car_name
                !=
                original_car_name
            ):

                st.caption(
                    f"統合検索車種：{merged_car_name}"
                )


            vehicle_type = clean_text(
                row.get(
                    "車両タイプ",
                    ""
                )
            )


            if vehicle_type:

                st.write(
                    "**車両タイプ：**",
                    vehicle_type
                )


            year = clean_text(
                row.get(
                    "年式原文",
                    ""
                )
            )


            if not year:

                year = clean_text(
                    row.get(
                        "年式",
                        ""
                    )
                )


            if year:

                st.write(
                    "**年式：**",
                    normalize_year_text(
                        year
                    )
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


        # ----------------------------------------------------
        # 商品
        # ----------------------------------------------------

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

            data_type_lower = (
                data_type.lower()
            )


            if data_type_lower == "select":

                st.info(
                    "Pioneer公式「車種別カーナビセレクト」に"
                    "基づく判定です。"
                )


            elif data_type_lower == "gtable":

                st.info(
                    "Pioneer公式の商品別適合情報"
                    "（gtable）に基づく判定です。"
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
                        "参照して生成した業務用モデル候補です。"
                    )

                else:

                    st.info(
                        "Pioneer公式適合情報を参照して生成した"
                        "業務用モデル候補です。"
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


        # ----------------------------------------------------
        # 関連品番
        # ----------------------------------------------------

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
