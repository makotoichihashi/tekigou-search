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

st.set_page_config(
    page_title="車種別 適合情報検索",
    page_icon="🚗",
    layout="wide"
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
# 和暦変換
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
        r"R\s*(\d+)",
        text
    )

    if match:
        return 2018 + int(
            match.group(1)
        )

    match = re.fullmatch(
        r"H\s*(\d+)",
        text
    )

    if match:
        return 1988 + int(
            match.group(1)
        )

    match = re.fullmatch(
        r"S\s*(\d+)",
        text
    )

    if match:
        return 1925 + int(
            match.group(1)
        )

    return None


def parse_year_range_from_text(
    value
):

    text = clean_text(
        value
    )

    if not text:
        return None, None

    text = text.replace("令和", "R")
    text = text.replace("平成", "H")
    text = text.replace("昭和", "S")
    text = text.replace("〜", "～")

    era_matches = re.findall(
        r"([RHS])\s*(\d{1,2})(?:\s*/\s*\d{1,2})?",
        text,
        flags=re.IGNORECASE
    )

    converted_years = []

    for era, year in era_matches:

        ad_year = japanese_year_to_ad(
            era,
            year
        )

        if ad_year is not None:
            converted_years.append(
                ad_year
            )

    if converted_years:

        start_year = converted_years[0]

        if len(converted_years) >= 2:
            end_year = converted_years[-1]
        else:
            if (
                "～" in text
                and
                text.rstrip().endswith("～")
            ):
                end_year = 9999
            else:
                end_year = start_year

        return start_year, end_year

    western_years = re.findall(
        r"(?<!\d)(19\d{2}|20\d{2})(?!\d)",
        text
    )

    if western_years:

        western_years = [
            int(x)
            for x in western_years
        ]

        start_year = western_years[0]

        if len(western_years) >= 2:
            end_year = western_years[-1]
        else:
            if (
                "～" in text
                and
                text.rstrip().endswith("～")
            ):
                end_year = 9999
            else:
                end_year = start_year

        return start_year, end_year

    return None, None


# ============================================================
# DB読込
# ============================================================

@st.cache_data
def load_database():

    try:
        df = pd.read_excel(
            DB_PATH,
            sheet_name="master"
        )
    except:
        df = pd.read_excel(
            DB_PATH
        )

    return df.fillna("")


# ============================================================
# 部分一致検索
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
        re.escape(keyword),
        na=False
    )


# ============================================================
# 年式検索
# ============================================================

