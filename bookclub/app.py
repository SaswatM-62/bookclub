import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "bookclub_secret_key")


# db helpers

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT"),
        )
    conn.autocommit = False
    return conn


def query_db(sql, params=None, fetchone=False):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetchone:
                return cur.fetchone()
            return cur.fetchall()
    finally:
        conn.close()


# home

@app.route("/")
def index():
    try:
        stats = query_db("""
            SELECT
                (SELECT COUNT(*) FROM books)   AS total_books,
                (SELECT COUNT(*) FROM members) AS total_members,
                (SELECT COUNT(*) FROM clubs)   AS total_clubs,
                (SELECT COUNT(*) FROM reviews) AS total_reviews
        """, fetchone=True)
    except Exception as e:
        flash(f"Error loading stats: {e}", "danger")
        stats = {}
    return render_template("index.html", stats=stats)


# quit

@app.route("/quit")
def quit_app():
    return render_template("quit.html")


# search and browse books

@app.route("/books")
def books_list():
    search = request.args.get("search", "").strip()
    genre  = request.args.get("genre", "").strip()
    params = []
    where  = []
    if search:
        where.append("b.title ILIKE %s")
        params.append(f"%{search}%")
    if genre:
        where.append("bg.genre = %s")
        params.append(genre)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT b.book_id, b.title, b.year_published, b.language,
               a.name AS author,
               STRING_AGG(DISTINCT bg.genre, ', ') AS genres,
               ROUND(AVG(r.rating)::numeric, 2) AS avg_rating,
               COUNT(DISTINCT r.review_id) AS review_count
        FROM books b
        LEFT JOIN book_author ba ON b.book_id = ba.book_id AND ba.author_order = 1
        LEFT JOIN authors a ON ba.author_id = a.author_id
        LEFT JOIN book_genre bg ON b.book_id = bg.book_id
        LEFT JOIN reviews r ON b.book_id = r.book_id
        {where_clause}
        GROUP BY b.book_id, b.title, b.year_published, b.language, a.name
        ORDER BY b.title
    """
    try:
        books  = query_db(sql, params)
        genres = query_db("SELECT genre FROM genres ORDER BY genre")
    except Exception as e:
        flash(f"Error loading books: {e}", "danger")
        books, genres = [], []
    return render_template("books/list.html", books=books, genres=genres,
                           search=search, selected_genre=genre)


@app.route("/books/<int:book_id>")
def book_detail(book_id):
    try:
        book = query_db("""
            SELECT b.*, ROUND(AVG(r.rating)::numeric, 2) AS avg_rating,
                   COUNT(r.review_id) AS review_count
            FROM books b
            LEFT JOIN reviews r ON b.book_id = r.book_id
            WHERE b.book_id = %s
            GROUP BY b.book_id
        """, (book_id,), fetchone=True)
        if not book:
            flash("Book not found.", "warning")
            return redirect(url_for("books_list"))
        authors = query_db("""
            SELECT a.author_id, a.name, ba.author_order
            FROM book_author ba
            JOIN authors a ON ba.author_id = a.author_id
            WHERE ba.book_id = %s ORDER BY ba.author_order
        """, (book_id,))
        book_genres = query_db(
            "SELECT bg.genre FROM book_genre bg WHERE bg.book_id = %s ORDER BY bg.genre",
            (book_id,))
        reviews = query_db("""
            SELECT r.review_id, r.rating, r.review_text, r.review_date,
                   m.member_id, m.name AS member_name
            FROM reviews r
            JOIN members m ON r.member_id = m.member_id
            WHERE r.book_id = %s ORDER BY r.review_date DESC
        """, (book_id,))
        all_members = query_db("SELECT member_id, name FROM members ORDER BY name")
    except Exception as e:
        flash(f"Error loading book: {e}", "danger")
        return redirect(url_for("books_list"))
    return render_template("books/detail.html", book=book, authors=authors,
                           book_genres=book_genres, reviews=reviews,
                           all_members=all_members)


# member profiles and activity

@app.route("/members")
def members_list():
    search = request.args.get("search", "").strip()
    params = []
    where  = ""
    if search:
        where = "WHERE m.name ILIKE %s"
        params.append(f"%{search}%")
    sql = f"""
        SELECT m.member_id, m.name, m.email, m.joined_date,
               COUNT(DISTINCT mc.club_id)  AS club_count,
               COUNT(DISTINCT r.review_id) AS review_count
        FROM members m
        LEFT JOIN member_club mc ON m.member_id = mc.member_id
        LEFT JOIN reviews r      ON m.member_id = r.member_id
        {where}
        GROUP BY m.member_id, m.name, m.email, m.joined_date
        ORDER BY m.name
    """
    try:
        members = query_db(sql, params)
    except Exception as e:
        flash(f"Error loading members: {e}", "danger")
        members = []
    return render_template("members/list.html", members=members, search=search)


@app.route("/members/<int:member_id>")
def member_detail(member_id):
    try:
        member = query_db("SELECT * FROM members WHERE member_id = %s",
                          (member_id,), fetchone=True)
        if not member:
            flash("Member not found.", "warning")
            return redirect(url_for("members_list"))
        clubs = query_db("""
            SELECT c.club_id, c.name, mc.role, mc.joined_date
            FROM member_club mc
            JOIN clubs c ON mc.club_id = c.club_id
            WHERE mc.member_id = %s ORDER BY c.name
        """, (member_id,))
        reviews = query_db("""
            SELECT r.review_id, r.rating, r.review_text, r.review_date,
                   b.book_id, b.title AS book_title
            FROM reviews r
            JOIN books b ON r.book_id = b.book_id
            WHERE r.member_id = %s ORDER BY r.review_date DESC
        """, (member_id,))
        # Meetings attended (subquery join)
        meetings_attended = query_db("""
            SELECT m.meeting_date, m.location, c.name AS club_name,
                   b.title AS book_title, a.status
            FROM attendance a
            JOIN meetings m  ON a.meeting_id = m.meeting_id
            JOIN clubs c     ON m.club_id = c.club_id
            LEFT JOIN books b ON m.book_id = b.book_id
            WHERE a.member_id = %s
            ORDER BY m.meeting_date DESC
            LIMIT 10
        """, (member_id,))
    except Exception as e:
        flash(f"Error loading member: {e}", "danger")
        return redirect(url_for("members_list"))
    return render_template("members/detail.html", member=member, clubs=clubs,
                           reviews=reviews, meetings_attended=meetings_attended)


# clubs and meetings

@app.route("/clubs")
def clubs_list():
    search = request.args.get("search", "").strip()
    params = []
    where  = ""
    if search:
        where = "WHERE c.name ILIKE %s"
        params.append(f"%{search}%")
    sql = f"""
        SELECT c.club_id, c.name, c.founded_date, c.meeting_frequency,
               COUNT(DISTINCT mc.member_id) AS member_count,
               COUNT(DISTINCT m.meeting_id) AS meeting_count
        FROM clubs c
        LEFT JOIN member_club mc ON c.club_id = mc.club_id
        LEFT JOIN meetings m     ON c.club_id = m.club_id
        {where}
        GROUP BY c.club_id, c.name, c.founded_date, c.meeting_frequency
        ORDER BY c.name
    """
    try:
        clubs = query_db(sql, params)
    except Exception as e:
        flash(f"Error loading clubs: {e}", "danger")
        clubs = []
    return render_template("clubs/list.html", clubs=clubs, search=search)


@app.route("/clubs/<int:club_id>")
def club_detail(club_id):
    try:
        club = query_db("SELECT * FROM clubs WHERE club_id = %s",
                        (club_id,), fetchone=True)
        if not club:
            flash("Club not found.", "warning")
            return redirect(url_for("clubs_list"))
        members = query_db("""
            SELECT m.member_id, m.name, mc.role, mc.joined_date
            FROM member_club mc
            JOIN members m ON mc.member_id = m.member_id
            WHERE mc.club_id = %s ORDER BY mc.role, m.name
        """, (club_id,))
        meetings = query_db("""
            SELECT m.meeting_id, m.meeting_date, m.location, m.status,
                   b.book_id, b.title AS book_title
            FROM meetings m
            LEFT JOIN books b ON m.book_id = b.book_id
            WHERE m.club_id = %s ORDER BY m.meeting_date DESC
        """, (club_id,))
        reading_list = query_db("""
            SELECT rl.scheduled_date, rl.status, b.book_id, b.title
            FROM reading_list rl
            JOIN books b ON rl.book_id = b.book_id
            WHERE rl.club_id = %s ORDER BY rl.scheduled_date
        """, (club_id,))
        completed_count = query_db("""
            SELECT COUNT(*) AS cnt FROM meetings
            WHERE club_id = %s AND status = 'completed'
        """, (club_id,), fetchone=True)
    except Exception as e:
        flash(f"Error loading club: {e}", "danger")
        return redirect(url_for("clubs_list"))
    return render_template("clubs/detail.html", club=club, members=members,
                           meetings=meetings, reading_list=reading_list,
                           completed_count=completed_count["cnt"])


@app.route("/meetings")
def meetings_list():
    club_id = request.args.get("club_id", "").strip()
    status  = request.args.get("status", "").strip()
    params  = []
    where   = []
    if club_id:
        where.append("m.club_id = %s")
        params.append(club_id)
    if status:
        where.append("m.status = %s")
        params.append(status)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT m.meeting_id, m.meeting_date, m.location, m.status,
               m.duration_minutes, c.club_id, c.name AS club_name,
               b.book_id, b.title AS book_title
        FROM meetings m
        JOIN clubs c ON m.club_id = c.club_id
        LEFT JOIN books b ON m.book_id = b.book_id
        {where_clause}
        ORDER BY CASE WHEN m.status = 'planned' THEN 0 ELSE 1 END,
                 m.meeting_date ASC
    """
    try:
        meetings = query_db(sql, params)
        clubs    = query_db("SELECT club_id, name FROM clubs ORDER BY name")
    except Exception as e:
        flash(f"Error loading meetings: {e}", "danger")
        meetings, clubs = [], []
    return render_template("meetings/list.html", meetings=meetings, clubs=clubs,
                           selected_club=club_id, selected_status=status)


