import os
import time
import traceback
import psycopg2
import pandas as pd
import numpy as np
from psycopg2 import sql
from dotenv import load_dotenv
from fashion_clip.fashion_clip import FashionCLIP

#--------------------- CONSTANTS --------------------------#

PROJECT_NAME = "MUSINSA CLONE BACKEND"

#--------------------- DB CONNECTION ----------------------#
start_time = time.time()
print("DB Connecting...")
load_dotenv()

db_name = os.getenv('PG_DBNAME')
db_user = os.getenv('PG_USERNAME')
db_password = os.getenv('PG_PASSWORD')
db_host = os.getenv('PG_HOST')
db_port = os.getenv('PG_PORT')

conn = psycopg2.connect(
    dbname=db_name,
    user=db_user,
    password=db_password,
    host=db_host,
    port=db_port
)

cursor = conn.cursor()
print("DB Connected!", f"({round(time.time()-start_time, 2)}s.)")
# --------------------- EXCPETIONS ------------------------#
class NotFoundError(Exception):
    pass

# --------------------- RAW DATA --------------------------#
# load raw data as datframe (this works only for the NL search feature)
start_time = time.time()
print("RawData Loading...")
raw_df = pd.read_csv('./data/itemDB.csv')
raw_df['vector'] = raw_df['vector'].apply(lambda x: np.array(list(map(float, x.replace('[', '').replace(']','').replace(' ','').split(',')))))
image_embeddings = np.stack(raw_df['vector'].values)
categories = raw_df['category'].unique().tolist()
print("RawData Loaded!", f"({round(time.time()-start_time, 2)}s.)")
# --------------------- UTILS -----------------------------#
# load fashion-clip model
start_time = time.time()
print("FashionCLIP Loading...")
fclip = FashionCLIP('fashion-clip')
print("FashionCLIP Loaded!", f"({round(time.time()-start_time, 2)}s.)")

def get_choice(*args, msg="", get_label=False):
    print(f"{msg if msg else 'Please choose an option'}")
    for i, arg in enumerate(args):
        print(f"{i+1}. {arg}")
    while True:
        c = int(input(f"Enter your choice (1-{len(args)}): "))
        if c not in range(1, len(args)+1):
            print(f"Invalid choice. Please enter a number between 1 and {len(args)}.")
        else:
            return args[c - 1] if get_label else c

def get_numchoice():
    top_k = None
    while type(top_k) != int:
        try:
            top_k = int(input('How many products do you want to find? (1~10): '))
        except:
            print('You should type a number.')
    return top_k

print('==============================================================================')
# --------------------- BACKEND ----------------------------#

