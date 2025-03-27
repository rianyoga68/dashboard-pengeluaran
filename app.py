import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import date, datetime

# 🔹 Set Page Config
st.set_page_config(layout="wide", page_title="Dashboard Pengeluaran")

# 🔹 Konfigurasi Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/1XhB97l_K4kJbbKSgQoW2mGFW3AQr5C6Esc2acgh1IGI/gviz/tq?tqx=out:csv"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScYo4LMp6sp5etObYEBWKSM5mItl_siMK3X_jcgrC3ZD7nIxQ/formResponse"
LOG_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeSEc9OHafpas2PsnBY-uMMvB1KWzeGSI3umPEWMggxqJUs7A/formResponse"

# 🔹 Fungsi Logging ke Google Sheets Log
def log_transaction(message):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    log_payload = {
        "entry.412909777": timestamp,
        "entry.1680040627": message
    }
    requests.post(LOG_FORM_URL, data=log_payload)

# 🔹 Load Data dari Google Sheets
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, dtype_backend="numpy_nullable")

        # 🔹 Bersihkan nama kolom
        df.columns = df.columns.str.strip().str.replace(r"\s+", " ", regex=True).str.title()

        # 🔹 Konversi "Tanggal" menjadi hanya `datetime.date`
        df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce").dt.date

        log_transaction(f"✅ Data berhasil dimuat, jumlah baris: {len(df)}")
        return df
    except Exception as e:
        log_transaction(f"🚨 ERROR saat memuat data: {str(e)}")
        return pd.DataFrame()

# 🔹 Button Refresh Dashboard
st.button("🔄 Refresh Data", on_click=lambda: st.cache_data.clear())

# 🔹 Simpan Data ke Session State
st.session_state.data = load_data()

# 🔹 Notifikasi jika Data Berhasil Dimuat
if not st.session_state.data.empty:
    st.success(f"✅ Data berhasil dimuat! ({len(st.session_state.data)} baris)")

# 🔹 Form Input Data
col1, col2 = st.columns([1, 2])

with col1:
    with st.form("expense_form"):
        tanggal = st.date_input("Tanggal", date.today())
        nama_pengeluaran = st.text_input("Nama Pengeluaran")
        kategori = st.selectbox("Kategori", ["Makan", "Jajan", "Belanja", "Transportasi", "Laundry", "Lain - Lain"])
        total = st.number_input("Total Pengeluaran", min_value=0, step=1000)
        source = st.selectbox("Source", ["BRI", "Suami", "Istri"])
        submit = st.form_submit_button("Tambah Pengeluaran")

        if submit:
            payload = {
                "entry.82515941": tanggal.strftime("%Y-%m-%d"),
                "entry.777947910": nama_pengeluaran,
                "entry.1731311708": kategori,
                "entry.335974527": str(total),
                "entry.1970941208": source
            }

            success = requests.post(FORM_URL, data=payload).status_code == 200
            log_transaction(f"📌 Pengeluaran ditambahkan: {tanggal} | {nama_pengeluaran} | {kategori} | Rp {total:,} | {source}")

            if success:
                st.success("✅ Data berhasil dikirim ke Google Sheets & Log!")
            else:
                st.error("❌ Gagal mengirim data ke Google Sheets!")

# 🔹 Riwayat Pengeluaran
with col2:
    st.subheader("Riwayat Pengeluaran")

    # 🔹 Ambil input tanggal dengan default nilai hari ini
    tanggal_filter = st.date_input(
        "Filter Tanggal",
        value=[date.today(), date.today()],
        key="filter_tanggal"
    )

    # 🔹 Tangani kasus saat pengguna baru memilih satu tanggal
    if isinstance(tanggal_filter, list) and len(tanggal_filter) == 2:
        start_date, end_date = tanggal_filter
    elif isinstance(tanggal_filter, tuple) and len(tanggal_filter) == 2:
        start_date, end_date = tanggal_filter
    elif isinstance(tanggal_filter, list) and len(tanggal_filter) == 1:
        start_date = end_date = tanggal_filter[0]
    else:
        st.warning("⚠️ Silakan pilih rentang tanggal yang valid.")
        st.stop()

    # 🔹 Filter data berdasarkan tanggal
    filtered_data = st.session_state.data[
        (st.session_state.data["Tanggal"] >= start_date) & 
        (st.session_state.data["Tanggal"] <= end_date)
    ].copy()  # Gunakan copy untuk menghindari warning dari Pandas

    # 🔹 Hapus kolom timestamp jika ada
    timestamp_cols = [col for col in filtered_data.columns if "timestamp" in col.lower()]
    filtered_data = filtered_data.drop(columns=timestamp_cols, errors="ignore")

    # 🔹 Tampilkan hasil filter tanpa timestamp
    if not filtered_data.empty:
        st.dataframe(filtered_data.style.format({"Tanggal": lambda x: x.strftime("%d-%m-%Y")}))
    else:
        st.warning("⚠️ Tidak ada data pengeluaran pada rentang tanggal ini.")

