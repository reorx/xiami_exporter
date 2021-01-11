import peewee
from peewee import CharField, IntegerField, BooleanField, DateTimeField, DoesNotExist
import peeweedbevolve  # NOQA


# http://docs.peewee-orm.com/en/latest/peewee/database.html#run-time-database-configuration
db = peewee.SqliteDatabase(None)


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Song(BaseModel):
    row_number = IntegerField()
    id = IntegerField(help_text='songId', primary_key=True)
    sid = CharField(help_text='songStringId')
    name = CharField(help_text='songName')
    name_pinyin = CharField(help_text='pinyin')
    sub_name = CharField()

    album_id = IntegerField(help_text='albumId')
    album_sid = CharField(help_text='albumStringId')
    album_name = CharField(help_text='albumName')
    album_sub_name = CharField(help_text='albumSubName')
    album_lang = CharField(help_text='albumLanguage')
    album_song_count = IntegerField(help_text='albumSongCount')
    track = IntegerField(help_text='track')

    artist_id = IntegerField(help_text='artistId')
    artist_name = CharField(help_text='artistName')
    artist_alias = CharField(help_text='artistAlias')

    # singers are artists splited by '/'
    singers = CharField(help_text='singers')
    songwriters = CharField(help_text='songwriters')
    composer = CharField(help_text='composer')
    arrangement = CharField(help_text='arrangement')  # 编曲

    bak_song_id = IntegerField(help_text='bakSongId')

    # export meta
    download_status = IntegerField()
    in_songs = BooleanField(default=False)
    in_albums = BooleanField(default=False)
    in_playlists = BooleanField(default=False)

    def __str__(self):
        return f'{self.id}: {self.name} - {self.artist_name} - {self.album_name}'


class DownloadStatus:
    NOT_SET = 0
    SUCCESS = 1
    UNAVAILABLE = -1
    FAILED = -9

    @classmethod
    def to_str(cls, v):
        for k, _v in cls.__dict__.items():
            if v == _v:
                return k
        return ''


def create_song(data, row_number) -> Song:
    md = {}
    for field in Song._meta.sorted_fields:
        # print(field.name, field.help_text)
        if field.help_text:
            md[field.name] = data[field.help_text]

    song = Song(**md)
    song.row_number = row_number

    # sub name
    sub_name = data['subName']
    new_sub_name = data['newSubName']
    if sub_name and new_sub_name:
        sub_name = f'{sub_name} ({new_sub_name}'
    else:
        sub_name = sub_name + new_sub_name
    song.sub_name = sub_name

    song.download_status = DownloadStatus.NOT_SET
    song.in_songs = True
    try:
        song.save(force_insert=True)
    except peewee.IntegrityError:
        pass
    return song


# Migration model must not be changed ever after created
class Migration(BaseModel):
    schema_version = IntegerField()
    applied_at = DateTimeField()


all_models = [Song, Migration]