class BE:
    def get_user(self, user_id):
        cursor.execute("""
            select * from users where user_id = %s;""", (user_id,))
        result = cursor.fetchone()
        conn.commit()
        if not result:
            raise NotFoundError()
        return {
            "user_id": result[0],
            "username": result[1],
            "email": result[4],
            "sex": result[3],
            "date_of_birth": result[5],
            "account": result[6]
        }

    def sign_in(self, username, password):
        cursor.execute("""
            select * from users where username = %s and password = %s""", (username, password))
        result = cursor.fetchone()
        conn.commit()
        if not result:
            raise NotFoundError()
        return {
            "user_id": result[0],
            "username": result[1],
            "email": result[4],
            "sex": result[3],
            "date_of_birth": result[5],
            "account": result[6]
        }

    def sign_up(self, username, email, password, sex, birthday):
        cursor.execute("""
            insert into users (username, email, password, sex, account, date_of_birth)
            values (%s, %s, %s, %s, 0, %s)
            returning user_id""", (username, email, password, sex, birthday))
        conn.commit()
        return cursor.fetchone()[0]

    def charge_account(self, user_id, amount):
        cursor.execute("""
            update users set account = account + %s where user_id = %s""", (amount, user_id))
        conn.commit()

    def supplier_login(self):
        raise NotImplementedError()

    def add_searchlog(self, user_id, search_query):
        cursor.execute("""
            INSERT INTO searchlog (user_id, search_query)
            VALUES (%s, %s)
            RETURNING searchlog_id
        """, (user_id, search_query))
        conn.commit()
        return cursor.fetchone()[0]
    
    def add_searchresult(self, searchlog_id, product_id, rank):
        cursor.execute("""
            INSERT INTO searchresult (searchlog_id, product_id, rank)
            VALUES (%s, %s, %s)
            RETURNING result_id
        """, (searchlog_id, product_id, rank))
        conn.commit()
        return cursor.fetchone()[0]


    def search_nl(self, search_keyword, top_k, user_id):
        # search_keyword embedding
        text = ['a photo of ' + search_keyword]
        text_embeddings = fclip.encode_text(text, batch_size=32)
        text_embeddings = text_embeddings/np.linalg.norm(text_embeddings, ord=2, axis=-1, keepdims=True)
        # Cos Sim
        dot_product_single = np.dot(image_embeddings, text_embeddings.T)
        # get top_k
        indecies = np.flip(dot_product_single.argsort(0)[-top_k:]).flatten().tolist()
        goods_name = raw_df.loc[indecies, 'goods_name']
        products = []
        for gn in goods_name:
            cursor.execute(f"""
                SELECT * FROM product WHERE goods_name = '{gn}'""")
            result = cursor.fetchone()
            products.append({
                "product_id": result[0],
                "goods_name": result[1],
                "image_link": result[2],
                "sex": result[3],
                "category": result[4],
                "price": result[5]
            })
        # update searchlog 
        rank = 1
        for product in products:
            searchlog_id = self.add_searchlog(user_id=user_id, search_query=f"Search Style: {search_keyword}")
            product_id = product['product_id']
            self.add_searchresult(searchlog_id, product_id, rank)
            rank += 1

        return products

    def search_sex(self, sex, top_k, user_id): # split search and filter? or merge?
        cursor.execute("""
            SELECT * FROM product WHERE sex = %s""", (sex,))
        result = cursor.fetchall()
        if not result:
            raise NotFoundError()
        products = []
        for result in result:
            products.append({
                "product_id": result[0],
                "goods_name": result[1],
                "image_link": result[2],
                "sex": result[3],
                "category": result[4],
                "price": result[5]
            })
        # update searchlog
        rank = 1
        for product in products[:top_k]:
            searchlog_id = self.add_searchlog(user_id=user_id, search_query=f"Filter Sex: {sex}")
            product_id = product['product_id']
            self.add_searchresult(searchlog_id, product_id, rank)
            rank += 1

        return products
        
    def search_category(self, category, top_k, user_id):
        cursor.execute("""
            SELECT * FROM product WHERE category = %s""", (category,))
        result = cursor.fetchall()
        if not result:
            raise NotFoundError()
        products = []
        for result in result:
            products.append({
                "product_id": result[0],
                "goods_name": result[1],
                "image_link": result[2],
                "sex": result[3],
                "category": result[4],
                "price": result[5]
            })
        # update searchlog
        rank = 1
        for product in products[:top_k]:
            searchlog_id = self.add_searchlog(user_id=user_id, search_query=f"Filter Category: {category}")
            product_id = product['product_id']
            self.add_searchresult(searchlog_id, product_id, rank)
            rank += 1

        return products
    
    def search_name(self, name, top_k, user_id):
        cursor.execute(f"""
            SELECT * FROM product WHERE goods_name LIKE '%{name}%'""")
        result = cursor.fetchall()
        if not result:
            raise NotFoundError()
        products = []
        for result in result:
            products.append({
                "product_id": result[0],
                "goods_name": result[1],
                "image_link": result[2],
                "sex": result[3],
                "category": result[4],
                "price": result[5]
            })
        # update searchlog
        rank = 1
        for product in products[:top_k]:
            searchlog_id = self.add_searchlog(user_id=user_id, search_query=f"Search name: {name}")
            product_id = product['product_id']
            self.add_searchresult(searchlog_id, product_id, rank)
            rank += 1     
        return products

    def search(self): # split search and filter? or merge?
        raise NotImplementedError() # TODO: sangwon

    def brand_info(self, seller_id):
        cursor.execute("""
            SELECT * FROM sellers WHERE seller_id = %s""", (seller_id,))
        result = cursor.fetchone()
        conn.commit()
        if not result:
            raise NotFoundError()
        return {
            "seller_id": result[0],
            "seller_name": result[1],
            "contact_email": result[2],
            "contact_phone": result[3],
            "address": result[4],
            "date_joined": result[5]
        } # TODO: minchan

    def purchase(self):
        raise NotImplementedError() # TODO: hobin

    def product_info(self, product_id):
        cursor.execute("""
            SELECT * FROM products WHERE product_id = %s""", (product_id,))
        result = cursor.fetchone()
        conn.commit()
        if not result:
            raise NotFoundError()
        return {
            "product_id": result[0],
            "goods_name": result[1],
            "goods_link": result[2],
            "image_link": result[3],
            "sex": result[4],
            "category": result[5],
            "price": result[6],
            "seller_id": result[7],
            "stock_quantity": result[8],
            "date_added": result[9]
        } # TODO: minchan

    def register_product(self, goods_name, goods_link, image_link, sex, category, price, seller_id, stock_quantity):
        cursor.execute("""
            INSERT INTO products (goods_name, goods_link, image_link, sex, category, price, seller_id, stock_quantity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING product_id""", (goods_name, goods_link, image_link, sex, category, price, seller_id, stock_quantity))
        conn.commit()
        return cursor.fetchone()[0] # TODO: minchan

    def update_product(self, product_id, goods_name, goods_link, image_link, sex, category, price, seller_id, stock_quantity):
        cursor.execute("""
            UPDATE products
            SET goods_name = %s, goods_link = %s, image_link = %s, sex = %s, category = %s, price = %s, seller_id = %s, stock_quantity = %s
            WHERE product_id = %s""", (goods_name, goods_link, image_link, sex, category, price, seller_id, stock_quantity, product_id))
        conn.commit() # TODO: minchan

    def delete_product(self, product_id):
        cursor.execute("""
            DELETE FROM products WHERE product_id = %s""", (product_id,))
        conn.commit() # TODO: minchan

    def get_purchase_history(self):
        raise NotImplementedError() # TODO: dookyung

    def get_search_history(self):
        raise NotImplementedError() # TODO: dookyung

    # Fill free to add or mutate skeleton methods as needed, with various parameters

