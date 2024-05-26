import os
import traceback
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

#--------------------- CONSTANTS --------------------------#

PROJECT_NAME = "MUSINSA CLONE BACKEND"

#--------------------- DB CONNECTION ----------------------#
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

# --------------------- EXCPETIONS ------------------------#
class NotFoundError(Exception):
    pass

# --------------------- UTILS -----------------------------#

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
            "email": result[2],
            "date_joined": result[4],
            "sex": result[5],
            "date_of_birth": result[6],
            "account": result[7]
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
            "email": result[2],
            "date_joined": result[4],
            "sex": result[5],
            "date_of_birth": result[6],
            "account": result[7]
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

    def search(self): # split search and filter? or merge?
        raise NotImplementedError() # TODO: sangwon

    def brand_info(self):
        raise NotImplementedError() # TODO: minchan

    def purchase(self):
        raise NotImplementedError() # TODO: hobin

    def product_info(self):
        raise NotImplementedError() # TODO: minchan

    def register_product(self):
        raise NotImplementedError() # TODO: minchan

    def update_product(self):
        raise NotImplementedError() # TODO: minchan

    def delete_product(self):
        raise NotImplementedError() # TODO: minchan

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
        raise NotImplementedError() # TODO: sangwon
        # merge of split search + filter?

    @protected
    def product_info(self):
        raise NotImplementedError() # TODO: minchan

    @protected
    def brand_info(self):
        raise NotImplementedError() # TODO: minchan

    @protected
    def purchase(self):
        raise NotImplementedError() # TODO: hobin
        # 별도의 route가 필요한가?

    @protected
    def register_product(self):
        raise NotImplementedError() # TODO: minchan

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