import asyncio
import asyncpg

async def run_fix():
    print("جاري اختراق قاعدة البيانات...")
    try:
        # الاتصال المباشر بقاعدة بيانات EPPNE
        conn = await asyncpg.connect('postgresql://eppne:eppne123@localhost:5433/eppne')
        
        # تنفيذ أمر التصفير (الأرض المحروقة) وإعادة العداد إلى 1
        await conn.execute('TRUNCATE TABLE academy_tenants RESTART IDENTITY CASCADE;')
        
        print("🚀 تمت العملية بنجاح: تم مسح الكيانات المعلقة وإعادة معايرة العداد إلى 1!")
        await conn.close()
    except Exception as e:
        print(f"❌ حدث خطأ أثناء الاختراق: {e}")

if __name__ == "__main__":
    asyncio.run(run_fix())