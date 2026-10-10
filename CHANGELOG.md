# DermaScan batch Excel export

## Thay đổi

- Thêm endpoint `GET /api/upload-batches/<batch_id>/analysis.xlsx` cho Doctor phụ trách và Admin.
- Tạo workbook một sheet `ẢNH TRONG BATCH` với chín cột dữ liệu, giao diện xanh `#2BA149`, freeze pane và cấu hình in ngang A4.
- Nhúng thumbnail PNG của ảnh gốc và Grad-CAM từ file đã lưu; không chạy lại AI.
- Giữ nguyên hai endpoint CSV và tách phần truy vấn dữ liệu dùng chung để tránh trùng lặp.
- Đổi thao tác giao diện batch thành `Xuất Excel`, tải blob `.xlsx` và hiển thị lỗi phù hợp.
- Bảo vệ dữ liệu ô khỏi spreadsheet formula injection và ký tự XML không hợp lệ.
- Ảnh thiếu, hỏng, JPEG bị cắt hoặc không đọc được được thay bằng thông báo trong ô; một ảnh lỗi không làm hỏng toàn bộ export.
- Chuẩn hóa WEBP/JPEG/PNG thành thumbnail PNG tối đa 96 px trước khi nhúng để tương thích Excel và giảm kích thước workbook.
- Khai báo `openpyxl` và `Pillow` trong runtime database/API.

## File nguồn và test trong gói

- `README.md`
- `requirements.txt`
- `requirements-database.txt`
- `skin_cancer/webapp/routes/uploads.py`
- `skin_cancer/webapp/services/analysis_csv.py`
- `skin_cancer/webapp/services/analysis_export_data.py`
- `skin_cancer/webapp/services/analysis_excel.py`
- `skin_cancer/webapp/static/js/main.js`
- `skin_cancer/webapp/templates/index.html`
- `tests/test_analysis_csv.py`
- `tests/test_analysis_excel.py`
- `tests/test_auth_authorization.py`

Không có migration hay thay đổi database schema trong bản sửa này.
