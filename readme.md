# Xiami Exporter

> Note: 虾米音乐已经关闭，目前此项目已无法使用，
> 但代码框架良好，可用于实现网易云音乐等其他平台的导出工具。

导出虾米音乐的个人数据，功能：
- [x] 导出歌曲为 json
  - [x] 收藏歌曲
  - [x] 收藏专辑
  - [x] 播放列表
- [x] 导出收藏艺人为 json
- [x] 导出收藏专辑为 json
- [x] 导出播放列表为 json (个人和收藏)
- [x] 将导出的数据整理至 sqlite 数据库
  - [x] 收藏歌曲
  - [ ] ~~收藏艺人~~
  - [x] 收藏专辑
  - [x] 播放列表
- [x] 下载已导出歌曲的 MP3 文件
- [x] 下载已导出专辑的 MP3 文件
- [x] 下载已导出播放列表的 MP3 文件
- [x] 根据导出信息为 MP3 添加完整的 ID3 tag
- [x] 下载已导出歌曲的专辑、艺人的封面图片

## Getting Started

1. Clone 项目，创建 Python 3 虚拟环境，安装所有依赖

   ```
   $ python -m venv venv
   $ source venv/bin/activate
   $ pip install -r requirements.txt
   ```

2. 在 Chrome 中登录虾米，点击 “我的音乐”，从 URL 中获取 user_id，例如 `https://www.xiami.com/user/932367`, user_id 即为 `932367`.
3. 运行 `python -m xiami_exporter.cli init`，根据提示，输入配置项，其中包括刚刚获取的 user_id.
4. 回到 Chrome “我的音乐” 页面，右键选择 “审查页面” (Inspect)，点击 “网络” (Network) 并在过滤器中选择 XHR，刷新页面，在最后一条带有 `_s` 的网络请求上点击右键，选择 “Copy - Copy as Node.js fetch”
  ![](./inspect_steps.png)
5. 在项目目录下创建 fetch.py 文件，将刚才拷贝的内容粘贴进去并保存 (`pbpaste > fetch.py`)
6. 运行 `python -m xiami_exporter.cli check`, 显示成功表示可以使用导出功能，否则请重试上一步，或联系开发者
7. 根据想要导出的数据，运行相应指令，如 `python -m xiami_exporter.cli export-songs` 即导出收藏歌曲为 json

## Usage

运行方式为 `python -m xiami_exporter.cli COMMAND`, 可通过 `python -m xiami_exporter.cli --help` 查看指令列表。

### COMMAND: `init`

初始化配置文件

### COMMAND: `check`

检查 `fetch.py` 是否可以通过虾米 API 的验证，成功时输出如下:

```
test fetch() ok
recal token correct: be5bb12dbb135066f4cb282706019bc8
Success, you can now use the export commands
```

### COMMAND: `export <fav_type>`

> Previously `export-songs`

导出数据为 json 文件，需要指定子命令 fav_type:
- SONGS: 收藏歌曲
- ALBUMS: 收藏专辑
- ARTISTS: 收藏艺人
- PLAYLISTS: 收藏歌单
- MY_PLAYLISTS: 我创建的歌单

json 文件每页一个，文件名为 `<fav_type>-<page_number>.json`，存放于 `XiamiExports/json/<fav_type>` 目录下。

对于专辑和歌单 (ALBUMS, PLAYLISTS, MY_PLAYLISTS)，在完成首次导出后，需要额外使用 `-c, --complete-songs` 参数运行，
来获取包含歌曲的详细信息，每个专辑/歌单的详细信息 json 文件会以 `<id>.json` 为名存放于 `XiamiExports/json/<fav_type>/details` 目录下。

此指令是后续创建数据库、下载音乐的基础。

### COMMAND: `create-songs-db`

将收藏歌曲导入数据库中记录，此指令是 `download-music` 的基础。

### COMMAND: `download-music`

下载所有收藏歌曲，下载状态 (download_status) 会同步保存到数据库中。

中断后可重新运行，只会从数据库中筛选 download_status = NOT_SET 的歌曲进行下载。

> 注: 此指令后续会支持下载 album 和 playlist

### COMMAND: `download-covers`

下载所有歌曲的专辑封面 (album cover)，支持如下选项：
- `-f, --force`: 强制重新下载即使文件存在
- `-l, --artist-logos`: 下载艺人图片而非专辑封面

### COMMAND: `tag-music`

为所有已下载的歌曲添加 ID3 tags。

若专辑封面文件存在，则会将其添加到 tags 中，因此建议先运行 `download-covers`。

### COMMAND: `trim-json`

对已导出的 json 文件进行修剪，去掉不必要的数据。

此命令用于维护已导出的 json 数据，若使用最新版重新导出，
则导出时已对各类数据进行自动修剪，无需之后运行此命令。

## Hierarchy

Xiami Exporter 保存的数据有如下几类：
- json 数据文件: 歌曲、专辑、艺人、播放列表
- MP3 音频文件: 歌曲、专辑、播放列表
- jpg/png 图片文件: 专辑封面
- sqlite3 数据库文件: 歌曲、专辑、艺人、播放列表

默认在项目路径下创建 `XiamiExports` 目录，其文件系统结构大体如下:

```
XiamiExports/
  db.sqlite3
  json/
    songs/
      song-1.json
      song-2.json
      ...
    albums/
      details/
        ALBUM_ID.json
      albums-1.json
      ...
    playlists/
      details/
        PLAYLIST_ID.json
      playlists-1.json
      ...
    my_playlists/
      | same as `playlists/`
    artists/
  music/
    NUM-SONG_ID.mp3
  covers/
    ALBUM_ID.jpg
  artist_logos/
    ARTIST_ID.jpg
```

## Development

<details>
<summary><strong><code>Development notes, check if you have interests.</code></strong></summary>


TODOs
- download_covers: handle songs from albums/playlists details

### tag problems

- arrangement -> TIPL, tried to save but cannot be displayed
- [solved] comment -> COMM, easyid3 writes as:
  ```
  COMM==XXX=artist_alias: あーりーれい
  ```

  which is not recognized by Meta.app.

  Meta.app writes as:
  ```
  COMM==ENG=first line
  second line
  COMM=ID3v1 Comment=eng=first line
  second line
  ```

  solution:

  follows how itunes mp3 writes comment:
  ```
  COMM==eng=artist_alias: あーりーれい
  ```

- performers should be TMCL, but is written as TXXX:
  ```
  TXXX=PERFORMER=陽花
  ```

</details>
