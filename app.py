import time
import random

def call_gemini_with_fallback(api_key, prompt, sources_footer):
    """
    يحاول عدة نماذج Gemini.
    عند ظهور 503/429 ينتظر ثم يعيد المحاولة،
    وإذا بقي النموذج مزدحماً ينتقل إلى النموذج التالي.
    """

    client = genai.Client(api_key=api_key)

    models = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-2.5-flash",
    ]

    max_retries = 3
    last_error = None

    for model_name in models:

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                text = response.text or ""

                if not text.strip():
                    raise RuntimeError(
                        f"النموذج {model_name} أعاد استجابة فارغة."
                    )

                return (
                    f"### 🤖 النموذج المستخدم: `{model_name}`\n\n"
                    + text
                    + sources_footer
                )

            except Exception as exc:
                last_error = exc
                error_text = str(exc)

                transient_error = (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                    or "high demand" in error_text.lower()
                    or "overloaded" in error_text.lower()
                    or "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                )

                if transient_error:
                    if attempt < max_retries - 1:
                        # 2s → 4s → ... + jitter
                        wait_time = (2 ** (attempt + 1)) + random.uniform(0, 1.5)

                        time.sleep(wait_time)
                        continue

                    # فشل النموذج بعد المحاولات:
                    # الانتقال إلى النموذج التالي.
                    break

                # الخطأ ليس مؤقتاً، مثل مفتاح API غير صالح.
                return (
                    "❌ خطأ Gemini غير مؤقت:\n\n"
                    f"`{error_text}`"
                )

    return (
        "⚠️ جميع نماذج Gemini غير متاحة مؤقتاً.\n\n"
        "تمت تجربة:\n"
        "- Gemini 3.6 Flash\n"
        "- Gemini 3.5 Flash\n"
        "- Gemini 2.5 Flash\n\n"
        f"آخر خطأ: `{last_error}`\n\n"
        "يمكنك الاستمرار باستخدام نتائج Groq والمحكم المنهجي "
        "ثم إعادة تجربة Gemini لاحقاً."
    )