backend = BE()

# --------------------- FRONTEND ---------------------------#

class FE:
    global backend
    state = "home"
    prev_state = "home"
    authorized_user = None

    def run(self):
        while True:
            self.__getattribute__(self.state)()

    def push(self, state=""):
        self.prev_state = self.state
        self.state = state if state else self.state

    @staticmethod
    def route(protected):
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                if protected:
                    if not self.authorized_user:
                        print("Not authenticated. Fallback to login page.")
                        self.unauthorized()
                        return
                    try:
                        self.authorized_user = backend.get_user(self.userID())
                    except NotFoundError:
                        print("User not found. Fallback to login page.")
                        self.unauthorized()
                        return
                try:
                    func(self, *args, **kwargs)
                except NotImplementedError:
                    print(f"State {self.state} not implemented.")
                    self.state = self.prev_state
                except NotFoundError as e:
                    print(f"Not Found: {e}")
                    self.state = self.prev_state
                except Exception as e:
                    print(f"An unexcepted error occured: {e}")
                    traceback.print_exc()
                    self.state = self.prev_state
            return wrapper
        return decorator

    public = route(False)
    protected = route(True)

    @public
    def unauthorized(self):
        choice = get_choice("Customer Sign in", "Customer Sign up", "Supplier Login")
        if choice == 1:
            self.push("signin")
        elif choice == 2:
            self.push("signup")
        elif choice == 3:
            self.push("supplier_login")

    @protected
    def home(self):
        print("Welcome back", self.authorized_user["username"])
        choice = get_choice("Search", "My Page", "Logout")
        if choice == 1:
            self.push("search_result")
        elif choice == 2:
            self.push("mypage")
        elif choice == 3:
            self.authorized_user = None
            self.push("home") # go back to login page

    @public
    def signin(self):
        username = input("Enter your username: ")
        password = input("Enter your password: ")
        self.authorized_user = backend.sign_in(username, password)
        self.push("home")

    @public
    def signup(self):
        username = input("Enter your username: ")
        email = input("Enter your email: ")
        password = input("Enter your password: ")
        while True:
            password_confirm = input("Confirm your password: ")
            if password != password_confirm:
                print("Passwords do not match. Please try again.")
            else:
                break
        sex = get_choice("Male", "Female", "Other", msg="Enter your gender: ", get_label=True)
        birthday = input("Enter your birthday (YYYY-MM-DD): ")

        user_id = backend.sign_up(username, email, password, sex, birthday)
        print(f"New user ID registered!: {user_id}")
        self.push("home")

    @public
    def supplier_login(self):
        raise NotImplementedError() # TODO: minchan? dookyung?

    @protected
    def search_result(self):
        choice = get_choice("Search Name", "Search Style", "Filter Category", "Filter Sex")
        user_id = self.authorized_user['user_id']
        if choice == 1:
            name = input('Search with name: ')
            top_k = get_numchoice()
            products = backend.search_name(name, top_k, user_id)
        elif choice == 2:
            nl = input('Search with style you want (Natural Language supported): ')
            top_k = get_numchoice()
            products = backend.search_nl(nl, top_k, user_id)
        elif choice == 3:
            categories = ['반소매', '니트/스웨터', '셔츠/블라우스', '트레이닝/조거', '캡/야구', '데님', '카디건', '코튼', '피케/카라', '나일론/코치', '슈트', '슈트/블레이저', '백팩', '토트백', '후드', '패션스니커즈화']
            sub_choice = get_choice('반소매', '니트/스웨터', '셔츠/블라우스', '트레이닝/조거', '캡/야구', '데님', '카디건', '코튼', '피케/카라', '나일론/코치', '슈트', '슈트/블레이저', '백팩', '토트백', '후드', '패션스니커즈화')
            top_k = get_numchoice()
            products = backend.search_category(categories[sub_choice], top_k, user_id)
        elif choice == 4:
            sub_choice = get_choice('Male', 'Female')
            sex = 'Male' if sub_choice==1 else 'Female'
            top_k = get_numchoice()
            products = backend.search_sex(sex, top_k, user_id)
        # show result
        products = products[:top_k]
        for product in products:
            print("-----------------------------------------------")
            print(f"Product Name: {product['goods_name']}")
            print(f"Image: {product['image_link']}")
            print(f"Sex: {product['sex']}")
            print(f"Category: {product['category']}")
            print(f"Price: {product['price']}")    
        print("-----------------------------------------------")
        self.push("home")

    @protected
    def product_info(self):
        product_id = int(input("Enter the product ID: "))
        try:
            product = backend.product_info(product_id)
            print(f"Product ID: {product['product_id']}")
            print(f"Product Name: {product['goods_name']}")
            print(f"Product Link: {product['goods_link']}")
            print(f"Image Link: {product['image_link']}")
            print(f"Sex: {product['sex']}")
            print(f"Category: {product['category']}")
            print(f"Price: {product['price']}")
            print(f"Seller ID: {product['seller_id']}")
            print(f"Stock Quantity: {product['stock_quantity']}")
            print(f"Date Added: {product['date_added']}")
        except NotFoundError:
            print("Product not found.")
        self.push("home") # TODO: minchan

    @protected
    def brand_info(self):
        seller_id = int(input("Enter the seller ID: "))
        try:
            seller = backend.brand_info(seller_id)
            print(f"Seller ID: {seller['seller_id']}")
            print(f"Seller Name: {seller['seller_name']}")
            print(f"Contact Email: {seller['contact_email']}")
            print(f"Contact Phone: {seller['contact_phone']}")
            print(f"Address: {seller['address']}")
            print(f"Date Joined: {seller['date_joined']}")
        except NotFoundError:
            print("Sellor not found.")
        self.push("home") # TODO: minchan

    @protected
    def purchase(self):
        raise NotImplementedError() # TODO: hobin
        # 별도의 route가 필요한가?

    @protected
    def register_product(self):
        goods_name = input("Enter the product name: ")
        goods_link = input("Enter the product link: ")
        image_link = input("Enter the image link: ")
        sex = get_choice("Male", "Female", "Unisex", msg="Enter the sex: ", get_label=True)
        category = input("Enter the category: ")
        price = float(input("Enter the price: "))
        seller_id = int(input("Enter the seller ID: "))
        stock_quantity = int(input("Enter the stock quantity: "))
        product_id = backend.register_product(goods_name, goods_link, image_link, sex, category, price, seller_id, stock_quantity)
        print(f"New product registered with ID: {product_id}")
        self.push("home") # TODO: minchan
    
    @protected
    def delete_product(self):
        product_id = int(input("Enter the product ID to delete: "))
        try:
            backend.delete_product(product_id)
            print("Product deleted successfully.")
        except NotFoundError:
            print("Product not found.")
        self.push("home") # ADD: minchan

    @protected
    def mypage(self):
        print("My Page")
        print("-----------------------------------------------")
        print(f"username: {self.authorized_user['username']}")
        print(f"email: {self.authorized_user['email']}")
        print(f"joined: {self.authorized_user['date_joined']}")
        print(f"gender: {self.authorized_user['sex']}")
        print(f"birthday: {self.authorized_user['date_of_birth']}")
        print(f"account: {self.authorized_user['account']}")
        print("-----------------------------------------------")
        choice = get_choice("Purchase History", "Search History", "Charge Account", "Back")
        if choice == 1:
            self.push("purchase_history")
        elif choice == 2:
            self.push("search_history")
        elif choice == 3:
            charge_amount = int(input("Enter the amount to charge: "))
            if (charge_amount and charge_amount > 0 and charge_amount <= 2000000):
                backend.charge_account(self.userID(), charge_amount)
                print(f"Account charged by {charge_amount}.")
            else:
                print("Invalid amount. Please enter a number between 1 and 2,000,000.")
        elif choice == 4:
            self.push("home")

    @protected
    def purchase_history(self):
        raise NotImplementedError() # TODO: dookyung

    @protected
    def search_history(self):
        raise NotImplementedError() # TODO: dookyung

    def userID(self):
        return self.authorized_user['user_id']

    # Fill free to add or mutate skeleton methods as needed, with various parameters


if __name__ == "__main__":
    print(f"BKMS1-Team13 Project:{PROJECT_NAME}")
    fe = FE()
    fe.run()

