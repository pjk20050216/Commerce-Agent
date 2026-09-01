"""
Seed script - uses ORM with explicit naive datetimes.
"""
import asyncio
import sys
import random
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, "D:/ait-code/agent_part")

from src.db.postgres import get_db_session
from sqlalchemy import text
from src.db.models import Product, GenerationTask
from src.db.listing_models import (
    ListingProductPO, ListingTaskPO, AssetPackagePO,
    CopywritingPackagePO, ComplianceReportPO, TaskResultPO,
    AdapterConfigPO, GeneratedAssetPO,
)

TENANT_ID = "default"
PLATFORMS = ["amazon_us", "amazon_uk", "amazon_jp", "shopify", "ebay", "walmart", "aliexpress"]

# 50 real Amazon products
PRODUCTS_DATA = [
    ("PROD-0001", "Anker PowerCore 26800mAh Portable Charger", "Anker", "Electronics",
     "Ultra-high capacity 26800mAh portable charger with dual USB ports. PowerIQ and VoltageBoost technology.",
     [{"title":"Ultra-High Capacity","content":"26800mAh charges iPhone 13 over 6 times"},{"title":"Dual USB Ports","content":"Charge two devices simultaneously"},{"title":"Safety System","content":"MultiProtect 11-point safety protection"}],
     [{"name":"Capacity","value":"26800mAh"},{"name":"Output","value":"Dual USB 5V/3A"},{"name":"Weight","value":"495g"}]),
    ("PROD-0002", "Sony WH-1000XM5 Noise Cancelling Headphones", "Sony", "Electronics",
     "Industry-leading noise cancellation with 8 microphones. 30-hour battery life with quick charging.",
     [{"title":"Best ANC","content":"8 microphones with Auto NC Optimizer"},{"title":"30h Battery","content":"All-day listening with quick charge"},{"title":"Hi-Res Audio","content":"LDAC and DSEE Extreme upscaling"}],
     [{"name":"Driver","value":"30mm"},{"name":"Battery","value":"30 hours"},{"name":"Weight","value":"250g"}]),
    ("PROD-0003", "Apple AirPods Pro 2nd Generation", "Apple", "Electronics",
     "Up to 2x more Active Noise Cancellation. Adaptive Transparency. Personalized Spatial Audio with dynamic head tracking.",
     [{"title":"2x ANC","content":"Next-level noise cancellation"},{"title":"Spatial Audio","content":"Personalized immersive sound"},{"title":"Find My","content":"Precision Finding"}],
     [{"name":"Chip","value":"H2"},{"name":"Battery","value":"6h + 30h case"},{"name":"Water","value":"IPX4"}]),
    ("PROD-0004", "Samsung Galaxy Tab S9 Ultra 256GB", "Samsung", "Electronics",
     "14.6-inch Dynamic AMOLED 2X 120Hz display. Snapdragon 8 Gen 2. S Pen included.",
     [{"title":"14.6 AMOLED","content":"Stunning 120Hz display"},{"title":"S Pen","content":"IP68 water-resistant"},{"title":"DeX Mode","content":"Desktop-class multitasking"}],
     [{"name":"Screen","value":"14.6 AMOLED 120Hz"},{"name":"CPU","value":"Snapdragon 8 Gen 2"},{"name":"Storage","value":"256GB"}]),
    ("PROD-0005", "Logitech MX Master 3S Wireless Mouse", "Logitech", "Electronics",
     "8K DPI any-surface tracking with Darkfield sensor. USB-C quick charging, 70-day battery.",
     [{"title":"8K DPI","content":"Tracks on glass"},{"title":"70-Day Battery","content":"Full charge lasts 70 days"},{"title":"Multi-Device","content":"Control up to 3 computers"}],
     [{"name":"DPI","value":"8000"},{"name":"Battery","value":"70 days"},{"name":"Connectivity","value":"Bluetooth+USB-C"}]),
    ("PROD-0006", "Instant Pot Duo Plus 6-Quart 9-in-1 Pressure Cooker", "Instant Pot", "Home & Kitchen",
     "9-in-1 programmable cooker with 25 smart programs. Stainless steel inner pot.",
     [{"title":"9-in-1","content":"Replaces 9 kitchen appliances"},{"title":"Smart Programs","content":"25 one-touch presets"},{"title":"Safety","content":"10+ built-in safety features"}],
     [{"name":"Capacity","value":"6 Quart"},{"name":"Power","value":"1000W"},{"name":"Material","value":"Stainless Steel"}]),
    ("PROD-0007", "Ninja BL770 Mega Kitchen System", "Ninja", "Home & Kitchen",
     "1500W professional blender with 72oz pitcher. 8-cup food processor and 16oz Nutri Ninja cups.",
     [{"title":"1500W Motor","content":"Professional-grade power"},{"title":"4 Functions","content":"Blender, processor, personal blender"},{"title":"Auto-iQ","content":"Intelligent pre-set programs"}],
     [{"name":"Power","value":"1500W"},{"name":"Pitcher","value":"72oz"},{"name":"Cups","value":"2x 16oz"}]),
    ("PROD-0008", "iRobot Roomba j7+ Self-Emptying Robot Vacuum", "iRobot", "Home & Kitchen",
     "PrecisionVision Navigation identifies obstacles. Self-emptying base holds 60 days of debris.",
     [{"title":"Obstacle Avoid","content":"PrecisionVision identifies obstacles"},{"title":"Self-Emptying","content":"60 days of debris storage"},{"title":"Smart Map","content":"Room-by-room cleaning"}],
     [{"name":"Suction","value":"10x Standard"},{"name":"Bin","value":"60 days"},{"name":"Nav","value":"Camera+AI"}]),
    ("PROD-0009", "LEVOIT Air Purifier Core 400S", "LEVOIT", "Home & Kitchen",
     "Covers 1980 sq ft. H13 True HEPA filter 99.97% capture. Smart WiFi with VeSync app.",
     [{"title":"1980 sq ft","content":"Large room coverage"},{"title":"H13 HEPA","content":"99.97% particle capture"},{"title":"Smart WiFi","content":"App control + auto sensor"}],
     [{"name":"Coverage","value":"1980 sq ft"},{"name":"Filter","value":"H13 True HEPA"},{"name":"Noise","value":"24-52dB"}]),
    ("PROD-0010", "Keurig K-Elite Single Serve Coffee Maker", "Keurig", "Home & Kitchen",
     "Brews 5 cup sizes plus Iced Coffee setting. Strong Brew button. 75oz removable reservoir.",
     [{"title":"Iced Coffee","content":"Dedicated iced brewing"},{"title":"Strong Brew","content":"Bolder coffee flavor"},{"title":"5 Sizes","content":"4-12oz brew options"}],
     [{"name":"Reservoir","value":"75oz"},{"name":"Sizes","value":"5 sizes"},{"name":"Material","value":"Brushed Metal"}]),
    ("PROD-0011", "YETI Rambler 26 oz Bottle with Chug Cap", "YETI", "Sports & Outdoors",
     "18/8 stainless steel double-wall vacuum insulation. No Sweat design. Dishwasher safe.",
     [{"title":"Double-Wall","content":"Keeps drinks cold 24+ hours"},{"title":"18/8 Stainless","content":"Puncture and rust resistant"},{"title":"No Sweat","content":"No condensation rings"}],
     [{"name":"Capacity","value":"26oz"},{"name":"Material","value":"18/8 Stainless"},{"name":"Weight","value":"1.5 lbs"}]),
    ("PROD-0012", "Fitbit Charge 6 Fitness Tracker", "Fitbit", "Sports & Outdoors",
     "Built-in GPS. ECG and stress management. 40+ exercise modes. 7-day battery.",
     [{"title":"Built-in GPS","content":"Track without phone"},{"title":"ECG Monitor","content":"On-wrist heart health"},{"title":"7-Day Battery","content":"Week-long tracking"}],
     [{"name":"Display","value":"Color AMOLED"},{"name":"Battery","value":"7 days"},{"name":"Water","value":"50m"}]),
    ("PROD-0013", "Bowflex SelectTech 552 Adjustable Dumbbells", "Bowflex", "Sports & Outdoors",
     "Adjusts 5 to 52.5 lbs in 2.5 lb increments. Replaces 15 dumbbell pairs.",
     [{"title":"5-52.5 lbs","content":"Replaces 15 dumbbell pairs"},{"title":"Quick Dial","content":"Weight change in 5 seconds"},{"title":"Compact","content":"Saves 90% space"}],
     [{"name":"Range","value":"5-52.5 lbs"},{"name":"Increment","value":"2.5 lbs"},{"name":"Warranty","value":"2 years"}]),
    ("PROD-0014", "Garmin Forerunner 265 Running Smartwatch", "Garmin", "Sports & Outdoors",
     "AMOLED touchscreen. Training readiness with HRV. Multi-band GPS. 13 days battery.",
     [{"title":"AMOLED","content":"Vibrant always-on display"},{"title":"Training Readiness","content":"Daily score from HRV/sleep"},{"title":"Multi-Band GPS","content":"Superior accuracy"}],
     [{"name":"Display","value":"1.3 AMOLED"},{"name":"Battery","value":"13 days"},{"name":"GPS","value":"Multi-band+SatIQ"}]),
    ("PROD-0015", "Hydro Flask Wide Mouth 32oz Water Bottle", "Hydro Flask", "Sports & Outdoors",
     "TempShield double-wall vacuum insulation. Pro-grade stainless steel. Lifetime warranty.",
     [{"title":"TempShield","content":"Cold 24h, hot 12h"},{"title":"Flex Cap","content":"Leakproof insulation"},{"title":"Lifetime","content":"Lifetime warranty"}],
     [{"name":"Capacity","value":"32oz"},{"name":"Material","value":"18/8 Stainless"},{"name":"Weight","value":"0.8 lbs"}]),
    ("PROD-0016", "Dyson Supersonic Hair Dryer", "Dyson", "Beauty",
     "Fast drying with Air Multiplier. Intelligent heat control. 5 magnetic attachments.",
     [{"title":"Fast Drying","content":"Air Multiplier technology"},{"title":"Heat Control","content":"Measures 40x/second"},{"title":"5 Attachments","content":"Magnetic styling attachments"}],
     [{"name":"Motor","value":"Digital V9"},{"name":"Attachments","value":"5 magnetic"},{"name":"Weight","value":"1.8 lbs"}]),
    ("PROD-0017", "Philips Sonicare DiamondClean 9000 Electric Toothbrush", "Philips", "Beauty",
     "62,000 brush movements/min. Smart sensor coaching. 4 modes x 3 intensities. 2-week battery.",
     [{"title":"62K Movements","content":"Removes 10x more plaque"},{"title":"Smart Sensor","content":"Real-time coaching via app"},{"title":"USB Case","content":"Travel case+USB-C"}],
     [{"name":"Movements","value":"62,000/min"},{"name":"Modes","value":"4x3 intensities"},{"name":"Battery","value":"14 days"}]),
    ("PROD-0018", "Olaplex No.3 Hair Perfector 100ml", "Olaplex", "Beauty",
     "At-home bond-building treatment. Repairs broken disulfide bonds. Color-safe and vegan.",
     [{"title":"Bond Building","content":"Patented repair technology"},{"title":"Weekly Use","content":"Visible improvement first use"},{"title":"Color Safe","content":"Safe for all hair types"}],
     [{"name":"Size","value":"100ml"},{"name":"Type","value":"Leave-in"},{"name":"Frequency","value":"Weekly"}]),
    ("PROD-0019", "Revlon One-Step Volumizer PLUS 2.0", "Revlon", "Beauty",
     "2.4\" oval brush. 4 heat settings with cool option. 75% less frizz. Titanium ceramic.",
     [{"title":"One-Step","content":"Dry and style simultaneously"},{"title":"75% Less Frizz","content":"Smooth results"},{"title":"4 Settings","content":"Heat + cool shot"}],
     [{"name":"Brush","value":"2.4 oval"},{"name":"Power","value":"1100W"},{"name":"Coating","value":"Titanium Ceramic"}]),
    ("PROD-0020", "CeraVe Hydrating Facial Cleanser 16oz", "CeraVe", "Beauty",
     "Non-foaming gentle cleanser. 3 essential ceramides and hyaluronic acid. Fragrance-free.",
     [{"title":"3 Ceramides","content":"Restores skin barrier"},{"title":"Hyaluronic Acid","content":"Retains moisture"},{"title":"Fragrance-Free","content":"Safe for sensitive skin"}],
     [{"name":"Size","value":"16oz"},{"name":"Skin Type","value":"Normal to Dry"},{"name":"Key","value":"Ceramides+HA"}]),
    ("PROD-0021", "LEGO Star Wars Millennium Falcon 75257", "LEGO", "Toys & Games",
     "1,351-piece build with rotating gun turrets. 7 minifigures. Opening cockpit.",
     [{"title":"1351 Pieces","content":"Rotating gun turrets"},{"title":"7 Minifigures","content":"Complete character set"},{"title":"Display Ready","content":"Play or display"}],
     [{"name":"Pieces","value":"1,351"},{"name":"Minifigs","value":"7"},{"name":"Age","value":"9+"}]),
    ("PROD-0022", "Nintendo Switch OLED Model - White", "Nintendo", "Toys & Games",
     "7-inch OLED vibrant screen. 64GB internal storage. Wide adjustable stand with LAN port.",
     [{"title":"7 OLED","content":"Vivid colors and contrast"},{"title":"64GB Storage","content":"Double standard"},{"title":"Enhanced Audio","content":"Improved speakers"}],
     [{"name":"Screen","value":"7 OLED"},{"name":"Storage","value":"64GB"},{"name":"Battery","value":"4.5-9 hours"}]),
    ("PROD-0023", "Catan Board Game 5th Edition", "Catan Studio", "Toys & Games",
     "Classic strategy game for 3-4 players. Random board setup. 60 min playtime.",
     [{"title":"Strategy Classic","content":"30M+ copies sold"},{"title":"Replayable","content":"Random board variety"},{"title":"Family Fun","content":"Easy to learn, hard to master"}],
     [{"name":"Players","value":"3-4"},{"name":"Playtime","value":"60 min"},{"name":"Age","value":"10+"}]),
    ("PROD-0024", "Melissa & Doug Wooden Building Blocks 100 Pieces", "Melissa & Doug", "Toys & Games",
     "100 solid wood blocks in 9 shapes and 4 colors. Develops motor skills and creativity.",
     [{"title":"100 Pieces","content":"9 shapes, 4 colors"},{"title":"Educational","content":"Motor skills+creativity"},{"title":"Durable","content":"Solid wood built to last"}],
     [{"name":"Pieces","value":"100"},{"name":"Material","value":"Solid Wood"},{"name":"Age","value":"3-8"}]),
    ("PROD-0025", "Barbie Dreamhouse 2024 Dollhouse with Pool", "Mattel", "Toys & Games",
     "3-story 8-room dollhouse 43\" tall. Working elevator and pool slide. 75+ pieces.",
     [{"title":"3 Stories","content":"8 rooms, 43 tall"},{"title":"75+ Pieces","content":"Full furniture set"},{"title":"Interactive","content":"Lights, sounds, voice"}],
     [{"name":"Height","value":"43 inches"},{"name":"Rooms","value":"8"},{"name":"Pieces","value":"75+"}]),
    ("PROD-0026", "Levi's Men's 501 Original Fit Jeans", "Levi's", "Clothing",
     "The original blue jean since 1873. Straight leg, button fly. 100% cotton rigid denim.",
     [{"title":"Original Fit","content":"Iconic since 1873"},{"title":"Rigid Denim","content":"100% cotton authentic"},{"title":"30+ Washes","content":"Find your perfect shade"}],
     [{"name":"Material","value":"100% Cotton"},{"name":"Fit","value":"Straight Leg"},{"name":"Closure","value":"Button Fly"}]),
    ("PROD-0027", "Columbia Men's Steens Mountain Fleece Jacket", "Columbia", "Clothing",
     "Classic full-zip fleece. 100% polyester MTR filament. Zippered hand pockets.",
     [{"title":"MTR Fleece","content":"Max warmth-to-weight"},{"title":"Versatile","content":"Mid-layer or standalone"},{"title":"Easy Care","content":"Machine washable"}],
     [{"name":"Material","value":"100% Polyester"},{"name":"Fit","value":"Modern Classic"},{"name":"Pockets","value":"2 zippered"}]),
    ("PROD-0028", "Crocs Unisex-Adult Classic Clogs", "Crocs", "Clothing",
     "Iconic Crocs comfort with Croslite foam cushion. Ventilation ports. Customizable with Jibbitz.",
     [{"title":"Croslite Foam","content":"Lightweight all-day comfort"},{"title":"Ventilation","content":"Breathable ports"},{"title":"Customizable","content":"Jibbitz charm personalization"}],
     [{"name":"Material","value":"Croslite Foam"},{"name":"Closure","value":"Slip-on"},{"name":"Weight","value":"Ultra Light"}]),
    ("PROD-0029", "Ray-Ban RB2132 New Wayfarer Sunglasses", "Ray-Ban", "Clothing",
     "Updated classic Wayfarer. 100% UV protection. G-15 polarized lenses. Multiple color options.",
     [{"title":"100% UV","content":"Complete UV protection"},{"title":"Iconic Design","content":"Modern Wayfarer update"},{"title":"Polarized","content":"Crystal clear vision"}],
     [{"name":"Frame","value":"Acetate"},{"name":"Lens","value":"G-15 Polarized"},{"name":"Bridge","value":"18mm"}]),
    ("PROD-0030", "Under Armour Tech 2.0 Short Sleeve T-Shirt", "Under Armour", "Clothing",
     "UA Tech fabric quick-drying and ultra-soft. Anti-odor technology. Moisture transport system.",
     [{"title":"UA Tech","content":"Quick-drying ultra-soft"},{"title":"Anti-Odor","content":"Stays fresher longer"},{"title":"Moisture Wicking","content":"Keeps you dry"}],
     [{"name":"Material","value":"100% Polyester"},{"name":"Fit","value":"Loose"},{"name":"Care","value":"Machine Wash"}]),
    ("PROD-0031", "Furbo 360 Dog Camera with Treat Tossing", "Furbo", "Pet Supplies",
     "360 rotating HD camera 1080p. 2-way audio. Smart barking alerts. Night vision.",
     [{"title":"360 View","content":"Full room coverage"},{"title":"Treat Tossing","content":"Remote play from phone"},{"title":"Bark Alerts","content":"AI detection notifications"}],
     [{"name":"Camera","value":"1080p HD 360"},{"name":"Audio","value":"2-way"},{"name":"Night","value":"Yes"}]),
    ("PROD-0032", "Greenies Original Dental Dog Treats 36 Count", "Greenies", "Pet Supplies",
     "Veterinarian recommended dental chews. Unique texture cleans teeth. Highly digestible.",
     [{"title":"Vet Recommended","content":"VOHC accepted"},{"title":"Fights Plaque","content":"Cleans to gumline"},{"title":"Digestible","content":"Highly soluble and safe"}],
     [{"name":"Count","value":"36 treats"},{"name":"Size","value":"Regular"},{"name":"Flavor","value":"Original"}]),
    ("PROD-0033", "PetSafe ScoopFree Self-Cleaning Litter Box", "PetSafe", "Pet Supplies",
     "Automatic self-cleaning litter box. Crystal litter absorbs urine. No scooping for weeks.",
     [{"title":"No Scooping","content":"Auto rake after use"},{"title":"Crystal Litter","content":"5x better odor control"},{"title":"Weeks of Use","content":"Up to 30 days per cat"}],
     [{"name":"Type","value":"Self-Cleaning"},{"name":"Litter","value":"Crystal"},{"name":"Tray Life","value":"Up to 30 days"}]),
    ("PROD-0034", "KONG Classic Dog Toy Large", "KONG", "Pet Supplies",
     "Natural rubber formula puncture resistant and super bouncy. Stuff with treats. Dishwasher safe.",
     [{"title":"Indestructible","content":"Natural rubber durability"},{"title":"Stuffable","content":"Fill with treats"},{"title":"40+ Years","content":"Vet and trainer recommended"}],
     [{"name":"Size","value":"Large"},{"name":"Material","value":"Natural Rubber"},{"name":"Type","value":"Heavy Duty"}]),
    ("PROD-0035", "Blue Buffalo Life Protection Adult Dog Food 30lb", "Blue Buffalo", "Pet Supplies",
     "Real chicken first ingredient. LifeSource Bits with antioxidants. No corn, wheat, or soy.",
     [{"title":"Real Chicken","content":"High-quality first ingredient"},{"title":"LifeSource Bits","content":"Cold-formed nutrients"},{"title":"No Fillers","content":"No corn, wheat, soy"}],
     [{"name":"Size","value":"30 lb"},{"name":"Protein","value":"Chicken"},{"name":"Stage","value":"Adult"}]),
    ("PROD-0036", "Atomic Habits by James Clear", "Penguin", "Books",
     "#1 New York Times bestseller. Practical habit formation framework. 15M+ copies sold.",
     [{"title":"#1 Bestseller","content":"15M+ copies sold"},{"title":"4 Laws","content":"Proven habit framework"},{"title":"Practical","content":"Actionable strategies"}],
     [{"name":"Pages","value":"320"},{"name":"Format","value":"Hardcover"},{"name":"Language","value":"English"}]),
    ("PROD-0037", "The Body Keeps the Score", "Penguin", "Books",
     "Bessel van der Kolk's groundbreaking trauma research. 30+ years of research in one book.",
     [{"title":"Scientific","content":"30+ years trauma research"},{"title":"Innovative","content":"New brain treatments"},{"title":"Accessible","content":"For all readers"}],
     [{"name":"Pages","value":"464"},{"name":"Format","value":"Paperback"},{"name":"Language","value":"English"}]),
    ("PROD-0038", "Dune - Penguin Galaxy Hardcover", "Penguin", "Books",
     "Frank Herbert's epic masterpiece. Introduction by Neil Gaiman. Hugo and Nebula awards.",
     [{"title":"Epic Classic","content":"Best-selling sci-fi ever"},{"title":"Collector Edition","content":"Penguin Galaxy hardcover"},{"title":"Foreword","content":"Neil Gaiman intro"}],
     [{"name":"Pages","value":"720"},{"name":"Format","value":"Hardcover"},{"name":"Series","value":"Penguin Galaxy"}]),
    ("PROD-0039", "The Very Hungry Caterpillar Board Book", "Philomel", "Books",
     "Eric Carle's classic. Teaches counting, days, and metamorphosis. 50M+ copies sold.",
     [{"title":"50M+ Sold","content":"Generations of children"},{"title":"Educational","content":"Counting+science"},{"title":"Die-Cut","content":"Interactive pages"}],
     [{"name":"Pages","value":"26"},{"name":"Format","value":"Board Book"},{"name":"Age","value":"0-3"}]),
    ("PROD-0040", "Clean Code by Robert C. Martin", "Pearson", "Books",
     "Definitive guide to writing better code. Naming, functions, error handling, unit testing.",
     [{"title":"Industry Standard","content":"Required reading"},{"title":"Practical","content":"Code examples+case studies"},{"title":"Timeless","content":"Cross-language principles"}],
     [{"name":"Pages","value":"464"},{"name":"Author","value":"Robert C. Martin"},{"name":"Format","value":"Paperback"}]),
    ("PROD-0041", "AstroAI Digital Tire Pressure Gauge", "AstroAI", "Automotive",
     "Digital pressure gauge with backlit LCD. 0-150 PSI, 4 settings. Ergonomic design.",
     [{"title":"Precise","content":"+/-1% accuracy"},{"title":"4 Settings","content":"PSI, BAR, KPA, KG/CM2"},{"title":"Easy Read","content":"Glowing blue backlit LCD"}],
     [{"name":"Range","value":"0-150 PSI"},{"name":"Display","value":"Backlit LCD"},{"name":"Battery","value":"AAA included"}]),
    ("PROD-0042", "Chemical Guys 14-Piece Car Wash Kit", "Chemical Guys", "Automotive",
     "Complete detailing kit with Butter Wet Wax, Mr. Pink soap. Professional results at home.",
     [{"title":"14 Pieces","content":"Complete detail kit"},{"title":"Pro Grade","content":"Used by detailing pros"},{"title":"Foam Cannon","content":"Thick foam safe washing"}],
     [{"name":"Pieces","value":"14"},{"name":"Includes","value":"Soap,Wax,Wheel Cleaner"},{"name":"Level","value":"Beginner to Pro"}]),
    ("PROD-0043", "AUXITO LED Headlight Bulbs H11 20000LM", "AUXITO", "Automotive",
     "600% brighter than halogen. Aviation-grade aluminum heat sink. IP68 waterproof. 50K hours.",
     [{"title":"600% Brighter","content":"20,000 lumens"},{"title":"50K Hours","content":"Aviation aluminum cooling"},{"title":"Plug & Play","content":"10-min installation"}],
     [{"name":"Brightness","value":"20000LM/pair"},{"name":"Life","value":"50,000 hours"},{"name":"Waterproof","value":"IP68"}]),
    ("PROD-0044", "Armor All Car Interior Cleaning Wipes 90 Count", "Armor All", "Automotive",
     "Multi-surface cleaning wipes. UV blockers prevent fading. Safe for dash, leather, vinyl.",
     [{"title":"Multi-Surface","content":"Safe on all materials"},{"title":"UV Protection","content":"Prevents fading and cracking"},{"title":"Convenient","content":"Pop-up canister"}],
     [{"name":"Count","value":"90 wipes"},{"name":"Scent","value":"Fresh"},{"name":"Safe On","value":"Dash, Leather, Vinyl"}]),
    ("PROD-0045", "NOCO Boost Plus GB40 1000A Jump Starter", "NOCO", "Automotive",
     "1000-amp portable lithium jump starter. 20 jump starts per charge. USB power bank. Spark-proof.",
     [{"title":"1000 Amps","content":"Up to 6L gas engines"},{"title":"20 Jumps","content":"Per single charge"},{"title":"Safe","content":"Spark-proof design"}],
     [{"name":"Peak Amps","value":"1000A"},{"name":"Engine","value":"Up to 6L Gas"},{"name":"Weight","value":"2.4 lbs"}]),
    ("PROD-0046", "KitchenAid Artisan Series 5-Qt Stand Mixer", "KitchenAid", "Home & Kitchen",
     "Tilt-head design, 10 speeds. 5-quart stainless steel bowl. Flat beater, dough hook, wire whip.",
     [{"title":"10 Speeds","content":"Versatile mixing power"},{"title":"5 Qt Bowl","content":"Stainless steel durability"},{"title":"Tilt-Head","content":"Easy access design"}],
     [{"name":"Capacity","value":"5 Quart"},{"name":"Power","value":"325W"},{"name":"Attachments","value":"3 included"}]),
    ("PROD-0047", "Samsung 65 OLED 4K Smart TV S95C", "Samsung", "Electronics",
     "Quantum HDR OLED+ with Neural Quantum Processor 4K. Dolby Atmos. Gaming Hub.",
     [{"title":"OLED+","content":"Quantum HDR with Neural 4K"},{"title":"Dolby Atmos","content":"Immersive sound experience"},{"title":"Gaming Hub","content":"Cloud gaming without console"}],
     [{"name":"Size","value":"65 inch"},{"name":"Display","value":"OLED 4K"},{"name":"Sound","value":"Dolby Atmos"}]),
    ("PROD-0048", "DeWalt 20V MAX Cordless Drill Kit DCD771C2", "DeWalt", "Tools",
     "Compact lightweight design. 2-speed transmission. 1/2 ratcheting chuck. LED light. 2 batteries.",
     [{"title":"20V MAX","content":"Powerful cordless performance"},{"title":"2-Speed","content":"0-450 / 0-1500 RPM"},{"title":"Compact","content":"Fits tight spaces"}],
     [{"name":"Voltage","value":"20V MAX"},{"name":"Chuck","value":"1/2 inch"},{"name":"Batteries","value":"2 included"}]),
    ("PROD-0049", "Bose QuietComfort Ultra Headphones", "Bose", "Electronics",
     "Spatial audio with head tracking. World-class noise cancellation. 24-hour battery. Luxurious comfort.",
     [{"title":"Spatial Audio","content":"Immersive head tracking"},{"title":"ANC","content":"World-class noise cancel"},{"title":"24h Battery","content":"All-day comfort"}],
     [{"name":"Driver","value":"Custom Bose"},{"name":"Battery","value":"24 hours"},{"name":"Weight","value":"252g"}]),
    ("PROD-0050", "Owala FreeSip Insulated Stainless Steel Water Bottle 32oz", "Owala", "Sports & Outdoors",
     "Patented FreeSip spout with push-button lid. Double-wall insulation 24h cold. BPA-free.",
     [{"title":"FreeSip Spout","content":"Two ways to drink"},{"title":"24h Cold","content":"Triple-layer insulation"},{"title":"Wide Opening","content":"Easy cleaning and ice adding"}],
     [{"name":"Capacity","value":"32oz"},{"name":"Material","value":"Stainless Steel"},{"name":"Cold","value":"24 hours"}]),
]


