from collections import Counter
import os
import random
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Vietlott 6/55 Tự Động 100%", page_icon="🎱")

FILE_DATA = "vietlott_data.csv"
URL_VIETLOTT = (
    "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-655"
)


def doc_du_lieu_luu_tru():
  if os.path.exists(FILE_DATA):
    try:
      df = pd.read_csv(FILE_DATA, dtype={"Ky": str})
      df["Bo_so"] = df["Bo_so"].apply(
          lambda x: [int(i) for i in str(x).split("-")]
      )
      return df
    except Exception:
      return pd.DataFrame()
  return pd.DataFrame()


def luu_du_lieu(df):
  df_save = df.copy()
  df_save["Bo_so"] = df_save["Bo_so"].apply(
      lambda lst: "-".join([f"{int(i):02d}" for i in lst])
  )
  df_save.to_csv(FILE_DATA, index=False, encoding="utf-8-sig")


def boc_tach_html_vietlott(html_text):
  soup = BeautifulSoup(html_text, "html.parser")
  ket_qua = []
  rows = soup.select("table tbody tr")
  for row in rows:
    cols = row.find_all("td")
    if len(cols) >= 3:
      ngay = cols[0].get_text(strip=True)
      ky = cols[1].get_text(strip=True)
      bong = [
          int(b.get_text(strip=True))
          for b in cols[2].select("span.bong_tron")
          if b.get_text(strip=True).isdigit()
      ]
      if len(bong) >= 6:
        ket_qua.append({
            "Ngay": ngay,
            "Ky": ky,
            "Bo_so": sorted(bong[:6]),
            "Dac_biet": bong[6] if len(bong) > 6 else None,
        })
  return ket_qua


# --- GIAO DIỆN & TỰ ĐỘNG ĐỒNG BỘ QUA IP ĐIỆN THOẠI ---
st.title("🎱 Tự Động Cập Nhật & Phân Tích Vietlott 6/55")

df_data = doc_du_lieu_luu_tru()

# Dùng trình duyệt của chính điện thoại anh (IP Việt Nam) để kéo dữ liệu ngầm từ vietlott.vn
js_fetch_code = f"""
async () => {{
    try {{
        // Dùng proxy trung gian miễn phí hoặc fetch trực tiếp từ trình duyệt Việt Nam
        const res = await fetch("https://api.allorigins.win/get?url=" + encodeURIComponent("{URL_VIETLOTT}"));
        const data = await res.json();
        return data.contents;
    }} catch (e) {{
        return "ERROR:" + e.toString();
    }}
}}
"""

with st.spinner("🔄 Đang tự động đồng bộ dữ liệu thật từ vietlott.vn..."):
  html_tu_dong = streamlit_js_eval(
      js_expressions=js_fetch_code, key="auto_fetch_vietlott"
  )

if html_tu_dong and not str(html_tu_dong).startswith("ERROR:"):
  ds_moi = boc_tach_html_vietlott(html_tu_dong)
  if ds_moi:
    df_moi = pd.DataFrame(ds_moi)
    so_ky_truoc = len(df_data)
    df_data = (
        pd.concat([df_moi, df_data], ignore_index=True)
        .drop_duplicates(subset=["Ky"])
        .sort_values(by="Ky", ascending=False)
    )
    luu_du_lieu(df_data)
    so_ky_them = len(df_data) - so_ky_truoc
    if so_ky_them > 0:
      st.success(
          f"🎉 Đã tự động cập nhật thêm **{so_ky_them} kỳ quay mới** từ"
          f" vietlott.vn! Tổng kho: **{len(df_data)} kỳ**."
      )
    else:
      st.info(
          f"✅ Dữ liệu đã đồng bộ tự động mới nhất (**{len(df_data)} kỳ** | Kỳ"
          f" gần nhất: **#{df_data.iloc[0]['Ky']}** ngày"
          f" {df_data.iloc[0]['Ngay']})."
      )

# --- HIỂN THỊ KẾT QUẢ PHÂN TÍCH NGAY LẬP TỨC ---
if not df_data.empty:
  tat_ca_so = [so for bo in df_data["Bo_so"] for so in bo]
  tan_suat = Counter(tat_ca_so)
  for i in range(1, 56):
    tan_suat.setdefault(i, 0)

  df_tan_suat = pd.DataFrame([
      {
          "Số": f"{k:02d}",
          "Số lần về": v,
          "Tỷ lệ (%)": round(v / len(df_data) * 100, 1),
      }
      for k, v in tan_suat.items()
  ]).sort_values(by="Số lần về", ascending=False)

  c1, c2 = st.columns(2)
  with c1:
    st.subheader("🔥 Top 10 số về nhiều nhất")
    st.dataframe(df_tan_suat.head(10), hide_index=True, use_container_width=True)
  with c2:
    st.subheader("❄️ Top 10 số về ít nhất")
    st.dataframe(df_tan_suat.tail(10), hide_index=True, use_container_width=True)

  st.divider()
  st.subheader("🎯 Xuất bộ số theo dữ liệu thực tế từ Vietlott")
  so_ve = st.slider("Số lượng bộ vé muốn tạo:", 1, 10, 3)

  if st.button("🚀 Chạy phân tích & Tạo bộ số", type="primary"):
    cac_so = list(range(1, 56))
    trong_so = [tan_suat[s] + 1 for s in cac_so]
    for idx in range(1, so_ve + 1):
      bo_chon = set()
      while len(bo_chon) < 6:
        bo_chon.add(random.choices(cac_so, weights=trong_so, k=1)[0])
      chuoi_so = "  -  ".join([f"**{s:02d}**" for s in sorted(bo_chon)])
      st.success(f"Bộ số {idx}:   {chuoi_so}")

  with st.expander(f"📋 Bảng kết quả gốc từ vietlott.vn ({len(df_data)} kỳ)"):
    df_hien_thi = df_data.copy()
    df_hien_thi["Bo_so"] = df_hien_thi["Bo_so"].apply(
        lambda lst: " - ".join([f"{s:02d}" for s in lst])
    )
    st.dataframe(df_hien_thi, hide_index=True, use_container_width=True)
elif html_tu_dong is None:
  st.info("⏳ Đang khởi tạo kết nối tự động tới máy chủ Vietlott, vui lòng đợi 2–3 giây...")
else:
  st.error(
      "Không thể kết nối tự động lúc này. Anh thử tải lại trang (F5) để trình"
      " duyệt đồng bộ lại nhé."
  )