def filter_by_year(
    df,
    target_year
):

    if target_year is None:
        return df

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
                else
                None
            )
        except:
            start_year = None

        try:
            end_year = (
                int(float(end_year))
                if end_year
                else
                None
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
            return target_year >= start_year

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

        parsed_start, parsed_end = (
            parse_year_range_from_text(
                year_text
            )
        )

        if (
            parsed_start is not None
            and
            parsed_end is not None
        ):
            return (
                parsed_start
                <= target_year
                <= parsed_end
            )

        return False

    mask = df.apply(
        check_row,
        axis=1
    )

    return df[
        mask
    ]


# ============================================================
# Pioneer情報精度
# ============================================================

def get_quality(row):

    maker = clean_text(
        row.get(
            "商品メーカー",
            ""
        )
    )

    data_type = clean_text(
        row.get(
            "データ種別",
            ""
        )
    )

    if maker != "Pioneer":
        return ""

    if data_type.lower() == "gtable":
        return "Pioneer公式商品別適合"

    if data_type.upper() == "PDF":
        return "Pioneer公式資料掲載情報・要確認"

    return "Pioneer公式情報"


# ============================================================
# DB存在確認
# ============================================================

if not os.path.exists(
    DB_PATH
):

    st.error(
        "master_database.xlsx が見つかりません。"
    )

    st.stop()


df = load_database()


# ============================================================
# ヘッダー
# ============================================================

st.title(
    "🚗 車種別 適合情報検索"
)

st.caption(
    f"登録データ：{len(df):,}件"
)


# ============================================================
# 検索条件
# ============================================================

st.subheader(
    "検索条件"
)

search_df = df.copy()


# ============================================================
# 1段目
# ============================================================

col1, col2, col3 = st.columns(
    3
)


with col1:

    makers = sorted(
        [
            clean_text(x)
            for x in
            df["メーカー"].unique()
            if clean_text(x)
        ]
    )

    selected_maker = st.selectbox(
        "車両メーカー",
        [
            "指定なし"
        ]
        +
        makers
    )


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


with col2:

    cars = sorted(
        [
            clean_text(x)
            for x in
            search_df["車種"].unique()
            if clean_text(x)
        ]
    )

    selected_car = st.selectbox(
        "車種",
        [
            "指定なし"
        ]
        +
        cars
    )


if selected_car != "指定なし":

    search_df = search_df[
        search_df[
            "車種"
        ].map(
            clean_text
        )
        ==
        selected_car
    ]


with col3:

    year_input = st.text_input(
        "年式",
        placeholder="例：2026 / R8 / H30"
    )


target_year = convert_year_input(
    year_input
)


if year_input:

    if target_year is None:

        st.warning(
            "年式を判定できません。"
        )

    else:

        search_df = filter_by_year(
            search_df,
            target_year
        )


# ============================================================
# 2段目
# ============================================================

col4, col5, col6 = st.columns(
    3
)


with col4:

    model_keyword = st.text_input(
        "型式",
        placeholder="例：TRH200V"
    )


if model_keyword:

    search_df = search_df[
        contains_value(
            search_df[
                "実型式"
            ],
            model_keyword
        )
        |
        contains_value(
            search_df[
                "型式"
            ],
            model_keyword
        )
    ]


with col5:

    selected_product_maker = st.selectbox(
        "商品メーカー",
        [
            "指定なし",
            "Pioneer",
            "ALPINE",
            "KENWOOD"
        ]
    )


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


with col6:

    categories = sorted(
        [
            clean_text(x)
            for x in
            search_df["カテゴリ"].unique()
            if clean_text(x)
        ]
    )

    selected_category = st.selectbox(
        "カテゴリ",
        [
            "指定なし"
        ]
        +
        categories
    )


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


# ============================================================
# 3段目
# ============================================================

col7, col8 = st.columns(
    2
)


with col7:

    product_code = st.text_input(
        "商品型番",
        placeholder="例：AVIC-RF722"
    )


if product_code:

    search_df = search_df[
        contains_value(
            search_df[
                "商品型番"
            ],
            product_code
        )
    ]


with col8:

    product_name = st.text_input(
        "商品名",
        placeholder="商品名の一部でも検索できます"
    )


if product_name:

    search_df = search_df[
        contains_value(
            search_df[
                "商品名"
            ],
            product_name
        )
    ]


# ============================================================
# 結果
# ============================================================

st.divider()

st.subheader(
    "検索結果"
)

search_df = search_df.reset_index(
    drop=True
)

st.metric(
    "該当件数",
    f"{len(search_df):,} 件"
)


if search_df.empty:

    st.info(
        "該当する適合情報はありません。"
    )

    st.stop()


# ============================================================
# 集計
# ============================================================

col_a, col_b, col_c = st.columns(
    3
)


with col_a:

    st.write(
        "#### 商品メーカー"
    )

    st.dataframe(
        search_df[
            "商品メーカー"
        ]
        .value_counts()
        .rename_axis(
            "メーカー"
        )
        .reset_index(
            name="件数"
        ),
        hide_index=True,
        use_container_width=True
    )


with col_b:

    st.write(
        "#### カテゴリ"
    )

    st.dataframe(
        search_df[
            "カテゴリ"
        ]
        .value_counts()
        .rename_axis(
            "カテゴリ"
        )
        .reset_index(
            name="件数"
        ),
        hide_index=True,
        use_container_width=True
    )


with col_c:

    st.write(
        "#### 適合状態"
    )

    st.dataframe(
        search_df[
            "適合状態"
        ]
        .value_counts()
        .rename_axis(
            "状態"
        )
        .reset_index(
            name="件数"
        ),
        hide_index=True,
        use_container_width=True
    )


# ============================================================
# 検索結果一覧
# ============================================================

st.write(
    "### 適合情報"
)


for index, row in search_df.iterrows():

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
            "適合状態",
            ""
        )
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

        c1, c2 = st.columns(
            2
        )

        with c1:

            st.write(
                "**車両メーカー：**",
                clean_text(
                    row.get(
                        "メーカー",
                        ""
                    )
                )
            )

            st.write(
                "**車種：**",
                clean_text(
                    row.get(
                        "車種",
                        ""
                    )
                )
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

            st.write(
                "**年式：**",
                year
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


        with c2:

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

            st.write(
                "**適合状態：**",
                fitment
            )


        quality = get_quality(
            row
        )

        if quality:

            st.info(
                quality
            )


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
                "#### 適合条件・注意事項"
            )

            if reason:

                st.write(
                    reason
                )

            if (
                notes
                and
                notes != reason
            ):

                st.write(
                    notes
                )


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

        if product_url:

            st.link_button(
                "商品ページ",
                product_url
            )

        if source_url:

            st.link_button(
                "適合情報ページ",
                source_url
            )

        if pdf_url:

            st.link_button(
                "PDF・資料",
                pdf_url
            )


# ============================================================
# Excelダウンロード
# ============================================================

buffer = BytesIO()

with pd.ExcelWriter(
    buffer,
    engine="openpyxl"
) as writer:

    search_df.to_excel(
        writer,
        sheet_name="検索結果",
        index=False
    )


st.download_button(
    label="検索結果をExcelでダウンロード",
    data=buffer.getvalue(),
    file_name="search_result.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    )
)