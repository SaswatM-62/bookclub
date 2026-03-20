# generates and inserts all data for the book club management system
# run: python fetch_data.py
# requires: faker psycopg2-binary python-dotenv
# db config from .env: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

import os
import random
import sys
from datetime import date, timedelta

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from faker import Faker

load_dotenv()

# db connection
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "bookclub"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

# seed for reproducibility
random.seed(42)
Faker.seed(42)
fake = Faker()

# helpers

def rand_date(start_year=2015, end_year=2024, end_date=None):
    start = date(start_year, 1, 1)
    end   = end_date if end_date is not None else date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


def insert_rows(cur, table, fieldnames, rows):
    """Bulk-insert rows using execute_batch; prints a progress line."""
    if not rows:
        print(f"  {table:<25} -- 0 rows (skipped)")
        return
    cols         = ", ".join(fieldnames)
    placeholders = ", ".join(f"%({col})s" for col in fieldnames)
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    try:
        psycopg2.extras.execute_batch(cur, sql, rows, page_size=500)
        print(f"  {table:<25} -- {len(rows)} rows inserted")
    except psycopg2.errors.UniqueViolation as exc:
        raise RuntimeError(
            f"Duplicate key while inserting into '{table}': {exc.diag.message_detail}"
        ) from exc
    except psycopg2.errors.ForeignKeyViolation as exc:
        raise RuntimeError(
            f"Foreign key violation while inserting into '{table}': {exc.diag.message_detail}"
        ) from exc
    except psycopg2.errors.CheckViolation as exc:
        raise RuntimeError(
            f"Check constraint violated while inserting into '{table}': {exc.diag.message_detail}"
        ) from exc
    except psycopg2.Error as exc:
        raise RuntimeError(
            f"Database error while inserting into '{table}': {exc}"
        ) from exc


def reset_sequences(cur):
    """Advance SERIAL sequences past the highest manually-inserted ID."""
    sequences = [
        ("authors_author_id_seq",   "authors",  "author_id"),
        ("books_book_id_seq",       "books",    "book_id"),
        ("members_member_id_seq",   "members",  "member_id"),
        ("clubs_club_id_seq",       "clubs",    "club_id"),
        ("meetings_meeting_id_seq", "meetings", "meeting_id"),
        ("reviews_review_id_seq",   "reviews",  "review_id"),
    ]
    for seq, table, col in sequences:
        cur.execute(
            f"SELECT setval('{seq}', (SELECT MAX({col}) FROM {table}))"
        )
    print("  Sequences reset successfully")


# static lookup data
GENRE_DATA = [
    ("Mystery",            "Stories involving the investigation of a crime or puzzle.",                         "Fiction"),
    ("Science Fiction",    "Stories based on imagined future scientific or technological advances.",             "Fiction"),
    ("Fantasy",            "Stories set in fictional universes with magical elements.",                         "Fiction"),
    ("Romance",            "Stories focused on love and romantic relationships.",                                "Fiction"),
    ("Thriller",           "Fast-paced stories designed to create suspense and excitement.",                    "Fiction"),
    ("Horror",             "Stories intended to frighten, unsettle, or disturb the reader.",                    "Fiction"),
    ("Drama",              "Stories focusing on realistic characters and emotional themes.",                     "Fiction"),
    ("Adventure",          "Stories involving exciting journeys, quests, or dangerous situations.",             "Fiction"),
    ("Crime",              "Stories centered around criminal acts and their consequences.",                      "Fiction"),
    ("Classics",           "Works of enduring literary merit recognized across generations.",                   "Fiction"),
    ("Graphic Novel",      "Narrative works presented in comic-strip format.",                                  "Fiction"),
    ("Young Adult",        "Stories written for and about teenagers and young adults.",                         "Fiction"),
    ("Historical Fiction", "Stories set in the past that blend real history with fictional elements.",          "Fiction"),
    ("Dystopian",          "Stories set in oppressive, imagined future societies.",                             "Fiction"),
    ("Biography",          "Non-fiction accounts of a real person's life.",                                     "Non-Fiction"),
    ("History",            "Non-fiction accounts of past events and civilizations.",                            "Non-Fiction"),
    ("Self-Help",          "Books aimed at personal development and improvement.",                              "Non-Fiction"),
    ("Philosophy",         "Books exploring fundamental questions about existence and knowledge.",              "Non-Fiction"),
    ("Poetry",             "Literary works that use verse and rhythm to evoke meaning.",                        "Non-Fiction"),
    ("Science",            "Non-fiction books explaining scientific concepts and discoveries.",                  "Non-Fiction"),
]
ALL_GENRES = [g[0] for g in GENRE_DATA]

