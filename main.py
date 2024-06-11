import os
import time
import traceback
import psycopg2
import pandas as pd
from colorama import Fore
import colorama
import numpy as np
from psycopg2 import sql
from dotenv import load_dotenv
from fashion_clip.fashion_clip import FashionCLIP

#--------------------- CONSTANTS --------------------------#

PROJECT_NAME = "MUSINSA CLONE BACKEND"
GENDERS = {
    "남성": "Male",
    "여성": "Female",
    "기타": "Other",
    "공용": "Unisex"
}

PRODUCT_FIELD_MAP = {
    "이름": "goods_name",
    "이미지 URL": "image_link",
    "성별": "sex",
    "카테고리": "category",
    "가격": "price",
    "수량": "stock_quantity"
}
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

colorama.init(autoreset=True)

def get_choice(*args, msg="", get_label=False):
    print(f"{msg if msg else '옵션을 선택해 주세요.'} (1-{len(args)}):")
    for i, arg in enumerate(args):
        print(f"  {Fore.YELLOW}{i+1}. {Fore.WHITE}{arg}")
    while True:
        try:
            c = int(input())
            if c not in range(1, len(args) + 1):
                print(f"{Fore.RED}유효한 입력이 아닙니다. 1과 {len(args)} 사이의 숫자를 입력해 주세요.")
            else:
                return args[c - 1] if get_label else c
        except ValueError:
            print(f"{Fore.RED}유효한 숫자를 입력해 주세요.")


def get_choice_list(options, msg="", get_label=False):
    print(f"{msg if msg else 'Please choose an option'}")
    for i, arg in enumerate(options):
        print(f"{i+1}. {arg}")
    while True:
        c = int(input(f"Enter your choice (1-{len(options)}): "))
        if c not in range(1, len(options)+1):
            print(f"Invalid choice. Please enter a number between 1 and {len(options)}.")
        else:
            return options[c - 1] if get_label else c

def get_numchoice():
    top_k = None
    while type(top_k) != int:
        try:
            top_k = int(input('얼마나 많은 수량을 찾으시겠습니까? (1~10): '))
        except:
            print('1~10 사이의 숫자를 입력해 주세요')
    return top_k