# analytics and reports

@app.route("/analytics")
def analytics():
    try:
        # Q1: Top 10 highest-rated books (min 3 reviews)
        top_rated_books = query_db("""
            SELECT b.title, a.name AS author,
                   ROUND(AVG(r.rating)::numeric, 2) AS avg_rating,
                   COUNT(r.review_id) AS review_count
            FROM reviews r
            JOIN books b ON r.book_id = b.book_id
            LEFT JOIN book_author ba ON b.book_id = ba.book_id AND ba.author_order = 1
            LEFT JOIN authors a ON ba.author_id = a.author_id
            GROUP BY b.book_id, b.title, a.name
            HAVING COUNT(r.review_id) >= 3
            ORDER BY avg_rating DESC, review_count DESC
            LIMIT 10
        """)

        # Q2: Top 10 most active reviewers
        most_active_members = query_db("""
            SELECT m.name, m.email,
                   COUNT(r.review_id)              AS review_count,
                   ROUND(AVG(r.rating)::numeric, 2) AS avg_rating_given
            FROM members m
            JOIN reviews r ON m.member_id = r.member_id
            GROUP BY m.member_id, m.name, m.email
            ORDER BY review_count DESC
            LIMIT 10
        """)

        # Q3: Top 10 most discussed books (discussed in most distinct clubs)
        books_multi_club = query_db("""
            SELECT b.title,
                   COUNT(DISTINCT mt.club_id)       AS club_count,
                   COUNT(mt.meeting_id)              AS total_meetings,
                   STRING_AGG(DISTINCT c.name, ', ') AS clubs
            FROM books b
            JOIN meetings mt ON b.book_id = mt.book_id
            JOIN clubs c    ON mt.club_id = c.club_id
            GROUP BY b.book_id, b.title
            HAVING COUNT(DISTINCT mt.club_id) > 1
            ORDER BY club_count DESC, total_meetings DESC
            LIMIT 10
        """)

        # Q4: Top 10 authors by average review rating (min 3 reviews across all books)
        author_leaderboard = query_db("""
            SELECT a.name, a.nationality,
                   ROUND(AVG(r.rating)::numeric, 2) AS avg_rating,
                   COUNT(r.review_id)               AS total_reviews,
                   COUNT(DISTINCT ba.book_id)        AS books_reviewed
            FROM authors a
            JOIN book_author ba ON a.author_id = ba.author_id
            JOIN reviews r     ON ba.book_id   = r.book_id
            GROUP BY a.author_id, a.name, a.nationality
            HAVING COUNT(r.review_id) >= 3
            ORDER BY avg_rating DESC, total_reviews DESC
            LIMIT 10
        """)

        # Q5: 10 most recently completed meetings
        recent_completed = query_db("""
            SELECT b.title, c.name AS club_name,
                   mt.meeting_date, mt.location
            FROM meetings mt
            JOIN books b ON mt.book_id = b.book_id
            JOIN clubs c ON mt.club_id = c.club_id
            WHERE mt.status = 'completed'
            ORDER BY mt.meeting_date DESC
            LIMIT 10
        """)

        # Q6: Top 10 members by attendance rate
        #     Denominator = meetings recorded in attendance for clubs they belong to
        #     after their club join date (avoids counting meetings before they joined)
        attendance_rate = query_db("""
            SELECT m.name,
                   COUNT(CASE WHEN a.status = 'attended' THEN 1 END) AS meetings_attended,
                   COUNT(a.meeting_id)                                AS recorded_meetings,
                   ROUND(
                       COUNT(CASE WHEN a.status = 'attended' THEN 1 END)
                       * 100.0 / NULLIF(COUNT(a.meeting_id), 0)
                   , 1) AS attendance_pct
            FROM members m
            JOIN attendance a  ON a.member_id  = m.member_id
            JOIN meetings mt   ON a.meeting_id = mt.meeting_id
                              AND mt.status = 'completed'
            JOIN member_club mc ON mc.member_id = m.member_id
                               AND mc.club_id   = mt.club_id
                               AND (mc.joined_date IS NULL
                                    OR mt.meeting_date >= mc.joined_date)
            GROUP BY m.member_id, m.name
            HAVING COUNT(a.meeting_id) > 0
            ORDER BY attendance_pct DESC, meetings_attended DESC
            LIMIT 10
        """)

        # Q7: Top 10 genres by number of books assigned
        popular_genres = query_db("""
            SELECT g.genre, g.fiction_type,
                   COUNT(bg.book_id)                AS book_count,
                   ROUND(AVG(r.rating)::numeric, 2) AS avg_rating
            FROM genres g
            LEFT JOIN book_genre bg ON g.genre    = bg.genre
            LEFT JOIN reviews r     ON bg.book_id = r.book_id
            GROUP BY g.genre, g.fiction_type
            ORDER BY book_count DESC
            LIMIT 10
        """)

        # Q8: Top 10 books rated above the overall site average
        above_avg_books = query_db("""
            SELECT b.title, a.name AS author,
                   ROUND(AVG(r.rating)::numeric, 2) AS avg_rating,
                   COUNT(r.review_id)               AS review_count,
                   ROUND(
                       AVG(r.rating) - (SELECT AVG(rating) FROM reviews)
                   , 2)                              AS above_avg_by
            FROM books b
            LEFT JOIN book_author ba ON b.book_id = ba.book_id AND ba.author_order = 1
            LEFT JOIN authors a     ON ba.author_id = a.author_id
            JOIN reviews r          ON b.book_id = r.book_id
            GROUP BY b.book_id, b.title, a.name
            HAVING AVG(r.rating) > (SELECT AVG(rating) FROM reviews)
            ORDER BY avg_rating DESC
            LIMIT 10
        """)

        # Q10: 10 most dedicated attendees who have never written a review
        #      Uses EXCEPT: members who attended meetings minus members who reviewed
        members_no_review_in_club = query_db("""
            SELECT m.name, m.email, m.joined_date
            FROM members m
            WHERE m.member_id IN (
                SELECT member_id FROM attendance WHERE status = 'attended'
            )
            EXCEPT
            SELECT m.name, m.email, m.joined_date
            FROM members m
            WHERE m.member_id IN (SELECT member_id FROM reviews)
            ORDER BY joined_date ASC
            LIMIT 10
        """)

        # Q11: Top 10 clubs by reading list completion rate
        club_reading_progress = query_db("""
            SELECT c.name AS club_name,
                   COUNT(DISTINCT rl.book_id) AS total_on_list,
                   SUM(CASE WHEN rl.status = 'completed' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN rl.status = 'reading'   THEN 1 ELSE 0 END) AS reading,
                   SUM(CASE WHEN rl.status = 'planned'   THEN 1 ELSE 0 END) AS planned,
                   ROUND(
                       SUM(CASE WHEN rl.status = 'completed' THEN 1 ELSE 0 END) * 100.0
                       / NULLIF(COUNT(DISTINCT rl.book_id), 0)
                   , 1) AS completion_pct
            FROM clubs c
            LEFT JOIN reading_list rl ON c.club_id = rl.club_id
            GROUP BY c.club_id, c.name
            HAVING COUNT(DISTINCT rl.book_id) > 0
            ORDER BY completion_pct DESC NULLS LAST
            LIMIT 10
        """)

        # Q12: 10 most recent book activities (completed meetings UNION reading list)
        book_activity_union = query_db("""
            SELECT b.title,
                   'Meeting' AS source,
                   mt.meeting_date AS activity_date,
                   c.name          AS club_name
            FROM books b
            JOIN meetings mt ON b.book_id = mt.book_id
            JOIN clubs c     ON mt.club_id = c.club_id
            WHERE mt.status = 'completed'
            UNION
            SELECT b.title,
                   'Reading List (' || rl.status || ')' AS source,
                   rl.scheduled_date                    AS activity_date,
                   c.name                               AS club_name
            FROM books b
            JOIN reading_list rl ON b.book_id  = rl.book_id
            JOIN clubs c         ON rl.club_id = c.club_id
            ORDER BY activity_date DESC NULLS LAST
            LIMIT 10
        """)

    except Exception as e:
        flash(f"Error loading analytics: {e}", "danger")
        (top_rated_books, most_active_members, books_multi_club,
         author_leaderboard, recent_completed, attendance_rate,
         popular_genres, above_avg_books,
         members_no_review_in_club, club_reading_progress,
         book_activity_union) = ([], [], [], [], [], [], [], [], [], [], [])

    return render_template("analytics/index.html",
                           top_rated_books=top_rated_books,
                           most_active_members=most_active_members,
                           books_multi_club=books_multi_club,
                           author_leaderboard=author_leaderboard,
                           recent_completed=recent_completed,
                           attendance_rate=attendance_rate,
                           popular_genres=popular_genres,
                           above_avg_books=above_avg_books,
                           members_no_review_in_club=members_no_review_in_club,
                           club_reading_progress=club_reading_progress,
                           book_activity_union=book_activity_union)