NATIONALITIES = [
    "American", "British", "Canadian", "Australian", "Irish",
    "French", "German", "Russian", "Japanese", "Indian",
    "Nigerian", "South African", "Brazilian", "Spanish", "Italian",
    "Swedish", "Norwegian", "Danish", "Polish", "Scottish",
    "Chinese", "Mexican", "Argentine", "Portuguese", "Dutch",
]

LANGUAGES = ["English"] * 90 + [
    "French", "German", "Spanish", "Italian",
    "Portuguese", "Japanese", "Russian", "Dutch", "Swedish", "Polish",
]

MEETING_FREQUENCIES = ["Weekly", "Biweekly", "Monthly", "Quarterly"]
MEETING_LOCATIONS   = [
    "Public Library", "Community Center", "Coffee Shop", "Online - Zoom",
    "Member's Home", "Bookstore", "University Library", "Online - Google Meet",
    "Local Cafe", "City Hall Meeting Room",
]
MEETING_STATUSES    = ["planned", "completed"]
ATTENDANCE_STATUSES = ["attended", "absent", "excused"]
READING_STATUSES    = ["planned", "reading", "completed"]
MEMBER_ROLES        = ["President", "Moderator", "Regular", "Regular", "Regular"]

# title and club name generators
TITLE_TEMPLATES = [
    "The {adj} {noun}", "{noun} of {place}", "The Last {noun}", "A {adj} {noun}",
    "{name}'s {noun}", "The {noun} and the {noun2}", "Beyond the {noun}",
    "In the {adj} {noun}", "The {noun} of {name}", "When {noun}s {verb}",
    "The {adj} Truth", "City of {noun}s", "The {noun} Keeper",
    "Secrets of the {noun}", "The {adj} Journey", "Land of {noun}s",
    "The {noun} Within", "Rise of the {noun}", "The {adj} Hour", "Shadow of {noun}",
]
ADJS   = ["Dark","Hidden","Lost","Broken","Silent","Golden","Ancient","Secret",
          "Forgotten","Sacred","Eternal","Crimson","Hollow","Wild","Distant",
          "Pale","Burning","Shattered","Empty","Bright"]
NOUNS  = ["Storm","Kingdom","Shadow","Fire","River","Moon","Star","Forest","Tower",
          "Garden","Clock","Mirror","Map","Key","Dream","Voice","Heart","Soul",
          "Path","Door","Wind","Sea"]
NOUN2S = ["Stone","Flame","Tide","Mountain","Sky","Light","Blade","Crown",
          "Sword","Rose","Wolf","Raven","Fox","Serpent"]
PLACES = ["the North","Shadows","the Deep","the Forgotten","the East",
          "the Mountains","the Sea","Time","the Stars","the Past"]
VERBS  = ["Fall","Rise","Burn","Dance","Speak","Sleep","Wake","Fly"]

CLUB_ADJECTIVES = ["Literary","Classic","Modern","Avid","Curious","Wandering",
                   "Thoughtful","Bookish","Passionate","Local"]
CLUB_NOUNS      = ["Readers","Pages","Chapters","Minds","Voices",
                   "Thinkers","Explorers","Friends","Circle","Society"]


def fake_title():
    t = random.choice(TITLE_TEMPLATES)
    return (t
            .replace("{adj}",   random.choice(ADJS))
            .replace("{noun2}", random.choice(NOUN2S))
            .replace("{noun}",  random.choice(NOUNS))
            .replace("{place}", random.choice(PLACES))
            .replace("{name}",  fake.last_name())
            .replace("{verb}",  random.choice(VERBS)))


def fake_club_name():
    return f"The {random.choice(CLUB_ADJECTIVES)} {random.choice(CLUB_NOUNS)}"


# data generation

def generate_data():
    print("Generating data...")
    TODAY = date(2026, 3, 20)

    # 1. Genres
    genres_rows = [
        {"genre": g, "description": d, "fiction_type": ft}
        for g, d, ft in GENRE_DATA
    ]

    # 2. Authors (500)
    authors_rows = []
    author_ids   = list(range(1, 501))
    seen_names   = set()
    for aid in author_ids:
        name = fake.name()
        while name in seen_names:
            name = fake.name()
        seen_names.add(name)
        birth_year  = random.randint(1920, 1990)
        nationality = random.choice(NATIONALITIES)
        biography   = (
            f"{name} is a {nationality.lower()} author born in {birth_year}. "
            f"{fake.sentence()} {fake.sentence()}"
        )[:500]
        authors_rows.append({
            "author_id":   aid,
            "name":        name,
            "nationality": nationality,
            "birth_date":  str(birth_year),
            "biography":   biography,
        })

    # 3. Books (2000)
    books_rows  = []
    book_ids    = list(range(1, 2001))
    seen_titles = set()
    seen_isbns  = set()
    for bid in book_ids:
        title = fake_title()
        for _ in range(20):
            if title not in seen_titles:
                break
            title = fake_title()
        seen_titles.add(title)

        isbn = fake.isbn13(separator="")
        while isbn in seen_isbns:
            isbn = fake.isbn13(separator="")
        seen_isbns.add(isbn)

        books_rows.append({
            "book_id":        bid,
            "isbn":           isbn,
            "title":          title,
            "description":    fake.paragraph(nb_sentences=3),
            "year_published": random.randint(1950, 2024),
            "language":       random.choice(LANGUAGES),
        })

    # 4. Members (1000)
    members_rows = []
    member_ids   = list(range(1, 1001))
    seen_emails  = set()
    for mid in member_ids:
        email = fake.email()
        while email in seen_emails:
            email = fake.email()
        seen_emails.add(email)
        members_rows.append({
            "member_id":   mid,
            "name":        fake.name(),
            "email":       email,
            "phone":       fake.phone_number()[:20],
            "joined_date": str(rand_date(2015, 2024)),
        })

    # 5. Clubs (100)
    clubs_rows = []
    club_ids   = list(range(1, 101))
    for cid in club_ids:
        clubs_rows.append({
            "club_id":           cid,
            "name":              fake_club_name(),
            "description":       fake.sentence(),
            "founded_date":      str(rand_date(2010, 2022)),
            "meeting_frequency": random.choice(MEETING_FREQUENCIES),
        })

    # Build lookups used by later sections
    club_founded = {
        r["club_id"]: date.fromisoformat(r["founded_date"])
        for r in clubs_rows
    }
    member_joined = {
        r["member_id"]: date.fromisoformat(r["joined_date"])
        for r in members_rows
    }

    # 6. Meetings: one meeting per interval from club founding to 6 months ahead.
    #    Past meetings (≤ today) = completed; future = planned.
    #    Books are assigned in order from a per-club shuffled list so each club
    #    discusses every book at most once (no repeated books within a club).
    FREQ_DAYS  = {"Weekly": 7, "Biweekly": 14, "Monthly": 30, "Quarterly": 91}
    PLAN_UNTIL = date(2026, 9, 20)

    # Pre-shuffle a unique book order for every club
    club_book_lists  = {cid: random.sample(book_ids, len(book_ids)) for cid in club_ids}
    club_book_cursor = {cid: 0 for cid in club_ids}

    meetings_rows = []
    meeting_id    = 1
    for club in clubs_rows:
        cid      = club["club_id"]
        interval = timedelta(days=FREQ_DAYS[club["meeting_frequency"]])
        current  = club_founded[cid]
        while current <= PLAN_UNTIL:
            status   = "completed" if current <= TODAY else "planned"
            cursor   = club_book_cursor[cid]
            book_id  = club_book_lists[cid][cursor % len(book_ids)]
            club_book_cursor[cid] += 1
            meetings_rows.append({
                "meeting_id":       meeting_id,
                "club_id":          cid,
                "book_id":          book_id,
                "meeting_date":     str(current),
                "location":         random.choice(MEETING_LOCATIONS),
                "duration_minutes": random.choice([60, 90, 120, 150]),
                "notes":            fake.sentence() if status == "completed" else "",
                "status":           status,
            })
            meeting_id += 1
            current   += interval

    # Build lookups for cross-table consistency checks
    book_pub_year   = {r["book_id"]:   r["year_published"]  for r in books_rows}
    author_birth_yr = {r["author_id"]: int(r["birth_date"]) for r in authors_rows}

    # 7. book_author (~2500 rows)
    # Only assign authors who were born at least 18 years before publication.
    ba_rows = []
    seen_ba = set()
    for bid in book_ids:
        year = book_pub_year[bid]
        eligible = [aid for aid in author_ids if author_birth_yr[aid] + 18 <= year]
        if not eligible:
            eligible = author_ids   # fallback: very old books (edge case)
        num     = random.choices([1, 2], weights=[75, 25])[0]
        authors = random.sample(eligible, min(num, len(eligible)))
        for order, aid in enumerate(authors, start=1):
            if (bid, aid) not in seen_ba:
                seen_ba.add((bid, aid))
                ba_rows.append({"book_id": bid, "author_id": aid, "author_order": order})

    # 8. book_genre (~4000 rows)
    bg_rows = []
    seen_bg = set()
    for bid in book_ids:
        num    = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
        genres = random.sample(ALL_GENRES, num)
        for genre in genres:
            if (bid, genre) not in seen_bg:
                seen_bg.add((bid, genre))
                bg_rows.append({"book_id": bid, "genre": genre})

    # 9. member_club: every member gets at least 1 club;
    #    joined_date must be >= max(club.founded_date, member.joined_date)
    def make_mc_row(mid, cid):
        earliest = max(club_founded[cid], member_joined[mid])
        if earliest >= cutoff:
            jdate = cutoff
        else:
            jdate = earliest + timedelta(
                days=random.randint(0, (cutoff - earliest).days)
            )
        return {
            "member_id":   mid,
            "club_id":     cid,
            "role":        random.choice(MEMBER_ROLES),
            "joined_date": str(jdate),
        }

    mc_rows = []
    seen_mc = set()
    cutoff  = date(2026, 3, 20)

    # Pass 1: guarantee every member has at least one club
    for mid in member_ids:
        cid = random.choice(club_ids)
        seen_mc.add((mid, cid))
        mc_rows.append(make_mc_row(mid, cid))

    # Pass 2: add extra memberships up to the 2000 target
    for mid in member_ids:
        if len(mc_rows) >= 2000:
            break
        extra = random.choices([0, 1, 2], weights=[50, 35, 15])[0]
        for cid in random.sample(club_ids, min(extra, len(club_ids))):
            if (mid, cid) not in seen_mc:
                seen_mc.add((mid, cid))
                mc_rows.append(make_mc_row(mid, cid))
            if len(mc_rows) >= 2000:
                break

    # Fix roles: exactly 1 President, at most 1 Moderator per club; rest Regular.
    from collections import defaultdict
    club_member_idx = defaultdict(list)
    for i, mc in enumerate(mc_rows):
        club_member_idx[mc["club_id"]].append(i)
    for indices in club_member_idx.values():
        random.shuffle(indices)
        for rank, idx in enumerate(indices):
            if rank == 0:
                mc_rows[idx]["role"] = "President"
            elif rank == 1:
                mc_rows[idx]["role"] = "Moderator"
            else:
                mc_rows[idx]["role"] = "Regular"

    # Build shared lookup used by attendance, reading_list, and reviews:
    #   club_id -> [(meeting_id, meeting_date, book_id)]  for completed meetings
    #   club_id -> [(meeting_id, meeting_date, book_id)]  for planned meetings
    club_completed_meetings = {}
    club_planned_meetings   = {}
    for m in meetings_rows:
        cid   = m["club_id"]
        entry = (m["meeting_id"], date.fromisoformat(m["meeting_date"]), m["book_id"])
        if m["status"] == "completed":
            club_completed_meetings.setdefault(cid, []).append(entry)
        else:
            club_planned_meetings.setdefault(cid, []).append(entry)

    # 10. attendance: valid pairs only: member in club, meeting completed,
    #     meeting_date >= member's club join date; ~80% sampling for realism.
    #     Status is weighted to reflect realistic attendance patterns:
    #     ~70% attended, ~20% absent, ~10% excused.
    ATT_STATUSES  = ["attended", "attended", "attended", "attended",
                     "attended", "attended", "attended",
                     "absent",  "absent",
                     "excused"]
    att_rows = []
    seen_att = set()
    for mc in mc_rows:
        mid       = mc["member_id"]
        cid       = mc["club_id"]
        mc_joined = date.fromisoformat(mc["joined_date"])
        eligible  = [
            mtg_id
            for mtg_id, mtg_date, _ in club_completed_meetings.get(cid, [])
            if mtg_date >= mc_joined
        ]
        for mtg_id in eligible:
            if (mid, mtg_id) not in seen_att and random.random() < 0.8:
                seen_att.add((mid, mtg_id))
                att_rows.append({
                    "member_id":  mid,
                    "meeting_id": mtg_id,
                    "status":     random.choice(ATT_STATUSES),
                })

    # 11. reading_list: derived directly from meetings so counts are consistent:
    #
    #   • 'completed' entry for every book from a completed meeting (1 per meeting
    #     since books are unique per club) → count equals completed-meetings count
    #   • 'planned' entry for every book from a planned meeting (no overlap with
    #     completed)
    #   • Extra 'planned' entries (5–15 per club) for books with no meeting yet,
    #     so total reading-list entries > completed + planned meeting counts
    rl_rows = []
    seen_rl = set()

    for cid in club_ids:
        comp_entries  = {book_id: mtg_date
                         for _, mtg_date, book_id
                         in club_completed_meetings.get(cid, [])}
        plan_entries  = {book_id: mtg_date
                         for _, mtg_date, book_id
                         in club_planned_meetings.get(cid, [])
                         if book_id not in comp_entries}

        for bid, mdate in comp_entries.items():
            if (cid, bid) not in seen_rl:
                seen_rl.add((cid, bid))
                rl_rows.append({"club_id": cid, "book_id": bid,
                                 "scheduled_date": str(mdate),
                                 "status": "completed"})

        # The soonest upcoming planned meeting = the book the club is currently
        # reading; mark it 'reading', everything else 'planned'.
        plan_sorted = sorted(plan_entries.items(), key=lambda x: x[1])  # by date
        for i, (bid, mdate) in enumerate(plan_sorted):
            if (cid, bid) not in seen_rl:
                seen_rl.add((cid, bid))
                status = "reading" if i == 0 else "planned"
                rl_rows.append({"club_id": cid, "book_id": bid,
                                 "scheduled_date": str(mdate),
                                 "status": status})

        # Extra books on the reading list that have no meeting scheduled yet
        used      = set(comp_entries) | set(plan_entries)
        extras    = random.sample([b for b in book_ids if b not in used],
                                  random.randint(5, 15))
        for bid in extras:
            if (cid, bid) not in seen_rl:
                seen_rl.add((cid, bid))
                future = TODAY + timedelta(days=random.randint(30, 730))
                rl_rows.append({"club_id": cid, "book_id": bid,
                                 "scheduled_date": str(future),
                                 "status": "planned"})

    # 12. reviews: each member reviews books their club discussed at completed
    #     meetings, written within 60 days of the meeting.
    #     ~30 % sampling keeps the table at a manageable size.
    #     Constraints: review_date >= meeting_date AND >= book.year_published
    review_end = TODAY   # reviews can be written up to today (2026-03-20)
    rev_rows   = []
    seen_rev   = set()
    review_id  = 1

    for mc in mc_rows:
        mid       = mc["member_id"]
        cid       = mc["club_id"]
        mc_joined = date.fromisoformat(mc["joined_date"])

        for _, mtg_date, book_id in club_completed_meetings.get(cid, []):
            if mtg_date < mc_joined:
                continue                        # not a member at the time
            if random.random() >= 0.30:
                continue                        # 30 % of eligible meetings reviewed
            if (mid, book_id) in seen_rev:
                continue                        # UNIQUE(member, book) constraint

            earliest = max(mtg_date, date(book_pub_year[book_id], 1, 1))
            if earliest > review_end:
                continue
            latest = min(review_end, mtg_date + timedelta(days=60))
            if latest < earliest:
                latest = earliest
            rdate = earliest + timedelta(
                days=random.randint(0, (latest - earliest).days)
            )
            seen_rev.add((mid, book_id))
            rev_rows.append({
                "review_id":   review_id,
                "member_id":   mid,
                "book_id":     book_id,
                "rating":      random.randint(1, 5),
                "review_text": fake.paragraph(nb_sentences=2),
                "review_date": str(rdate),
            })
            review_id += 1

    print(f"  Generated {len(genres_rows)} genres, {len(authors_rows)} authors, "
          f"{len(books_rows)} books, {len(members_rows)} members")
    print(f"  Generated {len(clubs_rows)} clubs, {len(meetings_rows)} meetings "
          f"({sum(1 for m in meetings_rows if m['status']=='completed')} completed, "
          f"{sum(1 for m in meetings_rows if m['status']=='planned')} planned), "
          f"{len(rev_rows)} reviews")
    print(f"  Generated {len(ba_rows)} book_author, {len(bg_rows)} book_genre, "
          f"{len(mc_rows)} member_club")
    comp_rl = sum(1 for r in rl_rows if r["status"] == "completed")
    plan_rl = sum(1 for r in rl_rows if r["status"] == "planned")
    print(f"  Generated {len(att_rows)} attendance records")
    print(f"  Generated {len(rl_rows)} reading_list entries "
          f"({comp_rl} completed, {plan_rl} planned), "
          f"{len(rev_rows)} reviews")

    return (genres_rows, authors_rows, books_rows, members_rows, clubs_rows,
            meetings_rows, ba_rows, bg_rows, mc_rows, att_rows, rl_rows, rev_rows)


# database insertion

def insert_all(data):
    (genres_rows, authors_rows, books_rows, members_rows, clubs_rows,
     meetings_rows, ba_rows, bg_rows, mc_rows, att_rows, rl_rows, rev_rows) = data

    print(f"\nConnecting to PostgreSQL "
          f"({DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']})...")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except psycopg2.OperationalError as exc:
        print(f"ERROR: Could not connect to the database.\n  {exc}")
        sys.exit(1)

    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            print("\nInserting rows...")

            # Insertion order respects FK dependencies
            insert_rows(cur, "genres",
                        ["genre", "description", "fiction_type"], genres_rows)
            insert_rows(cur, "authors",
                        ["author_id", "name", "nationality", "birth_date", "biography"],
                        authors_rows)
            insert_rows(cur, "books",
                        ["book_id", "isbn", "title", "description", "year_published", "language"],
                        books_rows)
            insert_rows(cur, "members",
                        ["member_id", "name", "email", "phone", "joined_date"],
                        members_rows)
            insert_rows(cur, "clubs",
                        ["club_id", "name", "description", "founded_date", "meeting_frequency"],
                        clubs_rows)
            insert_rows(cur, "meetings",
                        ["meeting_id", "club_id", "book_id", "meeting_date",
                         "location", "duration_minutes", "notes", "status"],
                        meetings_rows)
            insert_rows(cur, "book_author",
                        ["book_id", "author_id", "author_order"], ba_rows)
            insert_rows(cur, "book_genre",
                        ["book_id", "genre"], bg_rows)
            insert_rows(cur, "member_club",
                        ["member_id", "club_id", "role", "joined_date"], mc_rows)
            insert_rows(cur, "attendance",
                        ["member_id", "meeting_id", "status"], att_rows)
            insert_rows(cur, "reading_list",
                        ["club_id", "book_id", "scheduled_date", "status"], rl_rows)
            insert_rows(cur, "reviews",
                        ["review_id", "member_id", "book_id", "rating",
                         "review_text", "review_date"],
                        rev_rows)

            print("\nResetting sequences...")
            reset_sequences(cur)

        conn.commit()
        print("\nAll data committed to PostgreSQL.")

    except RuntimeError as exc:
        conn.rollback()
        print(f"\nERROR: {exc}")
        print("Transaction rolled back, no data was written.")
        sys.exit(1)
    except psycopg2.Error as exc:
        conn.rollback()
        print(f"\nUnexpected database error: {exc}")
        print("Transaction rolled back, no data was written.")
        sys.exit(1)
    finally:
        conn.close()


# entry point

if __name__ == "__main__":
    print("=" * 60)
    print("Book Club DB Data Generator")
    print("=" * 60)
    print()

    data = generate_data()
    insert_all(data)

    print()
    print("=" * 60)
    print("Done.")
    print("=" * 60)