def clear():
    os.system('clear')
    # can vary depending on the OS
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
                raise InsufficientStockError("Not enough stock available")
                pass

            total_price = price * quantity
            if user_account < total_price:
                raise InsufficientFundsError("Insufficient funds in user account")
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

    def proceed(self, state="home"):
        input("계속하려면 엔터 키를 눌러주세요.")
        self.push(state)

    @staticmethod
    def route(protected):
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                clear()
                print('==============================================================================')
                print(f"\033[1mBKMS1-Team13 Project:{PROJECT_NAME}\033[0m")
                print('==============================================================================')
                print()
                if protected:
                    if not (self.authorized_user) and not (self.authorized_seller):
                        self.unauthorized("로그인되지 않았습니다. 로그인 페이지로 이동합니다.")
                        return
                    if self.authorized_user:
                        try:
                            self.authorized_user = backend.get_user(self.userID())
                        except NotFoundError:
                            self.unauthorized("사용자를 찾지 못했습니다. 로그인 페이지로 이동합니다.")
                            return
                    else:
                        try:
                            self.authorized_seller = backend.seller_info(self.sellerID())
                        except NotFoundError:
                            self.unauthorized("판매자를 찾지 못했습니다. 로그인 페이지로 이동합니다.")
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
    def unauthorized(self, msg=""):
        print(msg)
        choice = get_choice("고객 로그인", "고객 회원가입", "판매자 로그인")
        if choice == 1:
            self.push("signin")
        elif choice == 2:
            self.push("signup")
        elif choice == 3:
            self.push("seller_login")

    @protected
    def home(self):
        if self.authorized_user:
            print("반갑습니다!", self.authorized_user["username"], "고객님!")
            choice = get_choice("검색", "마이페이지", "로그아웃")
            if choice == 1:
                self.push("search_result")
            elif choice == 2:
                self.push("mypage")
            elif choice == 3:
                self.authorized_user = None
                self.push("home") # go back to login page
        else:
            print("반갑습니다,", self.authorized_seller["seller_name"], "판매자님!")
            choice = get_choice("제품 관리", "판매 관리", "로그아웃")
            if choice == 1:
                self.push("myproduct")
            elif choice == 2:
                self.push("sales_history")
            elif choice == 3:
                self.authorized_seller = None
                self.push("home") # go back to login page

    @public
    def signin(self):
        username = input("사용자 이름: ")
        password = input("비밀번호: ")
        self.authorized_user = backend.sign_in(username, password)
        self.push("home")

    @public
    def signup(self):
        username = input("사용자 이름: ")
        email = input("이메일: ")
        password = input("비밀번호: ")
        while True:
            password_confirm = input("비밀번호 확인: ")
            if password != password_confirm:
                print("비밀번호가 일치하지 않습니다. 다시 시도해 주세요")
            else:
                break
        sex = GENDERS[get_choice("남성", "여성", "기타", msg="성별", get_label=True)]
        birthday = input("생년월일 (YYYY-MM-DD): ")
        try:
            user_id = backend.sign_up(username, email, password, sex, birthday)
            print(f"새로운 계정이 등록되었습니다!: {user_id}")
        except:
            print("회원가입에 실패했습니다.")
        self.proceed()

    @public
    def seller_login(self):
        name = input("판매자 이름: ")
        password = input("비밀번호: ")
        self.authorized_seller = backend.seller_login(name, password)
        self.push("home")

    @protected
    def search_result(self):
        # TODO: sangwon - multiple search + purchase
        choice = get_choice("이름으로 검색", "스타일로 검색", "카테고리 필터", "성별 필터", "뒤로")
        user_id = self.authorized_user['user_id']
        if choice == 1:
            name = input('이름 입력: ')
            top_k = get_numchoice()
            products = backend.search_name(name, top_k, user_id)
        elif choice == 2:
            nl = input('원하시는 스타일을 자유롭게 입력해 주세요: ')
            top_k = get_numchoice()
            products = backend.search_nl(nl, top_k, user_id)
        elif choice == 3:
            sub_choice = get_choice('반소매', '니트/스웨터', '셔츠/블라우스', '트레이닝/조거', '캡/야구', '데님', '카디건', '코튼', '피케/카라', '나일론/코치', '슈트', '슈트/블레이저', '백팩', '토트백', '후드', '패션스니커즈화', get_label=True)
            top_k = get_numchoice()
            products = backend.search_category(sub_choice, top_k, user_id)
        elif choice == 4:
            sub_choice = get_choice('남성', '여성')
            sex = 'Male' if sub_choice==1 else 'Female'
            top_k = get_numchoice()
            products = backend.search_sex(sex, top_k, user_id)
        else:
            self.push("home")
            return
        # show result
        products = products[:top_k]
        for idx, product in enumerate(products):
            print("-----------------------------------------------")
            print(f"\033[1m#{idx + 1}\033[0m")
            print(f"이름: {product['goods_name']}")
            print(f"이미지 URL: {product['image_link']}")
            print(f"성별: {product['sex']}")
            print(f"카테고리: {product['category']}")
            print(f"가격: {product['price']}")
        print("-----------------------------------------------")
        # purchase
        while(1):
            choices = [product['goods_name'] for product in products]+['Nothing']
            choice = get_choice(*choices, msg="구매하실 품목을 선택해주세요.")
            if choice <= len(products):
                try:
                    quantity = int(input("수량을 입력해 주세요.: "))
                    user_id = self.userID()
                    product_id = products[choice-1]['product_id']
                    backend.purchase(user_id, product_id, quantity)
                    print("구매에 성공했습니다!")
                except NotFoundError as e:
                    print(f"구매에 실패했습니다.: {e}")
                except InsufficientStockError:
                    print("재고가 부족합니다.")
                except InsufficientFundsError:
                    print("잔액이 부족합니다.")
                except ValueError:
                    print("올바른 입력이 아닙니다. 유효한 아이디와 수량을 입력해 주세요.")
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")
                    traceback.print_exc()
                finally:
                    input("계속하려면 엔터 키를 눌러주세요.")
            else:
                break
        self.push("search_result")

    @protected
    def product_info(self):
        product_id = int(input("Enter the product ID: "))
        try:
            product = backend.product_info(product_id, self.sellerID())
            print(f"품목 ID: {product['product_id']}")
            print(f"이름: {product['goods_name']}")
            print(f"이미지 URL: {product['image_link']}")
            print(f"성별: {product['sex']}")
            print(f"카테고리: {product['category']}")
            print(f"가격: {product['price']}")
            print(f"판매자 ID: {self.sellerID()}")
            print(f"수량: {product['stock_quantity']}")
            print(f"추가된 날짜: {product['date_added']}")
        except NotFoundError:
            print("품목을 찾지 못했습니다.")
        self.proceed("myproduct")

    @protected
    def seller_info(self):
        seller_id = int(input("Enter the seller ID: "))
        try:
            seller = backend.seller_info(seller_id)
            print(f"판매자 ID: {seller['seller_id']}")
            print(f"판매자명: {seller['seller_name']}")
            print(f"이메일: {seller['contact_email']}")
            print(f"캐시: {seller['seller_account']}")
        except NotFoundError:
            print("판매자를 찾지 못했습니다.")
        self.proceed()

    @protected
    def register_product(self):
        goods_name = input("품목명을 입력해 주세요.: ")
        image_link = input("이미지 링크를 입력해주세요.: ")
        sex = GENDERS[get_choice("남성", "여성", "공용", msg="성별을 입력해 주세요.: ", get_label=True)]
        category = input("카테고리를 입력해 주세요.: ")
        price = float(input("가격을 입력해 주세요.: "))
        stock_quantity = int(input("수량을 입력해 주세요.: "))
        product_id = backend.register_product(goods_name, image_link, sex, category, price, self.sellerID(), stock_quantity)
        print(f"ID {product_id}로 새로운 품목을 등록했습니다.")
        self.proceed("myproduct")

    @protected
    def update_product(self):
        product_id = input("업데이트할 품목 ID를 입력해 주세요.: ")

        field_to_update = get_choice("이름", "이미지 URL", "성별", "카테고리", "가격", "수량", msg="무엇을 업데이트하시겠습니까?", get_label=True)
        fail = False

        if field_to_update == "이름":
            new_value = input("새로운 이름을 입력해 주세요.: ")
        elif field_to_update == "이미지 URL":
            new_value = input("새로운 이미지 URL을 입력해 주세요.: ")
        elif field_to_update == "성별":
            new_value = GENDERS[get_choice("남성", "여성", "공용", msg="성별을 입력해 주세요. ", get_label=True)]
        elif field_to_update == "카테고리":
            new_value = input("새로운 카테고리를 입력해 주세요. ")
        elif field_to_update == "가격":
            new_value = float(input("새로운 가격을 입력해 주세요.: "))
        elif field_to_update == "수량":
            new_value = int(input("새로운 수량을 입력해 주세요.: "))
        else:
            print("Invalid field selected.")
            fail = True

        if not fail:
            backend.update_product(product_id, PRODUCT_FIELD_MAP[field_to_update], new_value, self.sellerID())
            print(f"Product with ID {product_id} has been updated.")
        self.proceed("myproduct") # ADD: minchan

    @protected
    def delete_product(self):
        product_id = int(input("삭제할 품목 ID를 입력해 주세요: "))
        try:
            backend.delete_product(product_id, self.sellerID())
            print("품목이 삭제되었습니다.")
        except NotFoundError:
            print("품목을 찾을 수 없습니다.")
        self.proceed("myproduct") # ADD: minchan

    @protected
    def mypage(self):
        print("My Page")
        print("-----------------------------------------------")
        print(f"이름: {self.authorized_user['username']}")
        print(f"이메일: {self.authorized_user['email']}")
        print(f"성별: {self.authorized_user['sex']}")
        print(f"생일: {self.authorized_user['date_of_birth']}")
        print(f"캐시: {self.authorized_user['user_account']}")
        print("-----------------------------------------------")
        choice = get_choice("구매 기록", "검색 기록", "캐시 충전", "뒤로")
        if choice == 1:
            self.push("purchase_history")
        elif choice == 2:
            self.push("search_history")
        elif choice == 3:
            charge_amount = int(input("충전할 금액을 입력해 주세요.: "))
            if (charge_amount and charge_amount > 0 and charge_amount <= 2000000):
                backend.charge_account(self.userID(), charge_amount)
                print(f"{charge_amount} 만큼의 캐시가 충전되었습니다.")
            else:
                print("올바르지 않은 수량입니다. 1 이상 2000000개 이하 수량을 입력해 주세요.")
                self.proceed()
        elif choice == 4:
            self.push("home")

    @protected
    def myproduct(self):
        print("제품 관리")
        choice = get_choice("품목 확인", "품목 추가", "품목 업데이트", "품목 삭제" ,"뒤로")
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
        print("구매 기록")
        print("품목명 \t\t 가격 \t\t 수량 \t\t 구매날짜")
        print("--------------------------------------------------------")
        history = backend.get_purchase_history(self.userID())
        for product_name, price, quantity, purchase_date in history:
            print(f"{product_name} \t\t {price} \t\t {quantity} \t\t {purchase_date}")
        print("--------------------------------------------------------")
        self.proceed("mypage")

    @protected
    def search_history(self):
        print("검색 기록")
        print("검색어 \t\t 검색 날짜")
        print("--------------------------------------------------------")
        history = backend.get_search_history(self.userID())
        for query, search_date in history:
            print(f"{query} \t\t {search_date}")
        print("--------------------------------------------------------")
        self.proceed("mypage")

    @protected
    def sales_history(self):
        print("-----------------------------------------------")
        print(f"username: {self.authorized_seller['seller_name']}")
        print(f"account: {self.authorized_seller['seller_account']}")
        print("-----------------------------------------------")

        sales_history = backend.get_sales_history(self.sellerID())
        if sales_history:
            print("판매 기록")
            print("구매일자 | 품목 ID | 품목명 | 가격 | 잔여 수량 || 유저 ID | 유저이름 | 수량 ")
            print("-------------------------------------------------------------------------------------------------------")
            for row in sales_history:
                print(row)
                product_id, goods_name, price, stock_quantity, user_id, username, quantity, purchase_date = row
                print(f"{purchase_date} | {product_id} | {goods_name} | {price} | {stock_quantity} || {user_id} | {username} | {quantity}")
            print("-------------------------------------------------------------------------------------------------------")
        else:
            print("No sales history found.")
        self.proceed("home") # ADD: minchan

    def userID(self):
        return self.authorized_user['user_id']

    def sellerID(self):
        return self.authorized_seller['seller_id'] # ADD: minchan

    # Fill free to add or mutate skeleton methods as needed, with various parameters


if __name__ == "__main__":
    fe = FE()
    fe.run()