# advanced explore

@app.route("/explore")
def explore():
    try:
        genres        = query_db("SELECT genre FROM genres ORDER BY genre")
        languages     = query_db("SELECT DISTINCT language FROM books WHERE language IS NOT NULL ORDER BY language")
        nationalities = query_db("SELECT DISTINCT nationality FROM authors WHERE nationality IS NOT NULL ORDER BY nationality")
    except Exception as e:
        flash(f"Error loading filter options: {e}", "danger")
        genres, languages, nationalities = [], [], []

    f_genre       = request.args.get("genre", "").strip()
    f_fiction     = request.args.get("fiction_type", "").strip()
    f_language    = request.args.get("language", "").strip()
    f_year_from   = request.args.get("year_from", "").strip()
    f_year_to     = request.args.get("year_to", "").strip()
    f_min_rating  = request.args.get("min_rating", "").strip()
    f_nationality = request.args.get("nationality", "").strip()
    f_sort        = request.args.get("sort", "title_asc").strip()

    sort_map = {
        "title_asc":   "b.title ASC",
        "title_desc":  "b.title DESC",
        "year_newest": "b.year_published DESC NULLS LAST",
        "year_oldest": "b.year_published ASC NULLS LAST",
        "rating_high": "avg_rating DESC NULLS LAST",
        "rating_low":  "avg_rating ASC NULLS LAST",
    }
    order_by = sort_map.get(f_sort, "b.title ASC")

    where_clauses  = []
    having_clauses = []
    params         = []

    if f_genre:
        where_clauses.append("bg.genre = %s")
        params.append(f_genre)
    if f_fiction:
        where_clauses.append("g.fiction_type = %s")
        params.append(f_fiction)
    if f_language:
        where_clauses.append("b.language = %s")
        params.append(f_language)
    if f_year_from:
        where_clauses.append("b.year_published >= %s")
        params.append(int(f_year_from))
    if f_year_to:
        where_clauses.append("b.year_published <= %s")
        params.append(int(f_year_to))
    if f_nationality:
        where_clauses.append("a.nationality = %s")
        params.append(f_nationality)
    if f_min_rating:
        having_clauses.append("AVG(r.rating) >= %s")
        params.append(float(f_min_rating))

    where_sql  = ("WHERE "  + " AND ".join(where_clauses))  if where_clauses  else ""
    having_sql = ("HAVING " + " AND ".join(having_clauses)) if having_clauses else ""

    sql = f"""
        SELECT b.book_id, b.title, b.year_published, b.language,
               a.name AS author,
               STRING_AGG(DISTINCT bg.genre, ', ') AS genres,
               ROUND(AVG(r.rating)::numeric, 2) AS avg_rating,
               COUNT(DISTINCT r.review_id) AS review_count
        FROM books b
        LEFT JOIN book_author ba ON b.book_id = ba.book_id AND ba.author_order = 1
        LEFT JOIN authors a ON ba.author_id = a.author_id
        LEFT JOIN book_genre bg ON b.book_id = bg.book_id
        LEFT JOIN genres g ON bg.genre = g.genre
        LEFT JOIN reviews r ON b.book_id = r.book_id
        {where_sql}
        GROUP BY b.book_id, b.title, b.year_published, b.language, a.name
        {having_sql}
        ORDER BY {order_by}
        LIMIT 100
    """
    try:
        results = query_db(sql, params)
    except Exception as e:
        flash(f"Error running explore query: {e}", "danger")
        results = []

    filters = dict(genre=f_genre, fiction_type=f_fiction, language=f_language,
                   year_from=f_year_from, year_to=f_year_to, min_rating=f_min_rating,
                   nationality=f_nationality, sort=f_sort)
    return render_template("explore/index.html",
                           results=results, genres=genres, languages=languages,
                           nationalities=nationalities,
                           fiction_types=["Fiction", "Non-Fiction"],
                           filters=filters)


