from collections import Counter
import os
import random
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Vietlott 6/55 Auto-Data", page_icon="🎱")

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
  """Bóc tách chuẩn xác bảng kết quả từ mã HTML của trang chính thống vietlott.vn."""
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


def thu_ket_noi_vietlott(df_cu):
  try:
    session = cffi_requests.Session(impersonate="chrome120")
    res = session.get(URL_VIETLOTT, timeout=15)
    res.raise_for_status()
    du_lieu_moi = boc_tach_html_vietlott(res.text)
    if du_lieu_moi:
      df_moi = pd.DataFrame(du_lieu_moi)
      df_tong = pd.concat([df_moi, df_cu], ignore_index=True)
      df_tong = df_tong.drop_duplicates(subset=["Ky"]).sort_values(
          by="Ky", ascending=False
      )
      luu_du_lieu(df_tong)
      return df_tong, len(du_lieu_moi), None
    return df_cu, 0, None
  except Exception as e:
    return df_cu, 0, str(e)


# --- GIAO DIỆN CHÍNH ---
st.title("🎱 Phân tích Vietlott Power 6/55")

df_kho = doc_du_lieu_luu_tru()
df_data, so_ky_moi, loi_403 = thu_ket_noi_vietlott(df_kho)

# Nếu server Mỹ bị Vietlott chặn IP 403, hiển thị công cụ nạp dữ liệu trực tiếp từ Vietlott
if loi_403:
  st.warning(
      "⚠️ Máy chủ Streamlit ở nước ngoài đang bị tường lửa `vietlott.vn` chặn"
      " IP (Lỗi 403)."
  )
  with st.expander(
      "📥 Nạp & Cập nhật dữ liệu thật từ Vietlott.vn (Không bị chặn IP)",
      expanded=df_data.empty,
  ):
    st.markdown(
        "1. Mở trang chính thống:"
        f" [vietlott.vn/winning-number-655]({URL_VIETLOTT}) trên trình duyệt"
        " điện thoại (dùng IP Việt Nam nên vào bình thường).\n2. Tải lên file"
        " dữ liệu `.csv` đã lưu hoặc dán mã nguồn trang web để hệ thống tự"
        " động bóc tách & cập nhật:"
    )

    file_tai_len = st.file_uploader(
        "Chọn file dữ liệu (.csv) hoặc trang web đã lưu (.html) từ Vietlott:",
        type=["csv", "html", "htm"],
    )
    if file_tai_len is not None:
      if file_tai_len.name.endswith(".csv"):
        df_upload = pd.read_csv(file_tai_len, dtype={"Ky": str})
        df_upload["Bo_so"] = df_upload["Bo_so"].apply(
            lambda x: [int(i) for i in str(x).split("-")]
        )
        df_data = (
            pd.concat([df_upload, df_data], ignore_index=True)
            .drop_duplicates(subset=["Ky"])
            .sort_values(by="Ky", ascending=False)
        )
        luu_du_lieu(df_data)
        st.success(f"✅ Đã nạp thành công **{len(df_data)} kỳ quay** vào kho!")
      else:
        noi_dung_html = file_tai_len.read().decode("utf-8", errors="ignore")
        ds_moi = boc_tach_html_vietlott(noi_dung_html)
        if ds_moi:
          df_moi = pd.DataFrame(ds_moi)
          df_data = (
              pd.concat([df_moi, df_data], ignore_index=True)
              .drop_duplicates(subset=["Ky"])
              .sort_values(by="Ky", ascending=False)
          )
          luu_du_lieu(df_data)
          st.success(
              f"✅ Đã bóc tách và cập nhật thêm **{len(ds_moi)} kỳ quay** từ"
              " file trang web Vietlott!"
          )

# --- PHÂN TÍCH DỮ LIỆU ---
if not df_data.empty:
  col_info, col_dl = st.columns([2, 1])
  with col_info:
    st.info(
        f"📊 Kho dữ liệu hiện có: **{len(df_data)} kỳ quay** (Mới nhất:"
        f" **#{df_data.iloc[0]['Ky']}** - {df_data.iloc[0]['Ngay']})"
    )
  with col_dl:
    csv_bytes = df_data.to_csv(index=False, encoding="utf-8-sig").encode(
        "utf-8-sig"
    )
    st.download_button(
        "📥 Tải file Data (.csv)",
        csv_bytes,
        "vietlott_data.csv",
        "text/csv",
        use_container_width=True,
    )

  tat_ca_so = [so for bo in df_data["Bo_so"] for so in bo]
  tan_suat = Counter(tat_ca_so)
  for i in range(1, 56):
    tan_suat.setdefault(i, 0)

  df_tan_suat = pd.DataFrame(
      [{"Số": f"{k:02d}", "Số lần về": v} for k, v in tan_suat.items()]
  ).sort_values(by="Số lần về", ascending=False)

  c1, c2 = st.columns(2)
  with c1:
    st.subheader("🔥 Top 10 số về nhiều nhất")
    st.dataframe(df_tan_suat.head(10), hide_index=True, use_container_width=True)
  with c2:
    st.subheader("❄️ Top 10 số về ít nhất")
    st.dataframe(df_tan_suat.tail(10), hide_index=True, use_container_width=True)

  st.divider()
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

  with st.expander(f"📋 Xem toàn bộ kho dữ liệu ({len(df_data)} kỳ quay)"):
    df_hien_thi = df_data.copy()
    df_hien_thi["Bo_so"] = df_hien_thi["Bo_so"].apply(
        lambda lst: " - ".join([f"{s:02d}" for s in lst])
    )
    st.dataframe(df_hien_thi, hide_index=True, use_container_width=True)
