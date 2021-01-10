import peewee as pw
from playhouse import migrate as pw_migrate
import logging
import datetime
import sys
from .models import db, all_models, Migration


schema_version = 2

lg = logging.getLogger('xiami.db')

migrator = pw_migrate.SqliteMigrator(db)


def migrate():
    if db.table_exists('song'):
        # table 'song' exists means schema_version >= 2
        if db.table_exists('migration'):
            # version > 2 must have migration records, or fail here, and recreate the database file manually
            m_query = list(Migration.select().order_by(Migration.schema_version.desc()).limit(1))
            try:
                m = list(m_query)[0]
            except IndexError:
                print('migration table is broken, please delete the database and re-run the command')
                return sys.exit(1)
            latest_version = m.schema_version
        else:
            # version 2 has no Migration model before running
            latest_version = 1

        if latest_version >= schema_version:
            lg.debug(f'no need to run migrations: {latest_version} >= {schema_version}')
            return

        for ver in range(latest_version + 1, schema_version + 1):
            print(ver)
            migration_name = f'migration_00{ver}'
            migration_func = globals().get(migration_name)
            if migration_func:
                print(f'\nRunning migration {migration_name}')
                with db.atomic():
                    migration_func()
                    Migration.create(schema_version=ver, applied_at=datetime.datetime.now())
    else:
        # first time running
        print('init db, create all tables')
        db.create_tables(all_models)
        Migration.create(schema_version=schema_version, applied_at=datetime.datetime.now())


class BaseModel(pw.Model):
    class Meta:
        database = db


def migration_002():
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