# manage data

@app.route("/manage")
def manage():
    try:
        counts = query_db("""
            SELECT
                (SELECT COUNT(*) FROM books)    AS books,
                (SELECT COUNT(*) FROM members)  AS members,
                (SELECT COUNT(*) FROM clubs)    AS clubs,
                (SELECT COUNT(*) FROM meetings) AS meetings,
                (SELECT COUNT(*) FROM authors)  AS authors,
                (SELECT COUNT(*) FROM genres)   AS genres
        """, fetchone=True)
    except Exception as e:
        flash(f"Error: {e}", "danger")
        counts = {}
    return render_template("manage.html", counts=counts)


# books crud

@app.route("/books/add", methods=["GET", "POST"])
def book_add():
    try:
        genres  = query_db("SELECT genre FROM genres ORDER BY genre")
        authors = query_db("SELECT author_id, name FROM authors ORDER BY name")
    except Exception as e:
        flash(f"Error loading form data: {e}", "danger")
        return redirect(url_for("manage"))

    if request.method == "POST":
        title            = request.form.get("title", "").strip()
        isbn             = request.form.get("isbn", "").strip()
        description      = request.form.get("description", "").strip()
        year             = request.form.get("year_published") or None
        language         = request.form.get("language", "English").strip()
        selected_genres  = request.form.getlist("genres")
        selected_authors = request.form.getlist("author_ids")
        new_author_name  = request.form.get("new_author_name", "").strip()
        new_author_nat   = request.form.get("new_author_nationality", "").strip()

        if not title or not isbn:
            flash("Title and ISBN are required.", "warning")
            return render_template("books/add.html", genres=genres, authors=authors)

        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Optionally create a new author first
                if new_author_name:
                    cur.execute("""
                        INSERT INTO authors (name, nationality)
                        VALUES (%s, %s) RETURNING author_id
                    """, (new_author_name, new_author_nat or None))
                    new_aid = str(cur.fetchone()["author_id"])
                    selected_authors = [new_aid] + selected_authors

                cur.execute("""
                    INSERT INTO books (isbn, title, description, year_published, language)
                    VALUES (%s, %s, %s, %s, %s) RETURNING book_id
                """, (isbn, title, description or None, year, language))
                book_id = cur.fetchone()["book_id"]

                seen_genres = set()
                for genre in selected_genres:
                    if genre and genre not in seen_genres:
                        seen_genres.add(genre)
                        cur.execute(
                            "INSERT INTO book_genre (book_id, genre) VALUES (%s, %s)",
                            (book_id, genre))

                seen_authors = set()
                for order, aid in enumerate(selected_authors, start=1):
                    if aid and aid not in seen_authors:
                        seen_authors.add(aid)
                        cur.execute("""
                            INSERT INTO book_author (book_id, author_id, author_order)
                            VALUES (%s, %s, %s)
                        """, (book_id, aid, order))

            conn.commit()
            flash("Book added successfully.", "success")
            return redirect(url_for("book_detail", book_id=book_id))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash("A book with that ISBN already exists.", "danger")
        except Exception as e:
            conn.rollback()
            flash(f"Error adding book: {e}", "danger")
        finally:
            conn.close()

    return render_template("books/add.html", genres=genres, authors=authors)


