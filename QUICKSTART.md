# Quickstart — HR Assistant Demo (Lab 3)

## Yêu cầu
- Python 3.10+
- API key của **Gemini** (khuyến nghị, miễn phí) hoặc **OpenAI**

---

## 1. Cài đặt môi trường

```bash
# Tạo virtual environment (tùy chọn nhưng nên làm)
python -m venv lab3_env
# Windows
lab3_env\Scripts\activate
# macOS / Linux
source lab3_env/bin/activate

# Cài dependencies
pip install -r requirements.txt
```

> Bỏ qua `llama-cpp-python` nếu không dùng local model — gói này nặng và cần compiler.
> ```bash
> pip install openai google-genai python-dotenv pydantic requests pytest streamlit
> ```

---

## 2. Cấu hình API key

```bash
# Sao chép file cấu hình mẫu
cp .env.example .env   # Windows: copy .env.example .env
```

Mở `.env` và điền API key:

```env
# Dùng Gemini (miễn phí tại aistudio.google.com)
GEMINI_API_KEY=your_gemini_api_key_here
DEFAULT_PROVIDER=google
DEFAULT_MODEL=gemini-1.5-flash

# --- HOẶC dùng OpenAI ---
# OPENAI_API_KEY=your_openai_api_key_here
# DEFAULT_PROVIDER=openai
# DEFAULT_MODEL=gpt-4o
```

---

## 3. Chạy demo

```bash
streamlit run app.py
```

Trình duyệt sẽ tự mở tại `http://localhost:8501`.

---

## 4. Thử nghiệm

Trong sidebar chọn chế độ:
- **ReAct Agent** — tra cứu dữ liệu thực qua tools, hiển thị từng bước suy luận
- **Chatbot** — chỉ dùng kiến thức chung của LLM (không có tools)

Câu hỏi mẫu để so sánh hai chế độ:

| Câu hỏi | Chatbot | ReAct Agent |
|---------|---------|-------------|
| "Lương tháng này của EMP004 là bao nhiêu?" | Bịa số / không biết | Tính đúng từ dữ liệu |
| "EMP003 còn bao nhiêu ngày phép?" | Không biết | Tra cứu và trả lời chính xác |
| "Cho EMP002 nghỉ 3 ngày" | Không thực hiện được | Kiểm tra phép + duyệt đơn |

Danh sách nhân viên: **EMP001 → EMP005** (xem sidebar để biết chi tiết).

---

## 5. (Tùy chọn) Chạy với Local Model — không cần API key

1. Tải model **Phi-3-mini-4k-instruct-q4.gguf** (~2.2 GB) từ [Hugging Face](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)
2. Tạo thư mục `models/` và đặt file `.gguf` vào đó
3. Cập nhật `.env`:
   ```env
   DEFAULT_PROVIDER=local
   LOCAL_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf
   ```
4. Cài thêm: `pip install llama-cpp-python`
5. Chạy lại: `streamlit run app.py`
