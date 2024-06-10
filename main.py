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

class InsufficientStockError(Exception):
    pass

class InsufficientFundsError(Exception):
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
            "sex": result[3],
            "email": result[4],
            "date_of_birth": result[5],
            "user_account": result[6]
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
            "sex": result[3],
            "email": result[4],
            "date_of_birth": result[5],
            "user_account": result[6]
        }

    def sign_up(self, username, email, password, sex, birthday):
        cursor.execute("""
            insert into users (username, email, password, sex, date_of_birth)
            values (%s, %s, %s, %s, %s)
            returning user_id""", (username, email, password, sex, birthday))
        conn.commit()
        return cursor.fetchone()[0]

    def charge_account(self, user_id, amount):
        cursor.execute("""
            update users set user_account = user_account + %s where user_id = %s""", (amount, user_id))
        conn.commit()

    def seller_login(self, seller_name, password):
        cursor.execute("""
            select * from seller where seller_name = %s and password = %s""", (seller_name, password))
        result = cursor.fetchone()
        conn.commit()
        if not result:
            raise NotFoundError()
        return {
            "seller_id": result[0],
            "seller_name": result[1],
            "contact_email": result[3],
            "seller_account": result[4]
        }

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
        raise NotImplementedError()

    def seller_info(self, seller_id):
        cursor.execute("""
            SELECT * FROM seller WHERE seller_id = %s""", (seller_id,))
        result = cursor.fetchone()
        conn.commit()
        if not result:
            raise NotFoundError()
        return {
            "seller_id": result[0],
            "seller_name": result[1],
            "contact_email": result[3],
            "seller_account": result[4]
        }

    def purchase(self, user_id, product_id, quantity):
        try:
            cursor.execute("""
                SELECT p.stock_quantity, p.price, p.seller_id, u.user_account
                FROM product p
                JOIN users u ON u.user_id = %s
                WHERE p.product_id = %s
            """, (user_id, product_id))
            result = cursor.fetchone()
            if not result:
                raise NotFoundError("Product or User not found")

            stock_quantity, price, seller_id, user_account = result
            if stock_quantity < quantity:
                # raise InsufficientStockError("Not enough stock available")
                pass

            total_price = price * quantity
            if user_account < total_price:
                # raise InsufficientFundsError("Insufficient funds in user account")
                pass

            cursor.execute("BEGIN")

            try:
                cursor.execute("UPDATE users SET user_account = user_account - %s WHERE user_id = %s", (total_price, user_id))
                cursor.execute("UPDATE seller SET seller_account = seller_account + %s WHERE seller_id = %s", (total_price, seller_id))
                cursor.execute("UPDATE product SET stock_quantity = stock_quantity - %s WHERE product_id = %s", (quantity, product_id))
                cursor.execute("""
                    INSERT INTO buylog (user_id, product_id, quantity)
                    SELECT u.user_id, p.product_id, %s
                    FROM users u
                    INNER JOIN product p ON p.product_id = %s
                    WHERE u.user_id = %s
                """, (quantity, product_id, user_id))
                cursor.execute("COMMIT")

            except Exception as e:
                cursor.execute("ROLLBACK")
                raise e

        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Error during purchase: {error}")
            raise error

    def product_info(self, product_id, seller_id):
        cursor.execute("""
            SELECT * FROM product WHERE product_id = %s AND seller_id = %s""",
            (product_id, seller_id))
        result = cursor.fetchone()
        conn.commit()
        if not result:
            raise NotFoundError()
        return {
            "product_id": result[0],
            "goods_name": result[1],
            "image_link": result[2],
            "sex": result[3],
            "category": result[4],
            "price": result[5],
            "seller_id": seller_id,  # Update to use self.authorized_seller['seller_id']
            "stock_quantity": result[7],
            "date_added": result[8]
        }

    def register_product(self, goods_name, image_link, sex, category, price, seller_id, stock_quantity):
        cursor.execute("""
            INSERT INTO product (goods_name, image_link, sex, category, price, seller_id, stock_quantity)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING product_id""",
            (goods_name, image_link, sex, category, price, seller_id, stock_quantity))
        conn.commit()
        return cursor.fetchone()[0]

    def update_product(self, product_id, field_name, new_value, seller_id):
        try:
            query = f"UPDATE product SET {field_name} = %s WHERE product_id = %s AND seller_id = %s"
            cursor.execute(query, (new_value, product_id, seller_id))
            if cursor.rowcount == 0:
                raise NotFoundError("Product not found or unauthorized to update this product.")
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"An error occurred: {e}")
            raise

    def delete_product(self, product_id, seller_id):
        try:
            cursor.execute("""
                DELETE FROM product WHERE product_id = %s AND seller_id = %s""",
                (product_id, seller_id))
            if cursor.rowcount == 0:
                raise NotFoundError()
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise

    def get_purchase_history(self, user_id):
        cursor.execute("""SELECT goods_name, price, quantity, purchase_date FROM purchase_history WHERE user_id = %s ORDER BY purchase_date DESC;""", (user_id,))
        return cursor.fetchall()

    def get_sales_history(self, seller_id):
        cursor.execute("""
            SELECT ph.user_id, ph.username, ph.product_id, ph.goods_name, ph.price, ph.stock_quantity, ph.quantity, 
                TO_CHAR(ph.purchase_date, 'YYYY-MM-DD HH24:MI') AS purchase_date
            FROM sales_history ph
            WHERE ph.product_id IN (
                SELECT product_id 
                FROM product 
                WHERE seller_id = %s
            )
            ORDER BY ph.purchase_date DESC;
        """, (seller_id,))
        return cursor.fetchall() # ADD: minchan

    def get_search_history(self, user_id):
        cursor.execute("""SELECT search_query, search_date FROM user_search_history WHERE user_id = %s ORDER BY search_date DESC;""", (user_id,))
        return cursor.fetchall()

    # Fill free to add or mutate skeleton methods as needed, with various parameters

