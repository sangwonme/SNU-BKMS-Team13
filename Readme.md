# DB Initialization

```postgresql
/* users */
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sex ENUM('Male', 'Female', 'Other') NOT NULL,
    date_of_birth DATE NULL,
    account INT NOT NULL,
);

/* TODO: sangwon */
```

# Prequisites

1. `python-dotenv`, `psycopg2-binary` 라이브러리 설치
```
pip install python-dotenv psycopg2-binary
```
2. 루트폴더 (../SNU-BKMS-TEAM13) 에 `.env` 이름의 텍스트파일 생성 후, postgre DB 정보 입력
- 아래 예시 복붙하신 후, 일반적으로 USERNAME, DBNAME만 바꾸면 됩니다
```
PG_DBNAME=postgres
PG_USERNAME=kdk
PG_PASSWORD=1234
PG_PORT=5432
PG_HOST=localhost
```

3. 실행:
`python3 main.py`

# Notes
1. main에서 FE.run()을 통해 현재 상태에 맞는 라우트 함수(`@public`, `@protected`로 감싸져 있는 것)가 무한히 실행됩니다.
- route 데코레이터를 통해 **public/protected 라우팅**와 **유저 정보 업데이트**, **예외처리 코드 재사용** 등을 구현했습니다. 따라서 빡세게 예외처리 안 해도 되고, 로그인되어 있는지 매번 확인하는 코드를 작성하지 않아도 괜찮습니다.
- `self.push(routename)`을 통해 상태를 전이할 수 있습니다. 웹과 비슷하게 라우트 개념으로 이해하시면 될 것 같습니다.
2. BE(backend), FE(frontend)로 나눠서 구현했습니다. `cursor.~, conn.~`와 같이 DB 접근은 backend에서, 사용자 경험은 frontend에서 구현하면 좋을 것 같습니다.