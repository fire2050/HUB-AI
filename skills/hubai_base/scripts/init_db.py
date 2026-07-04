"""数据库初始化脚本 - 创建所有表并导入产品数据"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from db import HubAIDatabase

def init_database():
    """初始化数据库"""
    db = HubAIDatabase()
    
    # 1. 创建产品注册表
    db.execute('''
        CREATE TABLE IF NOT EXISTS product_registry (
            product_code TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            category_name TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            keywords TEXT,
            description TEXT,
            database_table TEXT,
            pricing_model TEXT,
            version TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. 创建报价策略表
    db.execute('''
        CREATE TABLE IF NOT EXISTS quotation_policy (
            policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_code TEXT UNIQUE NOT NULL,
            policy_name TEXT NOT NULL,
            customer_level TEXT,
            discount_rate REAL DEFAULT 1.0,
            priority INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            valid_from TEXT,
            valid_to TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. 创建报价单主表
    db.execute('''
        CREATE TABLE IF NOT EXISTS quotation (
            quotation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            quotation_no TEXT UNIQUE NOT NULL,
            customer_company TEXT,
            customer_level TEXT DEFAULT 'standard',
            contact_person TEXT,
            contact_phone TEXT,
            total_amount REAL DEFAULT 0.0,
            status TEXT DEFAULT 'draft',
            risk_flags TEXT,
            approval_required INTEGER DEFAULT 0,
            approval_status TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expired_at TEXT,
            notes TEXT
        )
    ''')
    
    # 4. 创建报价明细表
    db.execute('''
        CREATE TABLE IF NOT EXISTS quotation_line (
            line_id INTEGER PRIMARY KEY AUTOINCREMENT,
            quotation_no TEXT NOT NULL,
            product_code TEXT NOT NULL,
            product_name TEXT,
            performance_level TEXT,
            quantity INTEGER NOT NULL,
            unit_price_original REAL NOT NULL,
            discount_rate REAL DEFAULT 1.0,
            unit_price_final REAL NOT NULL,
            line_amount REAL NOT NULL,
            cost_price REAL,
            margin_rate REAL,
            additional_config TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (quotation_no) REFERENCES quotation(quotation_no)
        )
    ''')
    
    # 5. 创建价格历史表
    db.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT NOT NULL,
            performance_level TEXT,
            unit_price REAL NOT NULL,
            effective_date TEXT NOT NULL,
            created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 6. 创建审计日志表
    db.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            user_id TEXT,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print('✅ 数据库表创建完成')
    
    # 导入产品注册表数据
    products_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'products')
    imported_count = 0
    for filename in os.listdir(products_dir):
        if filename.endswith('.json'):
            with open(os.path.join(products_dir, filename), 'r', encoding='utf-8') as f:
                product = json.load(f)
                # 检查是否已存在
                existing = db.query_one(
                    'SELECT product_code FROM product_registry WHERE product_code = ?',
                    (product['code'],)
                )
                if not existing:
                    db.execute('''
                        INSERT INTO product_registry (
                            product_code, product_name, category, category_name,
                            skill_name, priority, keywords, description,
                            database_table, pricing_model, version
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        product['code'],
                        product['name'],
                        product['category'],
                        product['category_name'],
                        product['skill_name'],
                        product['priority'],
                        json.dumps(product['keywords'], ensure_ascii=False),
                        product['description'],
                        product['database_table'],
                        product['pricing_model'],
                        product['version']
                    ))
                    imported_count += 1
                    print(f'  + 导入产品: {product["name"]} ({product["code"]})')
    
    print(f'✅ 产品注册表导入完成: {imported_count} 个新产品')
    
    # 插入默认报价策略
    policies = [
        ('POLICY-STD-001', '标准客户折扣', 'standard', 1.00, 10),
        ('POLICY-NEW-001', '新客户折扣', 'new', 0.95, 20),
        ('POLICY-VIP-001', 'VIP客户折扣', 'vip', 0.90, 30),
        ('POLICY-STR-001', '战略客户折扣', 'strategic', 0.85, 40),
    ]
    
    for code, name, level, discount, priority in policies:
        existing = db.query_one(
            'SELECT policy_code FROM quotation_policy WHERE policy_code = ?',
            (code,)
        )
        if not existing:
            db.execute('''
                INSERT INTO quotation_policy (
                    policy_code, policy_name, customer_level, discount_rate, priority
                ) VALUES (?, ?, ?, ?, ?)
            ''', (code, name, level, discount, priority))
            print(f'  + 导入报价策略: {name}')
    
    print('✅ 报价策略导入完成')
    print('\n🎉 数据库初始化完成!')

if __name__ == '__main__':
    init_database()
