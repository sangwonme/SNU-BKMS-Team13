import os
import traceback
import psycopg2
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import random

PROJECT_NAME = "MUSINSA CLONE BACKEND"

load_dotenv()

db_name = os.getenv('PG_DBNAME')
db_user = os.getenv('PG_USERNAME')
db_password = os.getenv('PG_PASSWORD')
db_host = os.getenv('PG_HOST')
db_port = os.getenv('PG_PORT')

try:
    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )
    cursor = conn.cursor()
    print("Database connection established.")
except Exception as e:
    print("Failed to connect to the database.")
    print(traceback.format_exc())

def create_tables():
    try:
        # Drop tables if they exist
        cursor.execute("DROP TABLE IF EXISTS searchresult CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS searchlog CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS buylog CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS product CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS users CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS seller CASCADE;")

        cursor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sex_type') THEN
                CREATE TYPE sex_type AS ENUM ('Male', 'Female', 'Other');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'product_sex_type') THEN
                CREATE TYPE product_sex_type AS ENUM ('Male', 'Female', 'Unisex');
            END IF;
        END
        $$;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            sex sex_type NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            date_of_birth DATE,
            user_account VARCHAR(100) NOT NULL UNIQUE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS seller (
            seller_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            seller_name VARCHAR(100) NOT NULL,
            contact_email VARCHAR(100) NOT NULL UNIQUE,
            seller_account VARCHAR(100) NOT NULL UNIQUE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS product (
            product_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            goods_name VARCHAR(255) NOT NULL,
            image_link VARCHAR(255) NOT NULL,
            sex product_sex_type NOT NULL,
            category VARCHAR(100) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            seller_id INT NOT NULL REFERENCES seller(seller_id),
            stock_quantity INT NOT NULL,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS searchlog (
            searchlog_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(user_id),
            search_query VARCHAR(255) NOT NULL,
            search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS searchresult (
            result_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            searchlog_id INT NOT NULL REFERENCES searchlog(searchlog_id),
            product_id INT NOT NULL REFERENCES product(product_id),
            rank INT NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS buylog (
            buylog_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(user_id),
            product_id INT NOT NULL REFERENCES product(product_id),
            quantity INT NOT NULL,
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        print("All tables created successfully.")
    except Exception as e:
        print("Failed to create tables.")
        print(traceback.format_exc())
        conn.rollback()

def insert_seller_data():
    try:
        sellers = [
            ('Nike', 'contact@nike.com', '1234-5678'),
            ('Adidas', 'contact@adidas.com', '2345-6789'),
            ('Zara', 'contact@zara.com', '3456-7890'),
            ('H&M', 'contact@hm.com', '4567-8901'),
            ('Uniqlo', 'contact@uniqlo.com', '5678-9012'),
            ('Gap', 'contact@gap.com', '6789-0123'),
            ('Levis', 'contact@levis.com', '7890-1234'),
            ('Gucci', 'contact@gucci.com', '8901-2345'),
            ('Prada', 'contact@prada.com', '9012-3456'),
            ('Chanel', 'contact@chanel.com', '0123-4567')
        ]
        for seller_name, contact_email, seller_account in sellers:
            cursor.execute("""
            INSERT INTO seller (seller_name, contact_email, seller_account)
            VALUES (%s, %s, %s)
            """, (seller_name, contact_email, seller_account))
            # ON CONFLICT (contact_email, seller_account) DO NOTHING;
        conn.commit()
        print("Seller data inserted successfully.")
    except Exception as e:
        print("Failed to insert seller data.")
        print(traceback.format_exc())
        conn.rollback()

def insert_user_data():
    try:
        users = [
            ('johndoe1', 'password123', 'Male', 'john1@example.com', '1990-01-01', '0001-1111'),
            ('janedoe2', 'password456', 'Female', 'jane2@example.com', '1992-02-02', '0002-2222'),
            ('jacksmith3', 'password789', 'Male', 'jack3@example.com', '1988-03-03', '0003-3333'),
            ('emilyjones4', 'password012', 'Female', 'emily4@example.com', '1995-04-04', '0004-4444'),
            ('michaeljohnson5', 'password345', 'Male', 'michael5@example.com', '1985-05-05', '0005-5555'),
            ('sarahbrown6', 'password678', 'Female', 'sarah6@example.com', '1991-06-06', '0006-6666'),
            ('davidwilliams7', 'password901', 'Male', 'david7@example.com', '1993-07-07', '0007-7777'),
            ('amandamiller8', 'password234', 'Female', 'amanda8@example.com', '1989-08-08', '0008-8888'),
            ('robertmoore9', 'password567', 'Male', 'robert9@example.com', '1994-09-09', '0009-9999'),
            ('lisataylor10', 'password890', 'Female', 'lisa10@example.com', '1987-10-10', '0010-1010')
        ]
        for username, password, sex, email, date_of_birth, user_account in users:
            cursor.execute("""
            INSERT INTO users (username, password, sex, email, date_of_birth, user_account)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, password, sex, email, date_of_birth, user_account))
            # ON CONFLICT (username, email, user_account) DO NOTHING;
        conn.commit()
        print("User data inserted successfully.")
    except Exception as e:
        print("Failed to insert user data.")
        print(traceback.format_exc())
        conn.rollback()

def insert_example_data():
    try:
        cursor.execute("""
        INSERT INTO searchlog (user_id, search_query)
        VALUES
        (1, 'running shoes'),
        (2, 'casual sneakers'),
        (3, 'dresses'),
        (4, 'jackets'),
        (5, 't-shirts'),
        (6, 'jeans'),
        (7, 'sunglasses'),
        (8, 'handbags'),
        (9, 'watches'),
        (10, 'skirts');
        """)

        cursor.execute("""
        INSERT INTO searchresult (searchlog_id, product_id, rank)
        VALUES
        ((SELECT searchlog_id FROM searchlog WHERE user_id = 1 LIMIT 1), 1, 1),
        ((SELECT searchlog_id FROM searchlog WHERE user_id = 2 LIMIT 1), 2, 1),
        ((SELECT searchlog_id FROM searchlog WHERE user_id = 3 LIMIT 1), 3, 1),
        ((SELECT searchlog_id FROM searchlog WHERE user_id = 4 LIMIT 1), 4, 1),
        ((SELECT searchlog_id FROM searchlog WHERE user_id = 5 LIMIT 1), 5, 1),
        ((SELECT searchlog_id FROM searchlog WHERE user_id = 6 LIMIT 1), 6, 1),
        ((SELECT searchlog_id FROM searchlog WHERE user_id = 7 LIMIT 1), 7, 1),
        ((SELECT searchlog_id FROM searchlog WHERE user_id = 8 LIMIT 1), 8, 1),
        ((SELECT searchlog_id FROM searchlog WHERE user_id = 9 LIMIT 1), 9, 1),
        ((SELECT searchlog_id FROM searchlog WHERE user_id = 10 LIMIT 1), 10, 1);
        """)

        cursor.execute("""
        INSERT INTO buylog (user_id, product_id, quantity)
        VALUES
        (1, 1, 2),
        (2, 2, 1),
        (3, 3, 3),
        (4, 4, 2),
        (5, 5, 1),
        (6, 6, 3),
        (7, 7, 2),
        (8, 8, 1),
        (9, 9, 2),
        (10, 10, 1);
        """)

        conn.commit()
        print("Example data inserted successfully.")
    except Exception as e:
        print("Failed to insert example data.")
        print(traceback.format_exc())
        conn.rollback()

def insert_data_from_csv():
    try:
        df = pd.read_csv('Data/itemDB.csv').dropna()

        print("CSV Columns:", df.columns.tolist())

        sex_mapping = {'M': 'Male', 'W': 'Female', 'MW': 'Unisex', '': 'Unixex'}

        df['sex'] = df['sex'].map(sex_mapping)

        for index, row in df.iterrows():
            price = round(random.uniform(10, 1000), 2)
            seller_id = random.randint(1, 10)
            stock_quantity = random.randint(1, 100)
            cursor.execute("""
            INSERT INTO product (goods_name, image_link, sex, category, price, seller_id, stock_quantity, date_added)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id) DO NOTHING;
            """, (row['goods_name'], row['image_link'], row['sex'], row['category'], price, seller_id, stock_quantity, datetime.now()))

        conn.commit()
        print("CSV data inserted successfully.")
    except KeyError as e:
        print(f"KeyError: {e}. Please check if the column names in the CSV file match the expected column names.")
        conn.rollback()
    except Exception as e:
        print("Failed to insert data from CSV.")
        print(traceback.format_exc())
        conn.rollback()

if __name__ == "__main__":
    create_tables()
    insert_seller_data()
    insert_user_data()
    insert_data_from_csv()
    insert_example_data()
    
    cursor.close()
    conn.close()