backend = BE()

# --------------------- FRONTEND ---------------------------#

class FE:
    global backend
    state = "home"
    prev_state = "home"
    authorized_user = None
    authorized_seller = None

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
                    if not (self.authorized_user) and not (self.authorized_seller):
                        print("Not authenticated. Fallback to login page.")
                        self.unauthorized()
                        return
                    if self.authorized_user:
                        try:
                            self.authorized_user = backend.get_user(self.userID())
                        except NotFoundError:
                            print("User not found. Fallback to login page.")
                            self.unauthorized()
                            return
                    else:
                        try:
                            self.authorized_seller = backend.seller_info(self.sellerID())
                        except NotFoundError:
                            print("Seller not found. Fallback to login page.")
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
        choice = get_choice("Customer Sign in", "Customer Sign up", "Seller Sign in")
        if choice == 1:
            self.push("signin")
        elif choice == 2:
            self.push("signup")
        elif choice == 3:
            self.push("seller_login")

    @protected
    def home(self):
        if self.authorized_user:
            print("Welcome back", self.authorized_user["username"])
            choice = get_choice("Search", "My Page", "Purchase", "Logout")
            if choice == 1:
                self.push("search_result")
            elif choice == 2:
                self.push("mypage")
            elif choice == 3:
                self.push("purchase")
            elif choice == 4:
                self.authorized_user = None
                self.push("home") # go back to login page
        else:
            print("Welcome back", self.authorized_seller["seller_name"])
            choice = get_choice("Product management", "Sales management", "Logout")
            if choice == 1:
                self.push("myproduct")
            elif choice == 2:
                self.push("sales_history")
            elif choice == 3:
                self.authorized_seller = None
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
    def seller_login(self):
        name = input("Enter your sellername: ")
        password = input("Enter your password: ")
        self.authorized_seller = backend.seller_login(name, password)
        self.push("home")

    @protected
    def search_result(self):
        # TODO: sangwon - multiple search + purchase
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
            product = backend.product_info(product_id, self.sellerID())
            print(f"Product ID: {product['product_id']}")
            print(f"Product Name: {product['goods_name']}")
            print(f"Image Link: {product['image_link']}")
            print(f"Sex: {product['sex']}")
            print(f"Category: {product['category']}")
            print(f"Price: {product['price']}")
            print(f"Seller ID: {self.sellerID()}")
            print(f"Stock Quantity: {product['stock_quantity']}")
            print(f"Date Added: {product['date_added']}")
        except NotFoundError:
            print("Product not found.")
        self.push("myproduct")

    @protected
    def seller_info(self):
        seller_id = int(input("Enter the seller ID: "))
        try:
            seller = backend.seller_info(seller_id)
            print(f"Seller ID: {seller['seller_id']}")
            print(f"Seller Name: {seller['seller_name']}")
            print(f"Contact Email: {seller['contact_email']}")
            print(f"Seller account: {seller['seller_account']}")
        except NotFoundError:
            print("Sellor not found.")
        self.push("home")

    @protected
    def purchase(self):
        try:
            product_id = int(input("Enter product ID to purchase: "))
            quantity = int(input("Enter quantity to purchase: "))
            user_id = self.userID()
            backend.purchase(user_id, product_id, quantity)
            print("Purchase successful!")
        except (NotFoundError, InsufficientStockError, InsufficientFundsError) as e:
            print(f"Purchase failed: {e}")
        except ValueError:
            print("Invalid input. Please enter valid product ID and quantity.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            traceback.print_exc()
        finally:
            self.push("home")

    @protected
    def register_product(self):
        goods_name = input("Enter the product name: ")
        image_link = input("Enter the image link: ")
        sex = get_choice("Male", "Female", "Unisex", msg="Enter the sex: ", get_label=True)
        category = input("Enter the category: ")
        price = float(input("Enter the price: "))
        stock_quantity = int(input("Enter the stock quantity: "))
        product_id = backend.register_product(goods_name, image_link, sex, category, price, self.sellerID(), stock_quantity)
        print(f"New product registered with ID: {product_id}")
        self.push("myproduct")

    @protected
    def update_product(self):
        product_id = input("Enter the product ID to update: ")

        print("Which field would you like to update?")
        field_to_update = get_choice("goods_name", "image_link", "sex", "category", "price", "stock_quantity", msg="Enter the field: ", get_label=True)

        if field_to_update == "goods_name":
            new_value = input("Enter the new product name: ")
        elif field_to_update == "image_link":
            new_value = input("Enter the new image link: ")
        elif field_to_update == "sex":
            new_value = get_choice("Male", "Female", "Unisex", msg="Enter the sex: ", get_label=True)
        elif field_to_update == "category":
            new_value = input("Enter the new category: ")
        elif field_to_update == "price":
            new_value = float(input("Enter the new price: "))
        elif field_to_update == "stock_quantity":
            new_value = int(input("Enter the new stock quantity: "))
        else:
            print("Invalid field selected.")
            return

        backend.update_product(product_id, field_to_update, new_value, self.sellerID())
        print(f"Product with ID {product_id} has been updated.")
        self.push("myproduct") # ADD: minchan

    @protected
    def delete_product(self):
        product_id = int(input("Enter the product ID to delete: "))
        try:
            backend.delete_product(product_id, self.sellerID())
            print("Product deleted successfully.")
        except NotFoundError:
            print("Product not found.")
        self.push("myproduct") # ADD: minchan

    @protected
    def mypage(self):
        print("My Page")
        print("-----------------------------------------------")
        print(f"username: {self.authorized_user['username']}")
        print(f"email: {self.authorized_user['email']}")
        print(f"gender: {self.authorized_user['sex']}")
        print(f"birthday: {self.authorized_user['date_of_birth']}")
        print(f"account: {self.authorized_user['user_account']}")
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
    def myproduct(self):
        print("Product managment")
        choice = get_choice("Check product", "Add product", "Update product", "Delete product" ,"Back")
        if choice == 1:
            self.push("product_info")
        elif choice == 2:
            self.push("register_product")
        elif choice == 3:
            self.push("update_product")
        elif choice == 4:
            self.push("delete_product")
        elif choice == 5:
            self.push("home") # ADD: minchan

    @protected
    def purchase_history(self):
        print("Purchase History")
        print("Product Name \t\t Price \t\t Quantity \t\t Purchase Date")
        print("--------------------------------------------------------")
        history = backend.get_purchase_history(self.userID())
        for product_name, price, quantity, purchase_date in history:
            print(f"{product_name} \t\t {price} \t\t {quantity} \t\t {purchase_date}")
        print("--------------------------------------------------------")
        self.push("mypage")

    @protected
    def search_history(self):
        print("Search History")
        print("Query \t\t Purchase Date")
        print("--------------------------------------------------------")
        history = backend.get_search_history(self.userID())
        for query, search_date in history:
            print(f"{query} \t\t {search_date}")
        print("--------------------------------------------------------")
        self.push("mypage")

    @protected
    def sales_history(self):
        print("-----------------------------------------------")
        print(f"username: {self.authorized_seller['seller_name']}")
        print(f"account: {self.authorized_seller['seller_account']}")
        print("-----------------------------------------------")

        sales_history = backend.get_sales_history(self.sellerID())
        if sales_history:
            print("Sales History")
            print("Purchase Date | Product ID | Product Name | Price | Stock Quantity | User ID | Username | Quantity ")
            print("-------------------------------------------------------------------------------------------------------")
            for row in sales_history:
                product_id, goods_name, price, stock_quantity, user_id, username, quantity, purchase_date = row
                print(f"{purchase_date} | {product_id} | {goods_name} | {price} | {stock_quantity} | {user_id} | {username} | {quantity}")
            print("-------------------------------------------------------------------------------------------------------")
        else:
            print("No sales history found.")
        self.push("home") # ADD: minchan

    def userID(self):
        return self.authorized_user['user_id']

    def sellerID(self):
        return self.authorized_seller['seller_id'] # ADD: minchan

    # Fill free to add or mutate skeleton methods as needed, with various parameters


if __name__ == "__main__":
    print(f"BKMS1-Team13 Project:{PROJECT_NAME}")
    fe = FE()
    fe.run()
