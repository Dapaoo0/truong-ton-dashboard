# Project Rules — Banana Tracker Frontend

---

## ⚠️ Framework Warning: Next.js 16

**This is NOT the Next.js you know.**

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Before writing any Next.js code:
- Read the relevant guide in `node_modules/next/dist/docs/`.
- Always use **Context7 MCP** to look up current API signatures.
- Heed all deprecation notices.

---

## Quy tắc Skills

Tuyệt đối luôn đọc thư mục `.agent/skills/` trước khi bắt đầu thực hiện bất cứ tác vụ nào để đảm bảo tuân thủ đúng các quy trình và quy tắc phát triển (development standards) của dự án. Đặc biệt, phải đọc kĩ từng skill để xem xét và ứng dụng tối đa các skill phù hợp cho tác vụ đang làm, không được bỏ sót hay chỉ dùng một cấu hình duy nhất.

---

## Quy tắc Tài liệu (docs/)

Luôn phải đảm bảo duy trì và cập nhật các file markdown sau đây trong thư mục `docs/`:

| File | Nội dung |
|------|---------|
| `changelog.md` | Lưu lại những thay đổi đã thực hiện |
| `tech_stack.md` | Danh sách công cụ, framework và công nghệ đang dùng |
| `findings.md` | Khám phá, lưu ý, và bài học kinh nghiệm |
| `command.md` | Tóm tắt yêu cầu/chỉ thị từ người dùng |
| `schema.md` | Cấu trúc dữ liệu, các trường DB và ý nghĩa |
| `codebase_summary.md` | Ý nghĩa hàm, mục đích và luồng hoạt động chính |

---

## Quy tắc MCP (Model Context Protocol)

| Tình huống | MCP ưu tiên |
|-----------|-------------|
| Thao tác với GitHub (commit, PR, issues) | **GitHub MCP** |
| Thao tác với database (query, schema, migration) | **Supabase MCP** |
| Tra cứu API, cú pháp framework, documentation | **Context7 MCP** |

---

## Quy tắc Báo cáo (Task Report)

Mỗi khi hoàn thành và kết thúc một tác vụ bàn giao cho người dùng, luôn luôn đóng lại bằng một đoạn thông báo ngắn gọn ghi rõ những **Skills** và **MCPs** nào đã được sử dụng.
