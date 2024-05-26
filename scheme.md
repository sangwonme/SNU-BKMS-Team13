
### Complete Database Schema

#### User Table
This table will store information about the users of the application.

| Column Name      | Data Type    | Constraints             |
|------------------|--------------|-------------------------|
| user_id          | INT          | PRIMARY KEY, AUTO_INCREMENT |
| username         | VARCHAR(50)  | NOT NULL, UNIQUE        |
| email            | VARCHAR(100) | NOT NULL, UNIQUE        |
| password         | VARCHAR(255) | NOT NULL                |
| date_joined      | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP |
| sex              | ENUM('Male', 'Female', 'Other') | NOT NULL |
| date_of_birth    | DATE         | NULL                    |
| account          | INT          | NOT NULL                |

#### Product Table
This table will store information about the products.

| Column Name      | Data Type    | Constraints             |
|------------------|--------------|-------------------------|
| product_id       | INT          | PRIMARY KEY, AUTO_INCREMENT |
| goods_name       | VARCHAR(255) | NOT NULL                |
| goods_link       | VARCHAR(255) | NOT NULL                |
| image_link       | VARCHAR(255) | NOT NULL                |
| sex              | ENUM('Male', 'Female', 'Unisex') | NOT NULL |
| category         | VARCHAR(100) | NOT NULL                |
| price            | DECIMAL(10, 2) | NOT NULL              |
| seller_id        | INT          | FOREIGN KEY (references seller(seller_id)) |
| stock_quantity   | INT          | NOT NULL                |
| date_added       | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP |

#### Seller Table
This table will store information about the sellers.

| Column Name      | Data Type    | Constraints             |
|------------------|--------------|-------------------------|
| seller_id        | INT          | PRIMARY KEY, AUTO_INCREMENT |
| seller_name      | VARCHAR(100) | NOT NULL                |
| contact_email    | VARCHAR(100) | NOT NULL, UNIQUE        |
| contact_phone    | VARCHAR(20)  | NOT NULL                |
| address          | VARCHAR(255) | NULL                    |
| date_joined      | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP |

#### SearchLog Table
This table will store the search logs of users.

| Column Name      | Data Type    | Constraints             |
|------------------|--------------|-------------------------|
| searchlog_id     | INT          | PRIMARY KEY, AUTO_INCREMENT |
| user_id          | INT          | FOREIGN KEY (references user(user_id)) |
| search_query     | VARCHAR(255) | NOT NULL                |
| search_date      | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP |

#### SearchResult Table
This table will store the top-10 search results for each search query.

| Column Name      | Data Type    | Constraints             |
|------------------|--------------|-------------------------|
| result_id        | INT          | PRIMARY KEY, AUTO_INCREMENT |
| searchlog_id     | INT          | FOREIGN KEY (references searchlog(searchlog_id)) |
| product_id       | INT          | FOREIGN KEY (references product(product_id)) |
| rank             | INT          | NOT NULL                |

#### BuyLog Table
This table will store the purchase logs of users.

| Column Name      | Data Type    | Constraints             |
|------------------|--------------|-------------------------|
| buylog_id        | INT          | PRIMARY KEY, AUTO_INCREMENT |
| user_id          | INT          | FOREIGN KEY (references user(user_id)) |
| product_id       | INT          | FOREIGN KEY (references product(product_id)) |
| quantity         | INT          | NOT NULL                |
| total_price      | DECIMAL(10, 2) | NOT NULL              |
| purchase_date    | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP |

This schema now includes the ability to log the top-10 search results for each search query, linking them to the respective search log entries. If you have any further requirements or modifications, please let me know!