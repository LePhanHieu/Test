# Hướng dẫn cài đặt bản sửa Excel export

## 1. Sao lưu

Sao lưu các file đang dùng có đường dẫn trùng với danh sách dưới đây. Không cần thay database, model, checkpoint, ảnh upload hoặc thư mục `instance/`.

Các file cần chép/thay thế, tính từ thư mục gốc project:

- `README.md`
- `requirements.txt`
- `requirements-database.txt`
- `skin_cancer/webapp/routes/uploads.py`
- `skin_cancer/webapp/services/analysis_csv.py`
- `skin_cancer/webapp/services/analysis_export_data.py` (mới)
- `skin_cancer/webapp/services/analysis_excel.py` (mới)
- `skin_cancer/webapp/static/js/main.js`
- `skin_cancer/webapp/templates/index.html`
- `tests/test_analysis_csv.py`
- `tests/test_analysis_excel.py` (mới)
- `tests/test_auth_authorization.py`
- `CHANGELOG.md` (tài liệu bàn giao)
- `INSTALL_GUIDE.md` (tài liệu bàn giao)

## 2. Chép file

Giải nén gói tại thư mục gốc project để giữ nguyên cấu trúc tương đối. Không chép `.env`, database, checkpoint hoặc dữ liệu bệnh nhân từ môi trường khác.

## 3. Cài dependency

Windows CMD:

```bat
.venv\Scripts\activate
python -m pip install -r requirements-database.txt
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -r requirements-database.txt
```

Nếu chạy cả AI runtime, dùng `python -m pip install -r requirements.txt`.

## 4. Kiểm tra

```bash
python -m pytest -q
python -m flask --app skin_cancer.webapp.database_app db current
python -m flask --app skin_cancer.webapp.database_app db check
```

Không tạo migration mới cho thay đổi này.

## 5. Chạy và kiểm tra chức năng

API/database app:

```bash
python -m flask --app skin_cancer.webapp.database_app run --host 127.0.0.1 --port 5000
```

AI app, khi dependency và checkpoint đã có:

```bash
python -m skin_cancer.webapp.app
```

Đăng nhập bằng Doctor được giao Case hoặc Admin, mở batch đã phân tích và chọn `Xuất Excel`. Có thể kiểm tra trực tiếp endpoint `GET /api/upload-batches/<batch_id>/analysis.xlsx`. File phải có đúng một sheet `ẢNH TRONG BATCH`; ảnh thiếu/hỏng phải hiện thông báo thay vì làm tải file thất bại.

## 6. Rollback

Dừng ứng dụng, khôi phục các file đã sao lưu ở bước 1, cài lại manifest dependency cũ nếu cần rồi khởi động lại. Database không cần rollback vì bản sửa không thay đổi schema hay dữ liệu.
