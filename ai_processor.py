import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY bulunamadı (.env kontrol).")

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = OpenAI(api_key=API_KEY)

SYSTEM_INSTRUCTIONS = """
Sen bir veritabanı tasarımı asistanısın.
Kullanıcının verdiği proje bilgilerinden istenen çıktıyı üret.
Çıktıyı açık başlıklar ve maddeler halinde yaz.
Gereksiz açıklama yapma, direkt sonucu ver.
""".strip()


def _project_context(p: dict) -> str:
    return f"""
PROJE BAŞLIĞI: {p['title']}
DOMAIN: {p['domain']}
PRIMARY ENTITY: {p['primary_entity']}
CONSTRAINT / RULE: {p['constraints_text']}
ADVANCED FEATURE: {p['advanced_feature']}
SECURITY / ACCESS CONTROL: {p['security_access']}
REPORTING REQUIREMENT: {p['reporting_requirement']}
COMMON TASKS: {p['common_tasks']}
""".strip()


PROMPT_TEMPLATES = {
"business_rules": """
Aşağıdaki proje bilgilerine göre Business Rules üret ve SADECE tablo olarak ver.

ZORUNLU FORMAT:
- Kolonlar SIRASIYLA şu olacak:
  BR-ID | Tür | Kural | ER Etkisi | Uygulama İpucu | Gerekçe
- BR-ID formatı: BR-01, BR-02, ... (en az 12 kural)
- Tür alanı: "Yapısal" veya "Davranışsal" veya "Güvenlik" (bu 3’ünden biri)
- ER Etkisi: ilişki/kısıt etkisini yaz (örn: Kullanıcı (1)-Abonelik (N), UNIQUE, CHECK, M:N ara tablo vb.)
- Uygulama İpucu: MySQL’de nasıl uygulanır (UNIQUE, FK, CHECK, trigger, view vs.)
- Ekstra açıklama, başlık, madde işareti ASLA yazma. Sadece tablo.

=== PROJE ===
{ctx}
=== ÇIKTI ===
""",

    "er_tables": """
Aşağıdaki proje bilgilerine göre ER Tablosu Oluştur.
- Önce entity listesi
- Sonra her tablo için: PK, önemli alanlar, FK
- İlişkileri (1-N, N-N) belirt
- En az 7-12 tablo hedefle (domain’e göre)
-Sadece Tablo
-Ekstra açıklama, başlık, madde işareti ASLA yazma. Sadece tablo.

=== PROJE ===
{ctx}
=== ÇIKTI ===
""",
    "missing_rules": """
Aşağıdaki proje bilgilerine göre eksik/atlanan kuralları (missing rules) tespit et.
- En az 10 madde öner
- Maddeleri 3 başlık altında grupla: Data Integrity, Process/Workflow, Security/Access
- Her madde “kural + kısa gerekçe” şeklinde olsun

=== PROJE ===
{ctx}
=== ÇIKTI ===
""",
    "normalization": """
Aşağıdaki proje için 0NF→1NF→2NF→3NF normalizasyon çıktısı üret ve Sadece TABLO olarak ver.
-Sadece Tablo üret
- Başlangıçta örnek ham tablo(lar) varsay
- 1NF/2NF/3NF’de oluşan tabloları tek tek yaz
- Her adımda “neden”i 1-2 satırla açıkla
- En sonda “Final 3NF Şema”yı tablo tablo özetle
- sadece tablo üret

=== PROJE ===
{ctx}
=== ÇIKTI ===
""",
"er_plantuml": """
Aşağıdaki proje bilgilerine göre PlantUML ER diyagramı üret.

ZORUNLU KURALLAR:
- Çıktı SADECE PlantUML kod bloğu olsun: ```plantuml ... ```
- İlk satır @startuml, son satır @enduml olsun.
- Hiçbir satırın sonunda virgül (,) OL-MA-SIN.
- Alanlar listesinde virgül kullanma. Her alan ayrı satır olacak.
- İlişkilerde virgül kullanma.
- entity tanımı şu formatta olacak:

entity TableName {{
  *id : INT <<PK>>
  user_id : INT <<FK>>
  name : VARCHAR
}}

- İlişki formatı örnek:
User ||--o{{ Subscription : has
Content }}o--o{{ Platform : available_on

=== PROJE ===
{ctx}
=== ÇIKTI ===
""",

    "sql_script": """
Aşağıdaki proje için MySQL SQL script üret.
- CREATE TABLE’lar (PK/FK/UNIQUE mümkünse CHECK)
- Örnek INSERT (her tabloya 2-3 kayıt)
- En az 1 trigger veya 1 stored procedure (constraint/rule’a uygun)
- Role-based access için örnek kullanıcı/GRANT

=== PROJE ===
{ctx}
=== ÇIKTI ===
""",
    "report": """
Aşağıdaki proje için raporlama sorguları üret.
- reporting requirement’a uygun 5 rapor sorgusu
- En az 1 tanesi JOIN + GROUP BY içersin
- En az 1 tanesi VIEW mantığıyla olsun (MySQL VIEW)

=== PROJE ===
{ctx}
=== ÇIKTI ===
""",
}


def run_project_action(project_row: dict, action_key: str, temperature: float = 0.2):
    """
    Returns: (prompt_text, output_text, model_used)
    """
    if action_key not in PROMPT_TEMPLATES:
        raise ValueError(f"Bilinmeyen action_key: {action_key}")

    ctx = _project_context(project_row)
    prompt_text = PROMPT_TEMPLATES[action_key].format(ctx=ctx)

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt_text},
        ],
        temperature=temperature,
    )

    out = (resp.choices[0].message.content or "").strip()
    if not out:
        raise RuntimeError("OpenAI boş çıktı döndürdü.")
    return prompt_text, out, MODEL

def process_text_with_ai(input_text: str) -> str:
    if not input_text.strip():
        raise ValueError("AI'ye gönderilecek metin boş.")

    prompt = (
        "Aşağıdaki dokümanı proje yönergesine göre tamamla.\n"
        "Çıktıyı düzenli başlıklar ve maddelerle ver.\n\n"
        "=== DOKÜMAN ===\n"
        f"{input_text}\n"
        "=== SON ==="
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    output = response.choices[0].message.content
    if not output or not output.strip():
        raise RuntimeError("OpenAI boş çıktı döndürdü.")

    return output.strip()

