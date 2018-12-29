# RSS to SQL

Preserving your subscribed RSS feeds into a relational database.

## Specification

There are three `class` and a configuration file.

### Classes

1. *Class* ToolKit
    - This class define some useful static method to handle parsed feed

2. *Class* RSS
    - Just a representation of a single RSS feed item.

3. *Class* SQL
    - Creating table according to configuration file, call its **fetch** method to store data after that table created scuessfully.

### Configuration File

Thanks to the diversity of RSS feed, it is necessary to configure settings manually. Here is some examples:

#### Minimal configure

Store nothing but id.

```yaml
rss:
  url: "http://songshuhui.net/feed"
sql:
  tablename: "songshuhui"
  field:
    - name: id
      val: "x.get('id')"
      type: VARCHAR
      type_parameter: 64
      nullable: false
      primary_key: true
      autoincrement: false
```

#### Common configure

```yaml
rss:
  url: "https://share.dmhy.org/topics/rss/rss.xml"
  proxies:
    https: "https://127.0.0.1:1080"
sql:
  tablename: "dmhy"
  field:
    - name: id
      val: "x.get('id')"
      type: VARCHAR
      type_parameter: 256
      nullable: false
      primary_key: true
      autoincrement: false
    - name: title
      val: "x.get('title')"
      type: TEXT
    - name: link
      val: "x.get('link')"
      type: TEXT
    - name: pubtime
      val: "ToolKit.struct_time_To_datetime(x.get('published_parsed'))"
      type: TIMESTAMP
      index: true
    - name: summary
      val: "x.get('summary')"
      type: TEXT
```

Just remember the **x** in `val` denotes the *dict* instance of an item which parsed by `feedparser` library

## Usage

### Within code

```python
from rss2sql import SQL
SQL('/path/to/configuration','uri://of:your@own/database').fetch()
```

### Within commandline

```bash
python rss2sql.py -c /path/to/configuration -d uri://of:your@own/database --hide_banner
```

### Discover mode

Configuration file is needed, omit the field section, and run

```bash
python rss2sql.py -c /path/to/configuration  --discover
```

the configuration file should look like

```yaml
rss:
  url: http://songshuhui.net/feed
sql:
  tablename: nyaa
```

## Dependency

- SQLAlchemy and its connector friends (only if you need them)
- feedparser
- requests
- PyYAML