from datetime import datetime, timedelta
from app.extensions import db
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.sale import Sale, SaleItem
from app.models.purchase import Purchase, PurchaseItem
from app.models.expense import Expense
from app.models.setting import Setting


def seed_all():
    seed_settings()
    seed_users()
    seed_categories()
    seed_products()
    seed_customers()
    seed_suppliers()
    db.session.commit()
    print("✅ تم تهيئة البيانات الأولية بنجاح.")


def seed_settings():
    defaults = {
        "shop_name": "زيوت وكماليات السيارات",
        "shop_name_en": "AutoParts Store",
        "shop_address": "طريق المطار، طرابلس، ليبيا",
        "shop_phone": "0912345678",
        "shop_email": "info@autoparts.ly",
        "currency": "د.ل",
        "invoice_footer": "شكراً لتعاملكم معنا",
        "vat_rate": "0",
        "low_stock_default": "5",
        "backup_keep_days": "30",
        "force_password_change": "1",
        "login_max_attempts": "5",
        "login_lockout_minutes": "15",
    }
    for key, value in defaults.items():
        if not Setting.query.filter_by(key=key).first():
            db.session.add(Setting(key=key, value=value))
    db.session.commit()


def seed_users():
    if User.query.count() > 0:
        return
    admin = User(
        username="admin",
        full_name="المدير العام",
        email="admin@autoparts.ly",
        role="admin",
        is_active=True,
        force_password_change=False,
    )
    admin.set_password("admin123")
    db.session.add(admin)

    cashier = User(
        username="cashier",
        full_name="أمين الصندوق",
        email="cashier@autoparts.ly",
        role="cashier",
        is_active=True,
        force_password_change=True,
    )
    cashier.set_password("cashier123")
    db.session.add(cashier)
    db.session.commit()


def seed_categories():
    if Category.query.count() > 0:
        return
    cats = [
        "زيوت المحركات",
        "فلاتر",
        "بطاريات",
        "إطارات",
        "إكسسوارات",
        "قطع غيار",
        "سوائل",
        "أدوات",
    ]
    for name in cats:
        db.session.add(Category(name=name))
    db.session.commit()


def seed_products():
    if Product.query.count() > 0:
        return

    cat_map = {c.name: c.id for c in Category.query.all()}

    products = [
        # زيوت المحركات
        dict(name="زيت موبيل 1 5W-30 4 لتر", barcode="6001001001", category_id=cat_map.get("زيوت المحركات"), purchase_price=42.0,  sale_price=55.0,  quantity=50, unit="علبة"),
        dict(name="زيت شل هيليكس 10W-40 4 لتر", barcode="6001001002", category_id=cat_map.get("زيوت المحركات"), purchase_price=35.0,  sale_price=45.0,  quantity=40, unit="علبة"),
        dict(name="زيت كاسترول GTX 20W-50 4 لتر", barcode="6001001003", category_id=cat_map.get("زيوت المحركات"), purchase_price=28.0,  sale_price=38.0,  quantity=60, unit="علبة"),
        dict(name="زيت توتال كوارتز 5W-40 4 لتر", barcode="6001001004", category_id=cat_map.get("زيوت المحركات"), purchase_price=38.0,  sale_price=50.0,  quantity=30, unit="علبة"),
        dict(name="زيت فالفولين 10W-30 4 لتر",    barcode="6001001005", category_id=cat_map.get("زيوت المحركات"), purchase_price=30.0,  sale_price=40.0,  quantity=25, unit="علبة"),
        # فلاتر
        dict(name="فلتر زيت تويوتا",  barcode="6001002001", category_id=cat_map.get("فلاتر"), purchase_price=5.0,  sale_price=9.0,   quantity=80, unit="قطعة"),
        dict(name="فلتر زيت هيونداي", barcode="6001002002", category_id=cat_map.get("فلاتر"), purchase_price=5.0,  sale_price=9.0,   quantity=70, unit="قطعة"),
        dict(name="فلتر هواء عام",    barcode="6001002003", category_id=cat_map.get("فلاتر"), purchase_price=8.0,  sale_price=14.0,  quantity=50, unit="قطعة"),
        dict(name="فلتر وقود عام",    barcode="6001002004", category_id=cat_map.get("فلاتر"), purchase_price=7.0,  sale_price=12.0,  quantity=40, unit="قطعة"),
        # سوائل
        dict(name="سائل فرامل DOT4 500ml",      barcode="6001007001", category_id=cat_map.get("سوائل"), purchase_price=6.0,  sale_price=10.0, quantity=35, unit="علبة"),
        dict(name="سائل تبريد أخضر 1 لتر",     barcode="6001007002", category_id=cat_map.get("سوائل"), purchase_price=4.0,  sale_price=7.0,  quantity=45, unit="علبة"),
        dict(name="ماء بطارية 1 لتر",           barcode="6001007003", category_id=cat_map.get("سوائل"), purchase_price=1.5,  sale_price=3.0,  quantity=60, unit="علبة"),
        # إكسسوارات
        dict(name="معطر سيارة شجرة خضراء",  barcode="6001005001", category_id=cat_map.get("إكسسوارات"), purchase_price=1.0,  sale_price=2.5,  quantity=100, unit="قطعة"),
        dict(name="غطاء مقود جلد",          barcode="6001005002", category_id=cat_map.get("إكسسوارات"), purchase_price=8.0,  sale_price=15.0, quantity=20,  unit="قطعة"),
        dict(name="كاميرا خلفية للسيارة",   barcode="6001005003", category_id=cat_map.get("إكسسوارات"), purchase_price=18.0, sale_price=30.0, quantity=15,  unit="قطعة"),
        # قطع غيار
        dict(name="شمعات بوجيه NGK",       barcode="6001006001", category_id=cat_map.get("قطع غيار"), purchase_price=3.0,  sale_price=6.0,  quantity=60, unit="قطعة"),
        dict(name="تيل فرامل أمامي عام",   barcode="6001006002", category_id=cat_map.get("قطع غيار"), purchase_price=12.0, sale_price=22.0, quantity=25, unit="طقم"),
        dict(name="مصفاة هواء كبيرة",      barcode="6001006003", category_id=cat_map.get("قطع غيار"), purchase_price=10.0, sale_price=18.0, quantity=20, unit="قطعة"),
    ]

    for p in products:
        db.session.add(Product(**p, low_stock_alert=5))
    db.session.commit()


