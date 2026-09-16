__version__ = "2.0.0"

import os
import sqlite3
import uuid
from datetime import datetime, timedelta

from kivy.app import App
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.utils import platform
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup


SHOP_NAME = "MURALI KRISHNA ELECTRICAL"
SHOP_PHONE = "9866089242"
SHOP_ADDRESS = "MAIN ROAD YELLANDU"
GST_RATE = 18.0


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class DB:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.init()

    def q(self, sql, args=(), one=False):
        cur = self.con.cursor()
        cur.execute(sql, args)
        rows = cur.fetchone() if one else cur.fetchall()
        self.con.commit()
        return rows

    def init(self):
        self.q("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT, brand TEXT NOT NULL,
            model TEXT NOT NULL, hp TEXT, phase TEXT, voltage TEXT,
            purchase_price REAL DEFAULT 0, selling_price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0, warranty_months INTEGER DEFAULT 12,
            created_at TEXT)""")
        self.q("""CREATE TABLE IF NOT EXISTS motors(
            id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER,
            serial_number TEXT UNIQUE NOT NULL, status TEXT DEFAULT 'IN STOCK',
            customer_name TEXT, customer_phone TEXT, bill_no TEXT,
            warranty_start TEXT, warranty_end TEXT, created_at TEXT)""")
        self.q("""CREATE TABLE IF NOT EXISTS customers(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT UNIQUE,
            address TEXT, created_at TEXT)""")
        self.q("""CREATE TABLE IF NOT EXISTS suppliers(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT,
            address TEXT, gst_number TEXT, created_at TEXT)""")
        self.q("""CREATE TABLE IF NOT EXISTS bills(
            id INTEGER PRIMARY KEY AUTOINCREMENT, bill_no TEXT UNIQUE,
            customer_name TEXT, customer_phone TEXT, subtotal REAL,
            cgst REAL, sgst REAL, gst REAL, total REAL,
            payment TEXT, created_at TEXT)""")
        self.q("""CREATE TABLE IF NOT EXISTS bill_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT, bill_id INTEGER,
            product_id INTEGER, motor_id INTEGER, serial_number TEXT,
            product_name TEXT, qty INTEGER, price REAL, total REAL)""")
        self.q("""CREATE TABLE IF NOT EXISTS purchases(
            id INTEGER PRIMARY KEY AUTOINCREMENT, supplier_name TEXT,
            invoice_no TEXT, total REAL, created_at TEXT)""")
        self.q("""CREATE TABLE IF NOT EXISTS returns(
            id INTEGER PRIMARY KEY AUTOINCREMENT, bill_no TEXT,
            serial_number TEXT, reason TEXT, refund REAL, created_at TEXT)""")
        self.q("""CREATE TABLE IF NOT EXISTS repairs(
            id INTEGER PRIMARY KEY AUTOINCREMENT, serial_number TEXT,
            customer_name TEXT, phone TEXT, issue TEXT,
            status TEXT, amount REAL, created_at TEXT)""")
        self.q("""CREATE TABLE IF NOT EXISTS device_lock(
            id INTEGER PRIMARY KEY CHECK(id=1), device_id TEXT, created_at TEXT)""")
        self.seed()

    def seed(self):
        if self.q("SELECT COUNT(*) c FROM products", one=True)["c"]:
            return
        items = [
            ("Crompton","1 HP","1","Single","230V",4500,6000),
            ("Crompton","1.5 HP","1.5","Single","230V",5500,7200),
            ("Crompton","2 HP","2","Single","230V",7000,9000),
            ("Kirloskar","1 HP","1","Single","230V",4700,6300),
            ("Kirloskar","1.5 HP","1.5","Single","230V",5700,7500),
            ("Texmo","1 HP","1","Single","230V",4300,5900),
            ("Texmo","2 HP","2","Single","230V",6800,8800),
            ("V-Guard","1 HP","1","Single","230V",4600,6100),
            ("V-Guard","3 HP","3","Three Phase","415V",12000,15500),
        ]
        for x in items:
            self.q("""INSERT INTO products
            (brand,model,hp,phase,voltage,purchase_price,selling_price,stock,warranty_months,created_at)
            VALUES(?,?,?,?,?,?,?,0,12,?)""", (*x, now()))

    def device_id(self):
        if platform == "android":
            try:
                from jnius import autoclass
                Secure = autoclass("android.provider.Settings$Secure")
                Activity = autoclass("org.kivy.android.PythonActivity")
                return str(Secure.getString(Activity.mActivity.getContentResolver(),
                                            Secure.ANDROID_ID))
            except Exception:
                pass
        p = os.path.join(os.path.dirname(self.path), ".device_id")
        if os.path.exists(p):
            return open(p).read().strip()
        v = str(uuid.uuid4())
        open(p, "w").write(v)
        return v

    def enforce_device_lock(self):
        did = self.device_id()
        row = self.q("SELECT device_id FROM device_lock WHERE id=1", one=True)
        if not row:
            self.q("INSERT INTO device_lock(id,device_id,created_at) VALUES(1,?,?)", (did,now()))
            return True, "Device registered"
        return row["device_id"] == did, "This APK is already registered to another device."

    def bill_no(self):
        return "MKE-" + datetime.now().strftime("%Y%m%d-%H%M%S")

    def add_product(self, brand, model, hp, phase, voltage, buy, sell, warranty):
        self.q("""INSERT INTO products
        (brand,model,hp,phase,voltage,purchase_price,selling_price,stock,warranty_months,created_at)
        VALUES(?,?,?,?,?,?,?,0,?,?)""",
        (brand,model,hp,phase,voltage,buy,sell,warranty,now()))

    def purchase(self, pid, qty, serials, supplier, invoice):
        p = self.q("SELECT * FROM products WHERE id=?", (pid,), True)
        if not p or qty < 1:
            raise ValueError("Invalid product or quantity")
        serial_list = [s.strip() for s in serials.split(",") if s.strip()]
        if len(serial_list) != qty:
            raise ValueError("Enter exactly one serial number for every motor.")
        for s in serial_list:
            self.q("""INSERT INTO motors(product_id,serial_number,status,warranty_start,warranty_end,created_at)
                      VALUES(?,?, 'IN STOCK',NULL,NULL,?)""", (pid,s,now()))
        total = qty * float(p["purchase_price"])
        self.q("UPDATE products SET stock=stock+? WHERE id=?", (qty,pid))
        self.q("INSERT INTO purchases(supplier_name,invoice_no,total,created_at) VALUES(?,?,?,?)",
               (supplier,invoice,total,now()))

    def sell(self, customer, phone, pid, serial, payment):
        p = self.q("SELECT * FROM products WHERE id=?", (pid,), True)
        m = self.q("SELECT * FROM motors WHERE serial_number=?", (serial,), True)
        if not p:
            raise ValueError("Product not found")
        if not m or m["product_id"] != pid or m["status"] != "IN STOCK":
            raise ValueError("Serial number is not available in stock.")
        price = float(p["selling_price"])
        gst = price * GST_RATE / 100
        subtotal = price
        total = subtotal + gst
        bill = self.bill_no()
        self.q("""INSERT INTO bills(bill_no,customer_name,customer_phone,subtotal,cgst,sgst,gst,total,payment,created_at)
                  VALUES(?,?,?,?,?,?,?,?,?,?)""",
               (bill,customer,phone,subtotal,gst/2,gst/2,gst,total,payment,now()))
        bid = self.q("SELECT id FROM bills WHERE bill_no=?", (bill,), True)["id"]
        self.q("""INSERT INTO bill_items(bill_id,product_id,motor_id,serial_number,product_name,qty,price,total)
                  VALUES(?,?,?,?,?,?,?,?)""",
               (bid,pid,m["id"],serial,f'{p["brand"]} {p["model"]}',1,price,price))
        start = datetime.now()
        end = start + timedelta(days=30*int(p["warranty_months"]))
        self.q("""UPDATE motors SET status='SOLD',customer_name=?,customer_phone=?,bill_no=?,
                  warranty_start=?,warranty_end=? WHERE id=?""",
               (customer,phone,bill,start.strftime("%Y-%m-%d"),end.strftime("%Y-%m-%d"),m["id"]))
        self.q("UPDATE products SET stock=MAX(stock-1,0) WHERE id=?", (pid,))
        if phone:
            self.q("""INSERT INTO customers(name,phone,created_at) VALUES(?,?,?)
                      ON CONFLICT(phone) DO UPDATE SET name=excluded.name""",
                   (customer,phone,now()))
        return bill, total, gst

    def return_motor(self, bill, serial, reason, refund):
        m = self.q("SELECT * FROM motors WHERE serial_number=? AND bill_no=?", (serial,bill), True)
        if not m:
            raise ValueError("Sold motor not found for this bill.")
        self.q("UPDATE motors SET status='RETURNED' WHERE id=?", (m["id"],))
        self.q("INSERT INTO returns(bill_no,serial_number,reason,refund,created_at) VALUES(?,?,?,?,?)",
               (bill,serial,reason,refund,now()))

    def stats(self):
        return {
            "products": self.q("SELECT COUNT(*) c FROM products",one=True)["c"],
            "stock": self.q("SELECT COALESCE(SUM(stock),0) c FROM products",one=True)["c"],
            "sold": self.q("SELECT COUNT(*) c FROM motors WHERE status='SOLD'",one=True)["c"],
            "sales": self.q("SELECT COALESCE(SUM(total),0) c FROM bills",one=True)["c"],
            "warranty": self.q("""SELECT COUNT(*) c FROM motors
                                  WHERE status='SOLD' AND warranty_end IS NOT NULL
                                  AND warranty_end <= date('now','+30 day')""",one=True)["c"]
        }


def label(text, size=16):
    return Label(text=str(text), font_size=sp(size), size_hint_y=None, height=dp(38),
                 halign="left", valign="middle", text_size=(None,None))


def sp(v):
    return dp(v)


class Base(Screen):
    def box(self):
        b = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        return b

    def title(self, text):
        l = Label(text=text, font_size=dp(23), bold=True, size_hint_y=None, height=dp(50))
        return l

    def msg(self, text):
        Popup(title="Murali Krishna Electrical",
              content=Label(text=text, halign="center"),
              size_hint=(.9,.45)).open()

    def nav(self, *names):
        bar = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(5))
        for n in names:
            b=Button(text=n)
            b.bind(on_release=lambda _,x=n:self.manager.current=x)
            bar.add_widget(b)
        return bar


class Dashboard(Base):
    def on_pre_enter(self):
        self.clear_widgets()
        b=self.box()
        b.add_widget(self.title("MURALI KRISHNA ELECTRICAL"))
        b.add_widget(label("OFFLINE MOTOR SHOP POS • SAMSUNG TABLET",15))
        s=App.get_running_app().db.stats()
        g=GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        g.bind(minimum_height=g.setter("height"))
        for k,v in [("Products",s["products"]),("Motors in Stock",s["stock"]),
                    ("Motors Sold",s["sold"]),("Total Sales",f"₹{s['sales']:.2f}"),
                    ("Warranty Alerts",s["warranty"]),("GST",f"{GST_RATE:.0f}%")]:
            g.add_widget(label(k,15)); g.add_widget(label(v,17))
        b.add_widget(g)
        b.add_widget(self.nav("sale","purchase","inventory"))
        b.add_widget(self.nav("customers","reports","more"))
        self.add_widget(b)


class Sale(Base):
    def on_pre_enter(self):
        self.clear_widgets(); b=self.box()
        b.add_widget(self.title("NEW MOTOR SALE"))
        name=TextInput(hint_text="Customer name", multiline=False)
        phone=TextInput(hint_text="Customer phone", multiline=False, input_type="number")
        products=App.get_running_app().db.q("SELECT * FROM products ORDER BY brand,model")
        labels=[f'{p["id"]} • {p["brand"]} {p["model"]} • ₹{p["selling_price"]:.0f} • Stock {p["stock"]}' for p in products]
        spn=Spinner(text=labels[0] if labels else "No products", values=labels, size_hint_y=None,height=dp(50))
        serial=TextInput(hint_text="Motor serial number", multiline=False)
        pay=Spinner(text="Cash", values=("Cash","UPI","Card","Bank Transfer","Credit"), size_hint_y=None,height=dp(50))
        for w in (name,phone,spn,serial,pay): b.add_widget(w)
        def save(_):
            try:
                pid=int(spn.text.split(" • ")[0])
                bill,total,gst=App.get_running_app().db.sell(name.text.strip(),phone.text.strip(),pid,serial.text.strip(),pay.text)
                self.msg(f"SALE SUCCESS\nBill: {bill}\nTotal: ₹{total:.2f}\nGST: ₹{gst:.2f}")
                self.manager.current="dashboard"
            except Exception as e: self.msg(str(e))
        b.add_widget(Button(text="SAVE SALE",size_hint_y=None,height=dp(55),on_release=save))
        b.add_widget(self.nav("dashboard","inventory","reports"))
        self.add_widget(b)


class Purchase(Base):
    def on_pre_enter(self):
        self.clear_widgets(); b=self.box()
        b.add_widget(self.title("PURCHASE / STOCK ENTRY"))
        products=App.get_running_app().db.q("SELECT * FROM products ORDER BY brand,model")
        labels=[f'{p["id"]} • {p["brand"]} {p["model"]} • Buy ₹{p["purchase_price"]:.0f}' for p in products]
        spn=Spinner(text=labels[0],values=labels,size_hint_y=None,height=dp(50))
        qty=TextInput(hint_text="Quantity",multiline=False,input_type="number")
        serials=TextInput(hint_text="Serial numbers separated by commas",multiline=False)
        supplier=TextInput(hint_text="Supplier name",multiline=False)
        invoice=TextInput(hint_text="Supplier invoice number",multiline=False)
        for w in (spn,qty,serials,supplier,invoice): b.add_widget(w)
        def save(_):
            try:
                pid=int(spn.text.split(" • ")[0]); q=int(qty.text)
                App.get_running_app().db.purchase(pid,q,serials.text,supplier.text,invoice.text)
                self.msg("Purchase saved. Stock and serial inventory updated.")
                self.manager.current="inventory"
            except Exception as e:self.msg(str(e))
        b.add_widget(Button(text="ADD STOCK",size_hint_y=None,height=dp(55),on_release=save))
        b.add_widget(self.nav("dashboard","inventory"))
        self.add_widget(b)


class Inventory(Base):
    def on_pre_enter(self):
        self.clear_widgets(); root=self.box()
        root.add_widget(self.title("MOTOR INVENTORY"))
        search=TextInput(hint_text="Search serial / brand / model",multiline=False,size_hint_y=None,height=dp(48))
        root.add_widget(search)
        sv=ScrollView(); grid=GridLayout(cols=1,spacing=dp(4),size_hint_y=None,padding=dp(3))
        grid.bind(minimum_height=grid.setter("height")); sv.add_widget(grid); root.add_widget(sv)
        def refresh(*_):
            grid.clear_widgets(); term=search.text.strip()
            rows=App.get_running_app().db.q("""SELECT m.*,p.brand,p.model,p.hp,p.phase
                FROM motors m JOIN products p ON p.id=m.product_id
                WHERE m.serial_number LIKE ? OR p.brand LIKE ? OR p.model LIKE ?
                ORDER BY m.id DESC""",(f"%{term}%",f"%{term}%",f"%{term}%"))
            for r in rows:
                grid.add_widget(label(f'{r["serial_number"]} | {r["brand"]} {r["model"]} | {r["status"]} | Bill {r["bill_no"] or "-"}',13))
        search.bind(text=refresh); refresh()
        root.add_widget(self.nav("dashboard","sale","purchase"))
        self.add_widget(root)


class Customers(Base):
    def on_pre_enter(self):
        self.clear_widgets(); root=self.box(); root.add_widget(self.title("CUSTOMERS"))
        sv=ScrollView(); grid=GridLayout(cols=1,size_hint_y=None,spacing=dp(5)); grid.bind(minimum_height=grid.setter("height")); sv.add_widget(grid)
        rows=App.get_running_app().db.q("SELECT * FROM customers ORDER BY id DESC")
        for r in rows: grid.add_widget(label(f'{r["name"]} | {r["phone"]} | {r["address"] or ""}',14))
        root.add_widget(sv); root.add_widget(self.nav("dashboard","sale","reports")); self.add_widget(root)


class Reports(Base):
    def on_pre_enter(self):
        self.clear_widgets(); root=self.box(); root.add_widget(self.title("REPORTS"))
        db=App.get_running_app().db
        s=db.stats()
        rows=[
            ("Today's bills",db.q("SELECT COUNT(*) c FROM bills WHERE date(created_at)=date('now')",one=True)["c"]),
            ("Today's sales",db.q("SELECT COALESCE(SUM(total),0) c FROM bills WHERE date(created_at)=date('now')",one=True)["c"]),
            ("All sales",s["sales"]),
            ("Stock units",s["stock"]),
            ("Sold motors",s["sold"]),
            ("Warranty <= 30 days",s["warranty"]),
            ("Returns",db.q("SELECT COUNT(*) c FROM returns",one=True)["c"]),
            ("Repairs",db.q("SELECT COUNT(*) c FROM repairs",one=True)["c"]),
        ]
        for k,v in rows: root.add_widget(label(f"{k}: {v}",15))
        root.add_widget(self.nav("dashboard","inventory","more")); self.add_widget(root)


class More(Base):
    def on_pre_enter(self):
        self.clear_widgets(); root=self.box(); root.add_widget(self.title("MORE"))
        root.add_widget(label("Single-device • Offline • SQLite",15))
        root.add_widget(label("Shop: "+SHOP_NAME,14))
        root.add_widget(label("Phone: "+SHOP_PHONE,14))
        root.add_widget(label("Address: "+SHOP_ADDRESS,14))
        root.add_widget(label("GST: 18% (CGST 9% + SGST 9%)",14))
        root.add_widget(label("Device binding is created on first launch.",13))
        root.add_widget(self.nav("dashboard","customers","reports")); self.add_widget(root)


class MKEApp(App):
    def build(self):
        self.title=SHOP_NAME
        self.db=DB(os.path.join(self.user_data_dir,"murali_krishna_electrical.db"))
        ok,msg=self.db.enforce_device_lock()
        if not ok:
            return LockedScreen(msg)
        sm=ScreenManager()
        for name,cls in [("dashboard",Dashboard),("sale",Sale),("purchase",Purchase),
                         ("inventory",Inventory),("customers",Customers),("reports",Reports),("more",More)]:
            sm.add_widget(cls(name=name))
        return sm


class LockedScreen(Screen):
    def __init__(self,msg,**kwargs):
        super().__init__(**kwargs)
        b=BoxLayout(orientation="vertical",padding=dp(30),spacing=dp(20))
        b.add_widget(Label(text="DEVICE LOCKED",font_size=dp(28),bold=True))
        b.add_widget(Label(text=msg,halign="center"))
        self.add_widget(b)


if __name__ == "__main__":
    MKEApp().run()
