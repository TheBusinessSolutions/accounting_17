import polib
from deep_translator import GoogleTranslator
import time
import io

def clean_and_translate():
    input_file = 'ks_dynamic_financial_report.po'
    output_file = 'ar.po'
    
    print("جاري فحص وتنظيف ملف الترجمة...")
    
    try:
        # 1. تنظيف الملف من أي محارف مخفية في السطر الأول
        with open(input_file, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        # التأكد من أن الملف يبدأ بتعليق أو msgid
        clean_content = "".join(lines)
        
        # 2. تحميل محتوى الملف المنظف إلى polib
        po = polib.pofile(clean_content)
        translator = GoogleTranslator(source='en', target='ar')
        
        print(f"تم فتح الملف بنجاح. إجمالي الأسطر: {len(po)}")
        print("بدء الترجمة... (سيتم تحديثك كل 50 سطر)")

        for i, entry in enumerate(po):
            if not entry.msgstr:
                try:
                    # ترجمة النص
                    entry.msgstr = translator.translate(entry.msgid)
                    # تأخير بسيط جداً لتجنب الحظر
                    if i % 15 == 0:
                        time.sleep(0.1)
                except Exception:
                    continue
            
            if i % 50 == 0:
                print(f"تمت معالجة {i} سطر...")

        # 3. حفظ النتيجة
        po.save(output_file)
        print("\n" + "="*30)
        print("تمت العملية بنجاح!")
        print(f"الملف الجديد الجاهز لأودو هو: {output_file}")
        print("="*30)

    except Exception as e:
        print(f"فشل تنظيف أو ترجمة الملف: {e}")

if __name__ == "__main__":
    clean_and_translate()