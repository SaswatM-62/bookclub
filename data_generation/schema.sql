-- book club management system schema
-- run: psql -U postgres -d bookclub -f schema.sql

-- drop tables in reverse dependency order
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS reading_list CASCADE;
DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS member_club CASCADE;
DROP TABLE IF EXISTS book_genre CASCADE;
DROP TABLE IF EXISTS book_author CASCADE;
DROP TABLE IF EXISTS meetings CASCADE;
DROP TABLE IF EXISTS members CASCADE;
DROP TABLE IF EXISTS clubs CASCADE;
DROP TABLE IF EXISTS books CASCADE;
DROP TABLE IF EXISTS authors CASCADE;
DROP TABLE IF EXISTS genres CASCADE;

-- genres
CREATE TABLE genres (
    genre        VARCHAR(50)  PRIMARY KEY,
    description  TEXT         NOT NULL,
    fiction_type VARCHAR(20)  NOT NULL
        CHECK (fiction_type IN ('Fiction', 'Non-Fiction'))
);

-- authors
CREATE TABLE authors (
    author_id   SERIAL        PRIMARY KEY,
    name        VARCHAR(200)  NOT NULL,
    nationality VARCHAR(100),
    birth_date  VARCHAR(20),
    biography   TEXT
);

-- books
CREATE TABLE books (
    book_id        SERIAL        PRIMARY KEY,
    isbn           VARCHAR(30)   NOT NULL UNIQUE,
    title          VARCHAR(500)  NOT NULL,
    description    TEXT,
    year_published INT
        CHECK (year_published >= 1000 AND year_published <= 2026),
    language       VARCHAR(50)   DEFAULT 'English'
);

-- members
CREATE TABLE members (
    member_id   SERIAL        PRIMARY KEY,
    name        VARCHAR(100)  NOT NULL,
    email       VARCHAR(100)  NOT NULL UNIQUE,
    phone       VARCHAR(20),
    joined_date DATE
);

-- clubs
CREATE TABLE clubs (
    club_id            SERIAL        PRIMARY KEY,
    name               VARCHAR(100)  NOT NULL,
    description        TEXT,
    founded_date       DATE,
    meeting_frequency  VARCHAR(20)
        CHECK (meeting_frequency IN ('Weekly', 'Biweekly', 'Monthly', 'Quarterly'))
);

-- meetings
CREATE TABLE meetings (
    meeting_id       SERIAL        PRIMARY KEY,
    club_id          INT           NOT NULL
        REFERENCES clubs(club_id)   ON DELETE CASCADE,
    book_id          INT
        REFERENCES books(book_id)   ON DELETE SET NULL,
    meeting_date     DATE          NOT NULL,
    location         VARCHAR(200),
    duration_minutes INT
        CHECK (duration_minutes > 0),
    notes            TEXT,
    status           VARCHAR(20)   NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'completed'))
);

-- reviews
CREATE TABLE reviews (
    review_id   SERIAL  PRIMARY KEY,
    member_id   INT     NOT NULL
        REFERENCES members(member_id) ON DELETE CASCADE,
    book_id     INT     NOT NULL
        REFERENCES books(book_id)     ON DELETE CASCADE,
    rating      INT     NOT NULL
        CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    review_date DATE,
    UNIQUE (member_id, book_id)
);

-- book_author: many-to-many between books and authors
CREATE TABLE book_author (
    book_id      INT  NOT NULL
        REFERENCES books(book_id)     ON DELETE CASCADE,
    author_id    INT  NOT NULL
        REFERENCES authors(author_id) ON DELETE CASCADE,
    author_order INT  NOT NULL DEFAULT 1
        CHECK (author_order >= 1),
    PRIMARY KEY (book_id, author_id)
);

-- book_genre: many-to-many between books and genres
CREATE TABLE book_genre (
    book_id  INT         NOT NULL
        REFERENCES books(book_id)   ON DELETE CASCADE,
    genre    VARCHAR(50) NOT NULL
        REFERENCES genres(genre)    ON DELETE CASCADE,
    PRIMARY KEY (book_id, genre)
);

-- member_club: many-to-many between members and clubs
CREATE TABLE member_club (
    member_id   INT         NOT NULL
        REFERENCES members(member_id) ON DELETE CASCADE,
    club_id     INT         NOT NULL
        REFERENCES clubs(club_id)     ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL DEFAULT 'Regular'
        CHECK (role IN ('President', 'Moderator', 'Regular')),
    joined_date DATE,
    PRIMARY KEY (member_id, club_id)
);

-- attendance: many-to-many between members and meetings
CREATE TABLE attendance (
    member_id  INT         NOT NULL
        REFERENCES members(member_id) ON DELETE CASCADE,
    meeting_id INT         NOT NULL
        REFERENCES meetings(meeting_id) ON DELETE CASCADE,
    status     VARCHAR(20) NOT NULL DEFAULT 'attended'
        CHECK (status IN ('attended', 'absent', 'excused')),
    PRIMARY KEY (member_id, meeting_id)
);

-- reading_list: many-to-many between clubs and books
CREATE TABLE reading_list (
    club_id        INT         NOT NULL
        REFERENCES clubs(club_id) ON DELETE CASCADE,
    book_id        INT         NOT NULL
        REFERENCES books(book_id) ON DELETE CASCADE,
    scheduled_date DATE,
    status         VARCHAR(20) NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'reading', 'completed')),
    PRIMARY KEY (club_id, book_id)
);

-- verify tables were created
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