def _naive_now():
    return datetime.utcnow()


async def seed_all(session):
    now = _naive_now()

    # 1. Products (50)
    print("[1/9] Seeding 50 products...")
    product_records = []
    for p in PRODUCTS_DATA:
        product_records.append(Product(
            tenant_id=TENANT_ID, product_id=p[0], name=p[1], brand=p[2],
            category=p[3], description=p[4], selling_points=p[5],
            specifications=p[6], extra_data={"source": "amazon", "seed": True},
            created_at=_naive_now() - timedelta(days=random.randint(0, 60)),
            updated_at=_naive_now(),
        ))
    session.add_all(product_records)
    await session.flush()
    print(f"  [OK] {len(product_records)} products inserted")

    # 2. Generation Tasks (50)
    print("[2/9] Seeding 50 generation tasks...")
    task_types = ["image_only", "video_only", "image_and_video"]
    statuses = ["pending", "running", "completed", "failed"]
    task_records = []
    for i in range(50):
        product = random.choice(product_records)
        status = random.choices(statuses, weights=[15, 10, 50, 5], k=1)[0]
        task_records.append(GenerationTask(
            tenant_id=TENANT_ID,
            task_id=f"TASK-{uuid.uuid4().hex[:12].upper()}",
            product_id=product.id,
            task_type=random.choice(task_types),
            status=status,
            request_config={
                "platforms": random.sample(PLATFORMS, k=random.randint(1, 3)),
                "style": random.choice(["professional", "lifestyle", "bold"]),
                "count": random.randint(1, 5),
            },
            result={"images_generated": random.randint(0, 5), "videos_generated": random.randint(0, 2)} if status in ("completed", "failed") else {},
            quality_score=round(random.uniform(0.65, 0.99), 2) if status == "completed" else None,
            rag_enabled=random.choice([True, False]),
            created_at=_naive_now() - timedelta(days=random.randint(0, 30)),
            completed_at=_naive_now() if status == "completed" else None,
        ))
    session.add_all(task_records)
    await session.flush()
    print(f"  [OK] {len(task_records)} generation tasks inserted")

    # 3. Listing Products (25)
    print("[3/9] Seeding 25 listing products...")
    listing_products = []
    for i in range(25):
        sp = PRODUCTS_DATA[i % len(PRODUCTS_DATA)]
        sku = f"SKU-{sp[3][:3].upper()}-{1000+i:04d}"
        listing_products.append(ListingProductPO(
            tenant_id=TENANT_ID, sku=sku,
            title=f"{sp[1]} (Listing #{i+1})",
            description=sp[4], category=sp[3], brand=sp[2],
            price=round(random.uniform(9.99, 499.99), 2),
            weight=round(random.uniform(0.1, 15.0), 2),
            dimensions={"length_cm": random.randint(10, 60), "width_cm": random.randint(5, 40), "height_cm": random.randint(2, 30)},
            source_images=[{"url": f"https://cdn.example.com/{sku}/main.jpg", "type": "main"}],
            attributes={"condition": "new", "source": "amazon", "material": random.choice(["Plastic", "Metal", "Fabric", "Wood"]), "color": random.choice(["Black", "White", "Silver", "Blue"])},
            created_at=_naive_now() - timedelta(days=random.randint(0, 25)),
            updated_at=_naive_now(),
        ))
    session.add_all(listing_products)
    await session.flush()
    print(f"  [OK] {len(listing_products)} listing products inserted")

    # 4. Listing Tasks (25)
    print("[4/9] Seeding 25 listing tasks...")
    wf_states = ["import", "optimize_assets", "generate_copy", "compliance_check", "platform_push", "completed"]
    listing_tasks = []
    for lp in listing_products:
        status = random.choices(["pending", "running", "completed", "failed"], weights=[10, 5, 70, 15], k=1)[0]
        listing_tasks.append(ListingTaskPO(
            tenant_id=TENANT_ID, product_sku=lp.sku,
            target_platforms=random.sample(PLATFORMS, k=random.randint(1, 4)),
            status=status,
            workflow_state=random.choice(wf_states) if status != "pending" else "import",
            auto_execute=random.choice([True, False]),
            created_at=_naive_now() - timedelta(days=random.randint(0, 25)),
            updated_at=_naive_now(),
        ))
    session.add_all(listing_tasks)
    await session.flush()
    print(f"  [OK] {len(listing_tasks)} listing tasks inserted")

    # 5. Asset Packages
    print("[5/9] Seeding asset packages...")
    ap_count = 0
    for task in listing_tasks:
        for plat in random.sample(task.target_platforms, k=min(2, len(task.target_platforms))):
            session.add(AssetPackagePO(
                tenant_id=TENANT_ID, task_id=task.id, platform=plat,
                main_image=f"https://cdn.example.com/assets/{task.product_sku}/{plat}/main.jpg",
                variant_images=[f"https://cdn.example.com/assets/{task.product_sku}/{plat}/v1.jpg", f"https://cdn.example.com/assets/{task.product_sku}/{plat}/v2.jpg"],
                video_url=f"https://cdn.example.com/assets/{task.product_sku}/{plat}/promo.mp4" if random.random() > 0.5 else None,
                a_plus_images=[f"https://cdn.example.com/assets/{task.product_sku}/{plat}/aplus1.jpg"],
                created_at=_naive_now(),
            ))
            ap_count += 1
    print(f"  [OK] {ap_count} asset packages inserted")

    # 6. Copywriting Packages
    print("[6/9] Seeding copywriting packages...")
    languages = ["en", "de", "fr", "ja", "zh"]
    cp_count = 0
    for task in listing_tasks:
        for plat in random.sample(task.target_platforms, k=min(2, len(task.target_platforms))):
            session.add(CopywritingPackagePO(
                tenant_id=TENANT_ID, task_id=task.id, platform=plat,
                language=random.choice(languages),
                title=f"Premium Quality - {plat.upper()} Edition",
                bullet_points=["High-quality materials", "Easy to use", "100% satisfaction", "Free shipping", "2-year warranty"],
                description="Experience the difference with our premium product. Designed with cutting-edge technology.",
                search_terms=["premium", "quality", "bestseller"],
                created_at=_naive_now(),
            ))
            cp_count += 1
    print(f"  [OK] {cp_count} copywriting packages inserted")

    # 7. Compliance Reports
    print("[7/9] Seeding compliance reports...")
    cr_count = 0
    for task in listing_tasks:
        for plat in random.sample(task.target_platforms, k=1):
            session.add(ComplianceReportPO(
                tenant_id=TENANT_ID, task_id=task.id, platform=plat,
                report_data={"overall_score": random.randint(70, 100), "issues_found": random.randint(0, 3)},
                created_at=_naive_now(),
            ))
            cr_count += 1
    print(f"  [OK] {cr_count} compliance reports inserted")

    # 8. Task Results (for completed tasks)
    print("[8/9] Seeding task results...")
    tr_count = 0
    for task in listing_tasks:
        if task.status != "completed":
            continue
        for plat in task.target_platforms[:2]:
            session.add(TaskResultPO(
                tenant_id=TENANT_ID, task_id=task.id, platform=plat,
                success=random.random() > 0.15,
                result_data={"listing_id": f"{plat.upper()}-{random.randint(100000, 999999)}", "listing_url": f"https://{plat}.marketplace.com/listing/{random.randint(100000, 999999)}"},
                created_at=_naive_now(),
            ))
            tr_count += 1
    print(f"  [OK] {tr_count} task results inserted")

    # 9. Adapter Configs + Generated Assets
    print("[9/9] Seeding adapter configs + generated assets...")
    adapter_configs = [
        ("amazon_us", "shop-amz-us-001"), ("amazon_us", "shop-amz-us-002"), ("amazon_us", "shop-amz-us-003"),
        ("amazon_uk", "shop-amz-uk-001"), ("amazon_uk", "shop-amz-uk-002"),
        ("amazon_jp", "shop-amz-jp-001"), ("amazon_de", "shop-amz-de-001"),
        ("shopify", "shop-shopify-main"), ("shopify", "shop-shopify-outlet"),
        ("ebay", "shop-ebay-001"), ("ebay", "shop-ebay-002"), ("ebay", "shop-ebay-store1"),
        ("walmart", "shop-walmart-001"), ("walmart", "shop-walmart-002"),
        ("aliexpress", "shop-ali-001"), ("aliexpress", "shop-ali-002"),
        ("lazada", "shop-lazada-001"), ("lazada", "shop-lazada-002"),
        ("shopee", "shop-shopee-001"), ("shopee", "shop-shopee-002"),
        ("temu", "shop-temu-001"), ("rakuten", "shop-rakuten-001"),
        ("mercadolibre", "shop-ml-001"), ("noon", "shop-noon-001"),
    ]
    for platform, shop_id in adapter_configs:
        session.add(AdapterConfigPO(
            tenant_id=TENANT_ID, platform=platform, shop_id=shop_id,
            credentials={"access_key": f"AKID{random.randint(10000, 99999)}", "seller_id": f"S{random.randint(100000, 999999)}", "region": random.choice(["us-east-1", "eu-west-1", "ap-northeast-1"])},
            is_active=random.random() > 0.1,
            created_at=_naive_now(), updated_at=_naive_now(),
        ))
    print(f"  [OK] {len(adapter_configs)} adapter configs inserted")

    # Generated Assets
    completed_tasks = [t for t in task_records if t.status == "completed"]
    ga_count = 0
    for task in completed_tasks[:25]:
        for i in range(random.randint(1, 5)):
            session.add(GeneratedAssetPO(
                tenant_id=TENANT_ID, task_id=task.task_id, asset_type="image",
                provider=random.choice(["mock", "dashscope-image"]),
                url=f"https://cdn.example.com/generated/{task.task_id}/img_{i+1}.jpg",
                storage_key=f"output/{task.task_id}/img_{i+1}.jpg",
                storage_backend="local", mime_type="image/jpeg",
                file_size=random.randint(50000, 500000),
                width=random.choice([1024, 2048]), height=random.choice([1024, 2048]),
                status="completed", is_mock=random.random() > 0.5,
                created_at=_naive_now(), updated_at=_naive_now(),
            ))
            ga_count += 1
    print(f"  [OK] {ga_count} generated assets inserted")

    print(f"\n  All seeding complete! Committing...")


async def main():
    print("=" * 60)
    print("  Seeding Database (ORM)")
    print("=" * 60)

    async with get_db_session() as session:
        # Check existing
        from sqlalchemy import select, func
        count = (await session.execute(select(func.count()).select_from(Product).where(Product.tenant_id == TENANT_ID))).scalar()
        if count and count >= 40:
            print(f"\n  WARNING: {count} products exist. Clearing first...")
            for t in ['generated_assets', 'task_results', 'compliance_reports', 'copywriting_packages',
                       'asset_packages', 'adapter_configs', 'listing_tasks', 'listing_products',
                       'generation_tasks', 'products']:
                try:
                    await session.execute(text(f"DELETE FROM {t}"))
                except Exception:
                    pass
            await session.flush()
            print("  Cleared existing data.")

        await seed_all(session)
        await session.commit()

    print("  SUCCESS! Database is now seeded.\n")


if __name__ == "__main__":
    asyncio.run(main())