@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
def book_edit(book_id):
    try:
        book           = query_db("SELECT * FROM books WHERE book_id = %s", (book_id,), fetchone=True)
        if not book:
            flash("Book not found.", "warning")
            return redirect(url_for("books_list"))
        genres         = query_db("SELECT genre FROM genres ORDER BY genre")
        authors        = query_db("SELECT author_id, name FROM authors ORDER BY name")
        current_genres = query_db(
            "SELECT genre FROM book_genre WHERE book_id = %s ORDER BY genre", (book_id,))
        current_authors = query_db(
            "SELECT author_id FROM book_author WHERE book_id = %s ORDER BY author_order", (book_id,))
    except Exception as e:
        flash(f"Error loading book: {e}", "danger")
        return redirect(url_for("books_list"))

    if request.method == "POST":
        title            = request.form.get("title", "").strip()
        isbn             = request.form.get("isbn", "").strip()
        description      = request.form.get("description", "").strip()
        year             = request.form.get("year_published") or None
        language         = request.form.get("language", "English").strip()
        selected_genres  = request.form.getlist("genres")
        selected_authors = request.form.getlist("author_ids")
        new_author_name  = request.form.get("new_author_name", "").strip()
        new_author_nat   = request.form.get("new_author_nationality", "").strip()

        if not title or not isbn:
            flash("Title and ISBN are required.", "warning")
            return render_template("books/edit.html", book=book, genres=genres,
                                   authors=authors, current_genres=current_genres,
                                   current_authors=current_authors)
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if new_author_name:
                    cur.execute("""
                        INSERT INTO authors (name, nationality)
                        VALUES (%s, %s) RETURNING author_id
                    """, (new_author_name, new_author_nat or None))
                    new_aid = str(cur.fetchone()["author_id"])
                    selected_authors = [new_aid] + selected_authors

                cur.execute("""
                    UPDATE books SET isbn=%s, title=%s, description=%s,
                    year_published=%s, language=%s WHERE book_id=%s
                """, (isbn, title, description or None, year, language, book_id))

                cur.execute("DELETE FROM book_genre WHERE book_id = %s", (book_id,))
                seen_genres = set()
                for genre in selected_genres:
                    if genre and genre not in seen_genres:
                        seen_genres.add(genre)
                        cur.execute(
                            "INSERT INTO book_genre (book_id, genre) VALUES (%s, %s)",
                            (book_id, genre))

                cur.execute("DELETE FROM book_author WHERE book_id = %s", (book_id,))
                seen_authors = set()
                for order, aid in enumerate(selected_authors, start=1):
                    if aid and aid not in seen_authors:
                        seen_authors.add(aid)
                        cur.execute("""
                            INSERT INTO book_author (book_id, author_id, author_order)
                            VALUES (%s, %s, %s)
                        """, (book_id, aid, order))

            conn.commit()
            flash("Book updated successfully.", "success")
            return redirect(url_for("book_detail", book_id=book_id))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash("A book with that ISBN already exists.", "danger")
        except Exception as e:
            conn.rollback()
            flash(f"Error updating book: {e}", "danger")
        finally:
            conn.close()

    return render_template("books/edit.html", book=book, genres=genres,
                           authors=authors, current_genres=current_genres,
                           current_authors=current_authors)


