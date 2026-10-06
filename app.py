from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]
# ชื่อคอลัมน์ของแต่ละปีไม่เหมือนกัน จึงปรับให้เป็นชื่อเดียวกัน
RENAME = {
    "ใช้ประโยชน์ (กก.)": "นำไปใช้ประโยชน์ (กก.)",
    "ร้อยละส่งกำจัดลดลง": "ร้อยละขยะส่งกำจัดลดลง",
}
GENERATED = "ขยะที่เกิดขึ้น (กก.)"
UTILIZED = "นำไปใช้ประโยชน์ (กก.)"
DISPOSED = "ขยะที่ส่งกำจัด (กก.)"


@st.cache_data
def load_data() -> pd.DataFrame:
    # ไฟล์ต้นฉบับจาก data.go.th เข้ารหัสภาษาไทยแบบ cp874 (TIS-620)
    frames = [
        pd.read_csv(f, encoding="cp874").rename(columns=RENAME)
        for f in sorted(DATA_DIR.glob("waste_*.csv"))
    ]
    df = pd.concat(frames, ignore_index=True)
    df["เดือน"] = pd.Categorical(df["เดือน"], categories=MONTHS, ordered=True)
    return df


st.set_page_config(page_title="ปริมาณขยะมูลฝอย กรมอุทยานฯ", page_icon="♻️", layout="wide")
st.title("♻️ ปริมาณขยะมูลฝอย กรมอุทยานแห่งชาติ สัตว์ป่า และพันธุ์พืช")
st.caption(
    "แหล่งข้อมูล: [data.go.th – ปริมาณขยะมูลฝอย](https://data.go.th/dataset/gdpublish-69-dnp01-11-01) "
    "(ปี 2568 ครบ 12 เดือน, ปี 2569 ม.ค.–พ.ค.)"
)

df = load_data()

# ---------- Interactive widgets ----------
with st.sidebar:
    st.header("ตัวกรองข้อมูล")
    years = sorted(df["ปี"].unique())
    year = st.selectbox("ปี (พ.ศ.)", years, index=len(years) - 1)
    groups = st.multiselect(
        "สังกัด", sorted(df["สังกัด"].unique()), default=sorted(df["สังกัด"].unique())
    )
    top_n = st.slider("จำนวนหน่วยงานในกราฟอันดับ", min_value=5, max_value=20, value=10)

data = df[(df["ปี"] == year) & (df["สังกัด"].isin(groups))]
if data.empty:
    st.warning("ไม่มีข้อมูลตามตัวกรองที่เลือก กรุณาเลือกสังกัดอย่างน้อย 1 รายการ")
    st.stop()

# ---------- KPI ----------
total = data[GENERATED].sum()
utilized = data[UTILIZED].sum()
disposed = data[DISPOSED].sum()
c1, c2, c3, c4 = st.columns(4)
c1.metric("ขยะทั้งหมด (กก.)", f"{total:,.0f}")
c2.metric("ใช้ประโยชน์ (กก.)", f"{utilized:,.0f}")
c3.metric("ส่งกำจัด (กก.)", f"{disposed:,.0f}")
c4.metric("อัตราใช้ประโยชน์", f"{utilized / total:.1%}" if total else "-")

# ---------- กราฟ 1: แนวโน้มรายเดือน ----------
st.subheader(f"แนวโน้มปริมาณขยะรายเดือน ปี {year}")
monthly = (
    data.groupby("เดือน", observed=True)[[GENERATED, UTILIZED, DISPOSED]]
    .sum()
    .reset_index()
    .melt(id_vars="เดือน", var_name="ประเภท", value_name="กิโลกรัม")
)
fig_month = px.line(monthly, x="เดือน", y="กิโลกรัม", color="ประเภท", markers=True)
fig_month.update_layout(
    legend={"title": "", "orientation": "h", "y": 1.02, "yanchor": "bottom"},
    hovermode="x unified",
)
st.plotly_chart(fig_month, width="stretch")

# ---------- กราฟ 2: หน่วยงานที่มีขยะมากที่สุด ----------
st.subheader(f"{top_n} หน่วยงานที่มีขยะเกิดขึ้นมากที่สุด")
by_agency = (
    data.groupby("หน่วยงาน")[[UTILIZED, DISPOSED, GENERATED]]
    .sum()
    .nlargest(top_n, GENERATED)
    .reset_index()
)
fig_agency = px.bar(
    by_agency.melt(id_vars="หน่วยงาน", value_vars=[UTILIZED, DISPOSED],
                   var_name="ประเภท", value_name="กิโลกรัม"),
    x="กิโลกรัม", y="หน่วยงาน", color="ประเภท", orientation="h",
)
fig_agency.update_layout(
    yaxis={"categoryorder": "total ascending", "title": ""},
    legend={"title": "", "orientation": "h", "y": 1.02, "yanchor": "bottom"},
    height=max(400, top_n * 35),
)
st.plotly_chart(fig_agency, width="stretch")

# ---------- กราฟ 3: สัดส่วนตามสังกัด ----------
st.subheader("สัดส่วนขยะตามสังกัด")
by_group = data.groupby("สังกัด")[GENERATED].sum().reset_index()
fig_group = px.pie(by_group, names="สังกัด", values=GENERATED, hole=0.45)
st.plotly_chart(fig_group, width="stretch")

# ---------- ตารางข้อมูล ----------
with st.expander("ดูตารางข้อมูล"):
    st.dataframe(data.sort_values(["หน่วยงาน", "เดือน"]), width="stretch", hide_index=True)
    st.download_button(
        "ดาวน์โหลด CSV",
        data.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"waste_{year}.csv",
        mime="text/csv",
    )