def seed_customers():
    if Customer.query.count() > 0:
        return

    customers = [
        dict(name="محمد عمر البوسيف",    phone="0912345678", car_plate="124 طرابلس", car_model="تويوتا كامري 2020"),
        dict(name="خليفة سالم الورفلي",  phone="0923456789", car_plate="357 مصراتة", car_model="هيونداي سوناتا 2019"),
        dict(name="عبدالله علي القذافي", phone="0934567890", car_plate="489 بنغازي",  car_model="فورد فيوجن 2022"),
        dict(name="سالم مفتاح الزوي",    phone="0945678901", car_plate="612 سبها",    car_model="كيا أوبتيما 2018"),
        dict(name="أحمد فرج الترهوني",   phone="0956789012", car_plate="735 الزاوية", car_model="نيسان التيما 2021"),
        dict(name="مصطفى رجب العجيلي",   phone="0967890123", car_plate="841 درنة",    car_model="مرسيدس C200 2020"),
        dict(name="يوسف ناصر الفيتوري",  phone="0978901234", car_plate="963 غريان",   car_model="بي إم دبليو 520 2019"),
        dict(name="إبراهيم حسن الشريف",  phone="0989012345", car_plate="175 البيضاء", car_model="تويوتا كورولا 2021"),
    ]

    for c in customers:
        db.session.add(Customer(**c))
    db.session.commit()


def seed_suppliers():
    if Supplier.query.count() > 0:
        return

    suppliers = [
        dict(name="شركة الواحة للزيوت",      phone="0911111111", contact_person="علي محمد",    address="طرابلس — شارع الجمهورية"),
        dict(name="مؤسسة النجمة لقطع الغيار", phone="0922222222", contact_person="خالد سالم",   address="مصراتة — المنطقة الصناعية"),
        dict(name="شركة ليبيا أوتو",          phone="0933333333", contact_person="أحمد الورفلي", address="بنغازي — شارع التحرير"),
        dict(name="مستودعات الخليج للسيارات", phone="0944444444", contact_person="محمود فرج",   address="طرابلس — طريق المطار"),
    ]

    for s in suppliers:
        db.session.add(Supplier(**s))
    db.session.commit()