# 🔹 Visualisasi Data
col3, col4 = st.columns([1, 2])

with col3:
    total_bulanan = filtered_data["Total Pengeluaran"].sum() if not filtered_data.empty else 0
    st.markdown(f"""
    <div style='padding: 20px; background-color: #4CAF50; color: white; text-align: center; font-size: 24px;'>
        <h2>Total Pengeluaran</h2>
        <h1>Rp {total_bulanan:,.0f}</h1>
    </div>
    """, unsafe_allow_html=True)

with col4:
    kategori_total = filtered_data.groupby("Kategori")["Total Pengeluaran"].sum().to_dict() if not filtered_data.empty else {}
    col_kat = st.columns(3)
    i = 0
    for kat in ["Makan", "Jajan", "Belanja", "Transportasi", "Laundry", "Lain - Lain"]:
        val = kategori_total.get(kat, 0)
        with col_kat[i % 3]:
            st.markdown(f"""
            <div style='padding: 10px; background-color: #2196F3; color: white; text-align: center; font-size: 16px;'>
                <h4>{kat}</h4>
                <h3>Rp {val:,.0f}</h3>
            </div>
            """, unsafe_allow_html=True)
        i += 1

col5, col6 = st.columns([2, 1])

with col5:
    st.subheader("Grafik Trend Pengeluaran")
    
    if not filtered_data.empty and "Total Pengeluaran" in filtered_data.columns:
        daily_total = filtered_data.groupby("Tanggal")["Total Pengeluaran"].sum().reset_index()

        if not daily_total.empty:
            # 🔹 Hitung batas atas dan bawah grafik (50% dari max & min)
            max_value = daily_total["Total Pengeluaran"].max()
            min_value = daily_total["Total Pengeluaran"].min()
            upper_limit = max_value * 1.5
            lower_limit = min_value * 0.5

            # 🔹 Format tanggal agar hanya menampilkan "DD-MMM"
            daily_total["Tanggal"] = pd.to_datetime(daily_total["Tanggal"]).dt.strftime('%d-%b')

            # 🔹 Buat Grafik
            trend_chart = px.line(
                daily_total, 
                x="Tanggal", 
                y="Total Pengeluaran", 
                title="Trend Pengeluaran", 
                markers=True, 
                text=daily_total["Total Pengeluaran"].apply(lambda x: f"Rp {x:,.0f}")
            )

            # 🔹 Atur tampilan label & batas grafik
            trend_chart.update_traces(textposition="top center")
            trend_chart.update_layout(
                yaxis=dict(
                    title="Total Pengeluaran",
                    tickformat="Rp ,.0f",  # Thousand Separator
                    range=[lower_limit, upper_limit]  # Batas atas & bawah
                ),
                xaxis=dict(
                    title="Tanggal",
                    tickangle=-45  # Miring agar mudah dibaca
                )
            )

            # 🔹 Tampilkan Grafik
            st.plotly_chart(trend_chart, use_container_width=True)

            # 🔹 Tampilkan Filter yang Diterapkan
            st.markdown(f"**Filter Tanggal:** {start_date.strftime('%d-%b-%Y')} s/d {end_date.strftime('%d-%b-%Y')}")

            # 🔹 Tampilkan Data dengan Format "Rp xxx.xxx"
            st.subheader("Total Pengeluaran Harian")
            st.dataframe(daily_total.style.format({"Total Pengeluaran": "Rp {:,.0f}"}))
        else:
            st.warning("⚠️ Tidak ada data setelah diproses untuk grafik trend.")
    else:
        st.warning("⚠️ Tidak ada data untuk grafik trend.")

with col6:
    st.subheader("Distribusi Pengeluaran")
    if not filtered_data.empty:
        pie_chart = px.pie(filtered_data, names="Kategori", values="Total Pengeluaran", title="Pengeluaran per Kategori")
        st.plotly_chart(pie_chart, use_container_width=True)

        top_5_pengeluaran = filtered_data.nlargest(5, "Total Pengeluaran")[["Tanggal", "Nama Pengeluaran", "Total Pengeluaran"]]
        st.subheader("🏆 Top 5 Pengeluaran Terbesar")
        st.dataframe(top_5_pengeluaran.style.format({"Total Pengeluaran": "Rp {:,.0f}"}))
    else:
        st.warning("⚠️ Tidak ada data untuk pie chart atau Top 5 pengeluaran.")
