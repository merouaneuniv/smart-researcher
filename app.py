import streamlit as st
import requests
import json
import io
import sqlite3
import pandas as pd
from datetime import datetime
from docx import Document
from groq import Groq
# --- CORRECTION 1: Import correct pour Google Generative AI ---
from google import genai
from pypdf import PdfReader

# ==========================================
# 1. إعدادات الصفحة والتصميم المتجاوب
# ==========================================
st.set_page_config(
    page_title="محطة عمل الباحث الذكي - ANRN",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
    
    .stApp, .stMarkdown, p, h1, h2, h3, h4, label, input, textarea, select {
        font-family: 'Tajawal', sans-serif !important;
        direction: rtl !important;
        text-align: right !important;
    }
    
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem !important; }
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.15rem !important; }
        .stButton>button { font-size: 0.85rem !important; padding: 0.5rem !important; }
    }
    
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. إدارة الجلسة ودالة التفريغ (Clean Function)
# ==========================================
if "form_title" not in st.session_state:
    st.session_state["form_title"] = "أثر تطبيقات الذكاء الاصطناعي على جودة التعليم العالي والحوكمة الأكاديمية"
if "form_field" not in st.session_state:
    st.session_state["form_field"] = "علوم التسيير - إدارة المنظمات"

def reset_all_fields():
    st.session_state["form_title"] = ""
    st.session_state["form_field"] = ""
    if "results" in st.session_state:
        del st.session_state["results"]
    if "current_log_id" in st.session_state:
        del st.session_state["current_log_id"]
    st.rerun()

# ==========================================
# 3. قاعدة بيانات المطور
# ==========================================
def init_db():
    conn = sqlite3.connect("smart_researcher_logs.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS research_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            researcher_name TEXT,
            role TEXT,
            affiliation TEXT,
            email TEXT,
            phone TEXT,
            title TEXT,
            field TEXT,
            language TEXT,
            feedback TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_research_log(data):
    try:
        conn = sqlite3.connect("smart_researcher_logs.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO research_logs (
                timestamp, researcher_name, role, affiliation, email, phone, 
                title, field, language, feedback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("name", ""),
            data.get("role", ""),
            data.get("affiliation", ""),
            data.get("email", ""),
            data.get("phone", ""),
            data.get("title", ""),
            data.get("field", ""),
            data.get("language", ""),
            ""
        ))
        log_id = c.lastrowid
        conn.commit()
        conn.close()
        return log_id
    except Exception as e:
        st.error(f"خطأ في حفظ السجل: {e}")
        return None

def update_feedback(log_id, feedback_text):
    try:
        conn = sqlite3.connect("smart_researcher_logs.db")
        c = conn.cursor()
        c.execute("UPDATE research_logs SET feedback = ? WHERE id = ?", (feedback_text, log_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"خطأ في تحديث الملاحظات: {e}")
        return False

init_db()

# ==========================================
# 4. واجهة المستخدم الرئيسية
# ==========================================
st.title("🏛️ محطة عمل الباحث الذكي المتكاملة")
st.caption("المنظومة الأكاديمية للزحف المتوازي والتحكيم المقارن متعدد النماذج (ANRN Deep Research)")

with st.expander("🔐 إعدادات المفاتيح السحابية (Groq / Gemini / Semantic)", expanded=False):
    st.warning("⚠️ لا تقم بمشاركة هذه المفاتيح أو حفظها في الكود المصدري. استخدم secrets.toml للإنتاج.")
    col_k1, col_k2, col_k3 = st.columns(3)
    with col_k1:
        # --- SÉCURITÉ : Utilisation de st.secrets pour cacher les clés ---
        groq_key = st.text_input("مفتاح Groq API Key:", type="password", value=st.secrets.get("GROQ_API_KEY", "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"))
    with col_k2:
        gemini_key = st.text_input("مفتاح Google Gemini Key:", type="password", value=st.secrets.get("GEMINI_API_KEY", "AQ.Ab8RN6JI7XuW1iL9Iy1mvC-eTpI1je3WDSB1A9Q1nlpJJylNUQ"))
    with col_k3:
        s2_key = st.text_input("مفتاح Semantic Scholar:", type="password", value=st.secrets.get("S2_API_KEY", "s2k-JFm8ATLqSu5rLk2Lcx3HdDhJ7RRbjIM8BiPt"))

with st.expander("👤 بطاقة تعريف الباحث (توثيق بيانات صاحب البحث)", expanded=True):
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        res_name = st.text_input("الاسم واللقب *", value="د. مراد مروان")
        res_role = st.selectbox("الصفة الأكاديمية *", ["أستاذ جامعي / باحث دائم", "طالب دكتوراه", "طالب ماستر / تخرج", "باحث حر / مهني"], index=0)
        res_affil = st.text_input("الانتماء المؤسسي / الجامعة / المخبر *", value="المركز الجامعي مغنية / مخبر الحوكمة")
    with col_p2:
        res_email = st.text_input("البريد الإلكتروني *", value="researcher@univ.dz")
        res_phone = st.text_input("رقم الهاتف (اختياري)", value="")

st.markdown("### 🎛️ تخصيص موضوع ومنصات البحث")
col1, col2 = st.columns(2)
with col1:
    research_title = st.text_input("عنوان البحث أو الإشكالية الرئيسية *:", key="form_title")
with col2:
    research_field = st.text_input("الميدان والتخصص الأكاديمي:", key="form_field")

col_opt1, col_opt2 = st.columns(2)
with col_opt1:
    selected_language = st.selectbox("🌐 لغة صياغة التقرير والمسودة الأكاديمية:", ["العربية", "English", "Français"], index=0)
# --- CORRECTION : Le bloc manquant et la chaîne de caractères corrigés ---
with col_opt2:
