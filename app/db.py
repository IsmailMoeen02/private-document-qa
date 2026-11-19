import json, sqlite3
from . import config
def connect():
    c = sqlite3.connect(config.DB_PATH, check_same_thread=False, isolation_level=None, timeout=30); c.row_factory = sqlite3.Row; c.execute("pragma foreign_keys=on"); c.execute("pragma journal_mode=wal"); return c
def init():
    c = connect()
    c.executescript("""
    create table if not exists users(id integer primary key, username text unique, name text, salt text, hash text, groups text default '[]', is_admin integer default 0, active integer default 1, created text);
    create table if not exists docs(id integer primary key, filename text, title text, kind text, groups text default '["everyone"]', sha text, pages integer, active integer default 1, added_by text, created text);
    create table if not exists chunks(id integer primary key, doc integer references docs(id) on delete cascade, ord integer, heading text, page integer, text text);
    create table if not exists audit(id integer primary key, ts text, username text, question text, outcome text, cited text, score real);
    create table if not exists terms(term text primary key, means text);
    create index if not exists idx_chunks_doc on chunks(doc);
    """); c.close()
def loads(s, default): 
    try: return json.loads(s) if s else default
    except Exception: return default