@app.route("/books/<int:book_id>/delete", methods=["POST"])
def book_delete(book_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
        conn.commit()
        flash("Book deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting book: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("books_list"))


# members crud

@app.route("/members/add", methods=["GET", "POST"])
def member_add():
    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        email       = request.form.get("email", "").strip()
        phone       = request.form.get("phone", "").strip()
        joined_date = request.form.get("joined_date") or None

        if not name or not email:
            flash("Name and email are required.", "warning")
            return render_template("members/add.html")

        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO members (name, email, phone, joined_date)
                    VALUES (%s, %s, %s, %s) RETURNING member_id
                """, (name, email, phone or None, joined_date))
                member_id = cur.fetchone()["member_id"]
            conn.commit()
            flash("Member added successfully.", "success")
            return redirect(url_for("member_detail", member_id=member_id))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash("A member with that email already exists.", "danger")
        except Exception as e:
            conn.rollback()
            flash(f"Error adding member: {e}", "danger")
        finally:
            conn.close()

    return render_template("members/add.html")


@app.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
def member_edit(member_id):
    try:
        member = query_db("SELECT * FROM members WHERE member_id = %s",
                          (member_id,), fetchone=True)
        if not member:
            flash("Member not found.", "warning")
            return redirect(url_for("members_list"))
    except Exception as e:
        flash(f"Error loading member: {e}", "danger")
        return redirect(url_for("members_list"))

    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        email       = request.form.get("email", "").strip()
        phone       = request.form.get("phone", "").strip()
        joined_date = request.form.get("joined_date") or None

        if not name or not email:
            flash("Name and email are required.", "warning")
            return render_template("members/edit.html", member=member)

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE members SET name=%s, email=%s, phone=%s, joined_date=%s
                    WHERE member_id=%s
                """, (name, email, phone or None, joined_date, member_id))
            conn.commit()
            flash("Member updated successfully.", "success")
            return redirect(url_for("member_detail", member_id=member_id))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash("A member with that email already exists.", "danger")
        except Exception as e:
            conn.rollback()
            flash(f"Error updating member: {e}", "danger")
        finally:
            conn.close()

    return render_template("members/edit.html", member=member)


@app.route("/members/<int:member_id>/delete", methods=["POST"])
def member_delete(member_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM members WHERE member_id = %s", (member_id,))
        conn.commit()
        flash("Member deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting member: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("members_list"))


# clubs crud

@app.route("/clubs/add", methods=["GET", "POST"])
def club_add():
    if request.method == "POST":
        name      = request.form.get("name", "").strip()
        desc      = request.form.get("description", "").strip()
        founded   = request.form.get("founded_date") or None
        frequency = request.form.get("meeting_frequency", "").strip()

        if not name:
            flash("Club name is required.", "warning")
            return render_template("clubs/add.html")

        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO clubs (name, description, founded_date, meeting_frequency)
                    VALUES (%s, %s, %s, %s) RETURNING club_id
                """, (name, desc or None, founded, frequency or None))
                club_id = cur.fetchone()["club_id"]
            conn.commit()
            flash("Club added successfully.", "success")
            return redirect(url_for("club_detail", club_id=club_id))
        except Exception as e:
            conn.rollback()
            flash(f"Error adding club: {e}", "danger")
        finally:
            conn.close()

    return render_template("clubs/add.html")


@app.route("/clubs/<int:club_id>/edit", methods=["GET", "POST"])
def club_edit(club_id):
    try:
        club = query_db("SELECT * FROM clubs WHERE club_id = %s", (club_id,), fetchone=True)
        if not club:
            flash("Club not found.", "warning")
            return redirect(url_for("clubs_list"))
    except Exception as e:
        flash(f"Error loading club: {e}", "danger")
        return redirect(url_for("clubs_list"))

    if request.method == "POST":
        name      = request.form.get("name", "").strip()
        desc      = request.form.get("description", "").strip()
        founded   = request.form.get("founded_date") or None
        frequency = request.form.get("meeting_frequency", "").strip()

        if not name:
            flash("Club name is required.", "warning")
            return render_template("clubs/edit.html", club=club)

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE clubs SET name=%s, description=%s,
                    founded_date=%s, meeting_frequency=%s WHERE club_id=%s
                """, (name, desc or None, founded, frequency or None, club_id))
            conn.commit()
            flash("Club updated successfully.", "success")
            return redirect(url_for("club_detail", club_id=club_id))
        except Exception as e:
            conn.rollback()
            flash(f"Error updating club: {e}", "danger")
        finally:
            conn.close()

    return render_template("clubs/edit.html", club=club)


@app.route("/clubs/<int:club_id>/delete", methods=["POST"])
def club_delete(club_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clubs WHERE club_id = %s", (club_id,))
        conn.commit()
        flash("Club deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting club: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("clubs_list"))


# meetings crud

@app.route("/meetings/add", methods=["GET", "POST"])
def meeting_add():
    try:
        clubs = query_db("SELECT club_id, name FROM clubs ORDER BY name")
        books = query_db("SELECT book_id, title FROM books ORDER BY title")
    except Exception as e:
        flash(f"Error loading form data: {e}", "danger")
        return redirect(url_for("meetings_list"))

    if request.method == "POST":
        club_id  = request.form.get("club_id") or None
        book_id  = request.form.get("book_id") or None
        mdate    = request.form.get("meeting_date") or None
        location = request.form.get("location", "").strip()
        duration = request.form.get("duration_minutes") or None
        notes    = request.form.get("notes", "").strip()
        status   = request.form.get("status", "planned")

        if not club_id or not mdate:
            flash("Club and meeting date are required.", "warning")
            return render_template("meetings/add.html", clubs=clubs, books=books)

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO meetings
                    (club_id, book_id, meeting_date, location, duration_minutes, notes, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (club_id, book_id, mdate, location or None, duration,
                      notes or None, status))
            conn.commit()
            flash("Meeting added successfully.", "success")
            return redirect(url_for("meetings_list"))
        except Exception as e:
            conn.rollback()
            flash(f"Error adding meeting: {e}", "danger")
        finally:
            conn.close()

    return render_template("meetings/add.html", clubs=clubs, books=books)


@app.route("/meetings/<int:meeting_id>/edit", methods=["GET", "POST"])
def meeting_edit(meeting_id):
    try:
        meeting = query_db("SELECT * FROM meetings WHERE meeting_id = %s",
                           (meeting_id,), fetchone=True)
        if not meeting:
            flash("Meeting not found.", "warning")
            return redirect(url_for("meetings_list"))
        clubs = query_db("SELECT club_id, name FROM clubs ORDER BY name")
        books = query_db("SELECT book_id, title FROM books ORDER BY title")
    except Exception as e:
        flash(f"Error loading meeting: {e}", "danger")
        return redirect(url_for("meetings_list"))

    if request.method == "POST":
        club_id  = request.form.get("club_id") or None
        book_id  = request.form.get("book_id") or None
        mdate    = request.form.get("meeting_date") or None
        location = request.form.get("location", "").strip()
        duration = request.form.get("duration_minutes") or None
        notes    = request.form.get("notes", "").strip()
        status   = request.form.get("status", "planned")

        if not club_id or not mdate:
            flash("Club and meeting date are required.", "warning")
            return render_template("meetings/edit.html", meeting=meeting,
                                   clubs=clubs, books=books)
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE meetings SET club_id=%s, book_id=%s, meeting_date=%s,
                    location=%s, duration_minutes=%s, notes=%s, status=%s
                    WHERE meeting_id=%s
                """, (club_id, book_id, mdate, location or None, duration,
                      notes or None, status, meeting_id))
            conn.commit()
            flash("Meeting updated successfully.", "success")
            return redirect(url_for("meetings_list"))
        except Exception as e:
            conn.rollback()
            flash(f"Error updating meeting: {e}", "danger")
        finally:
            conn.close()

    return render_template("meetings/edit.html", meeting=meeting,
                           clubs=clubs, books=books)


@app.route("/meetings/<int:meeting_id>/delete", methods=["POST"])
def meeting_delete(meeting_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM meetings WHERE meeting_id = %s", (meeting_id,))
        conn.commit()
        flash("Meeting deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting meeting: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("meetings_list"))


# reviews

@app.route("/reviews/add", methods=["POST"])
def review_add():
    member_id   = request.form.get("member_id") or None
    book_id     = request.form.get("book_id") or None
    rating      = request.form.get("rating") or None
    review_text = request.form.get("review_text", "").strip()
    review_date = request.form.get("review_date") or None

    if not member_id or not book_id or not rating:
        flash("Member, book, and rating are required.", "warning")
        return redirect(url_for("book_detail", book_id=book_id))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO reviews (member_id, book_id, rating, review_text, review_date)
                VALUES (%s, %s, %s, %s, %s)
            """, (member_id, book_id, rating, review_text or None, review_date))
        conn.commit()
        flash("Review added successfully.", "success")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash("This member has already reviewed this book.", "danger")
    except Exception as e:
        conn.rollback()
        flash(f"Error adding review: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("book_detail", book_id=book_id))


# run

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
