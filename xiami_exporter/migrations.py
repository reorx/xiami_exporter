import sys
import peewee as pw
from playhouse import migrate as pw_migrate
import logging
import datetime
from .models import db, all_models, Migration
from .store import FileStore


schema_version = 4

lg = logging.getLogger('xiami.db')

migrator = pw_migrate.SqliteMigrator(db)


def table_exists(db, name):
    """
    vscode python syntax analyzer thinks that db.table_exists will always raise NotImplementedError,
    thus code below are seen as unreachable and painted grey,
    this function is an ugly fix for this behavior.
    """
    try:
        return db.table_exists(name)
    except NotImplementedError:
        pass


def migrate(fs: FileStore):
    if table_exists(db, 'song'):
        # table 'song' exists means schema_version >= 2
        if table_exists(db, 'migration'):
            # version > 2 must have migration records, or fail here, and recreate the database file manually
            m_query = list(Migration.select().order_by(Migration.schema_version.desc()).limit(1))
            try:
                m = list(m_query)[0]
            except IndexError:
                print('migration table is broken, please delete the database and re-run the command')
                sys.exit(1)
            latest_version = m.schema_version
        else:
            # version 2 has no Migration model before running
            latest_version = 1

        if latest_version >= schema_version:
            lg.debug(f'no need to run migrations: {latest_version} >= {schema_version}')
            return

        for ver in range(latest_version + 1, schema_version + 1):
            migration_name = f'migration_00{ver}'
            migration_func = globals().get(migration_name)
            if migration_func:
                print(f'\nRunning migration {migration_name}')
                with db.atomic():
                    migration_func(fs)
                    Migration.create(schema_version=ver, applied_at=datetime.datetime.now())
    else:
        # first time running
        print('init db, create all tables')
        db.create_tables(all_models)
        Migration.create(schema_version=schema_version, applied_at=datetime.datetime.now())


class BaseModel(pw.Model):
    class Meta:
        database = db


def migration_002(fs: FileStore):
    """
    - add migration table
    - update song table
    """
    db.create_tables([Migration])

    in_songs = pw.BooleanField(default=True)
    in_albums = pw.BooleanField(default=False)
    in_playlists = pw.BooleanField(default=False)

    pw_migrate.migrate(
        migrator.add_column('song', 'in_songs', in_songs),
        migrator.add_column('song', 'in_albums', in_albums),
        migrator.add_column('song', 'in_playlists', in_playlists),
    )


def migration_003(fs: FileStore):
    """
    - song: add disc field
    """
    pw_migrate.migrate(
        migrator.add_column('song', 'disc', pw.IntegerField(default=1)),
    )

    class Song(BaseModel):
        id = pw.IntegerField(help_text='songId', primary_key=True)
        disc = pw.IntegerField(help_text='cdSerial')

    for song in fs.load_all_song_json().values():
        Song.update(disc=song['cdSerial']).where(Song.id == song['songId']).execute()


def migration_004(fs):
    """
    - add song_list table
    """
    class SongList(BaseModel):
        list_type = pw.CharField()
        list_id = pw.IntegerField()
        song_id = pw.IntegerField()

        class Meta:
            table_name = 'song_list'

    db.create_tables([SongList])
